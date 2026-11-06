import csv
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps
from pypdf import PdfReader


class ExtractionError(RuntimeError):
    pass


@dataclass
class OCRResult:
    text: str
    mean_confidence: float | None
    words: list[dict]


class DocumentExtractor:
    provider = "local_ocr"
    version = "tesseract-5"

    def extract(self, body: bytes, media_type: str) -> tuple[dict, dict, dict, str]:
        raise NotImplementedError


def _preprocess(image: Image.Image) -> Image.Image:
    """Conservative processing on a copy; the immutable source is never changed."""
    image = ImageOps.exif_transpose(image).convert("L")
    if image.width < 1600:
        scale = min(3.0, 1600 / image.width)
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    image = ImageOps.autocontrast(image, cutoff=1)
    return ImageEnhance.Contrast(image).enhance(1.15)


def _run_tesseract(image: Image.Image, directory: Path, page: int) -> OCRResult:
    source = directory / f"page-{page}.png"
    output = directory / f"ocr-{page}"
    _preprocess(image).save(source, "PNG")
    executable = shutil.which("tesseract")
    if not executable:
        raise ExtractionError("OCR_ENGINE_NOT_INSTALLED")
    try:
        languages = subprocess.run(  # noqa: S603 - fixed trusted executable and arguments
            [executable, "--list-langs"], capture_output=True, text=True, timeout=5
        ).stdout.splitlines()
        language = "ita+eng" if "ita" in languages else "eng"
        completed = subprocess.run(  # noqa: S603 - fixed trusted executable and arguments
            [
                executable,
                str(source),
                str(output),
                "-l",
                language,
                "--oem",
                "1",
                "--psm",
                "6",
                "tsv",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise ExtractionError("OCR_UNAVAILABLE_OR_TIMEOUT") from exc
    if completed.returncode:
        raise ExtractionError("OCR_ENGINE_FAILED")
    tsv = output.with_suffix(".tsv")
    if not tsv.exists():
        raise ExtractionError("OCR_OUTPUT_MISSING")
    words, lines, confidences = [], {}, []
    reader = csv.DictReader(
        StringIO(tsv.read_text(encoding="utf-8", errors="replace")), delimiter="\t"
    )
    for row in reader:
        word = (row.get("text") or "").strip()
        try:
            word_confidence = float(row.get("conf") or -1)
        except ValueError:
            word_confidence = -1
        if not word or word_confidence < 0:
            continue
        key = (row.get("block_num"), row.get("par_num"), row.get("line_num"))
        lines.setdefault(key, []).append(word)
        confidences.append(word_confidence)
        words.append({
            "text": word,
            "confidence": round(word_confidence / 100, 3),
            "box": [int(row[k]) for k in ("left", "top", "width", "height")],
            "page": page,
        })
    text = "\n".join(" ".join(line) for line in lines.values())
    mean = round(sum(confidences) / len(confidences) / 100, 3) if confidences else None
    return OCRResult(text, mean, words)


def _decimal(raw: str) -> str | None:
    value = re.sub(r"[^0-9,.-]", "", raw)
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    else:
        value = value.replace(",", ".")
    try:
        return str(Decimal(value).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _parse(text: str, ocr_confidence: float | None) -> tuple[dict, dict, dict]:
    fields: dict[str, str] = {}
    confidence: dict[str, float] = {}
    candidates: dict[str, list[dict]] = {"amounts": [], "dates": []}
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fields, confidence, candidates
    upper = text.upper()
    date_pattern = r"\b([0-3]?\d)[/.\-]([01]?\d)[/.\-]((?:20)?\d{2})\b"
    for match in re.finditer(date_pattern, text):
        day, month, year = match.groups()
        year = "20" + year if len(year) == 2 else year
        try:
            parsed = datetime(int(year), int(month), int(day)).date().isoformat()
            candidates["dates"].append({"value": parsed, "source": match.group(0)})
        except ValueError:
            continue
    if candidates["dates"]:
        fields["expense_date"] = candidates["dates"][0]["value"]
        confidence["expense_date"] = 0.9 if len(candidates["dates"]) == 1 else 0.7

    # OCR engines occasionally omit a trailing zero ("23,4" for "23,40").
    amount_re = re.compile(r"(?<!\d)(\d{1,6}(?:[.,]\d{1,2}))(?!\d)")
    labelled = []
    ignored_labels = ("SUBTOTALE", "SUBTOTAL", "IVA", "TAX", "RESTO", "CHANGE")
    total_labels = ("TOTALE", "TOTAL", "IMPORTO", "AMOUNT", "PAGATO", "PAID")
    for index, line in enumerate(lines):
        for match in amount_re.finditer(line):
            value = _decimal(match.group(1))
            if value is None:
                continue
            item = {"value": value, "source": line[:240], "line": index + 1}
            candidates["amounts"].append(item)
            normalized = line.upper()
            has_total_label = any(label in normalized for label in total_labels)
            has_ignored_label = any(label in normalized for label in ignored_labels)
            if has_total_label and not has_ignored_label:
                labelled.append(item)
    if labelled:
        fields["document_total"] = labelled[-1]["value"]
        confidence["document_total"] = 0.92 if len(labelled) == 1 else 0.78
    if "€" in text or re.search(r"\bEUR\b", upper):
        fields["currency"] = "EUR"
        confidence["currency"] = 0.98
    elif re.search(r"\bUSD\b|\$", upper):
        fields["currency"] = "USD"
        confidence["currency"] = 0.95
    elif re.search(r"\bGBP\b|£", upper):
        fields["currency"] = "GBP"
        confidence["currency"] = 0.95

    noise = re.compile(r"^(SCONTRINO|RICEVUTA|RECEIPT|DOCUMENTO|DATA\b|DATE\b)", re.I)
    merchant = next((line for line in lines[:6] if not noise.search(line) and len(line) > 2), None)
    if merchant:
        fields["merchant"] = merchant[:200]
        confidence["merchant"] = 0.78 if (ocr_confidence or 0) >= 0.75 else 0.6

    if any(word in upper for word in ("RISTORANTE", "TRATTORIA", "CAFFE", "CAFFÈ", "RESTAURANT")):
        fields.update(category="Ristorazione", document_type="receipt")
    elif any(word in upper for word in ("POS", "BANCOMAT", "CARTA", "CARD PAYMENT")):
        fields["document_type"] = "pos_receipt"
    elif any(word in upper for word in ("TRENO", "TRAIN", "FRECCIAROSSA", "ITALO", "TRENITALIA")):
        fields.update(category="Trasporto ferroviario", document_type="rail_ticket")
        route = re.search(
            r"(?:DA|FROM)\s+([A-ZÀ-Ü .'-]{2,40})\s+(?:A|TO)\s+([A-ZÀ-Ü .'-]{2,40})",
            upper,
        )
        if route:
            fields["departure"] = route.group(1).strip()
            fields["arrival"] = route.group(2).strip()
        times = re.findall(r"\b([01]?\d|2[0-3]):([0-5]\d)\b", text)
        if times:
            fields["departure_time"] = ":".join(times[0])
        if len(times) > 1:
            fields["arrival_time"] = ":".join(times[1])
    else:
        fields["document_type"] = "other"
    if "document_total" in fields and fields.get("currency") and len(labelled) == 1:
        fields["personally_paid"] = fields["document_total"]
        fields["reimbursement_claimed"] = fields["document_total"]
        confidence["personally_paid"] = confidence["document_total"]
        confidence["reimbursement_claimed"] = confidence["document_total"]
    return fields, confidence, candidates


class LocalDocumentExtractor(DocumentExtractor):
    def extract(self, body: bytes, media_type: str) -> tuple[dict, dict, dict, str]:
        native_text = ""
        page_count = 1
        if media_type == "application/pdf":
            reader = PdfReader(BytesIO(body))
            page_count = len(reader.pages)
            native_text = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if native_text:
            fields, confidence, candidates = _parse(native_text, None)
            provenance = {
                "method": "native_pdf",
                "pages": page_count,
                "candidates": candidates,
            }
            return fields, confidence, provenance, native_text

        if not shutil.which("tesseract"):
            raise ExtractionError("OCR_ENGINE_NOT_INSTALLED")
        results = []
        with tempfile.TemporaryDirectory(prefix="missioni-ocr-") as tmp:
            directory = Path(tmp)
            if media_type == "application/pdf":
                pdf = directory / "input.pdf"
                pdf.write_bytes(body)
                try:
                    poppler = shutil.which("pdftoppm")
                    if not poppler:
                        raise ExtractionError("PDF_RENDERER_NOT_INSTALLED")
                    subprocess.run(  # noqa: S603 - fixed trusted executable and arguments
                        [
                            poppler,
                            "-png",
                            "-r",
                            "200",
                            "-f",
                            "1",
                            "-l",
                            str(page_count),
                            str(pdf),
                            str(directory / "scan"),
                        ],
                        check=True,
                        capture_output=True,
                        timeout=45,
                    )
                except (FileNotFoundError, subprocess.SubprocessError) as exc:
                    raise ExtractionError("PDF_RENDER_FAILED") from exc
                images = [Image.open(path) for path in sorted(directory.glob("scan-*.png"))]
            else:
                images = [Image.open(BytesIO(body))]
            for number, image in enumerate(images, 1):
                results.append(_run_tesseract(image, directory, number))
        raw_text = "\n\n".join(result.text for result in results).strip()
        available = [x.mean_confidence for x in results if x.mean_confidence is not None]
        mean = round(sum(available) / len(available), 3) if available else None
        fields, confidence, candidates = _parse(raw_text, mean)
        return fields, confidence, {
            "method": "local_ocr",
            "engine": self.version,
            "languages": ["ita", "eng"],
            "pages": len(results),
            "mean_word_confidence": mean,
            "words": [word for result in results for word in result.words],
            "candidates": candidates,
        }, raw_text


def extractor() -> DocumentExtractor:
    # External providers remain deliberately absent and disabled.
    return LocalDocumentExtractor()
