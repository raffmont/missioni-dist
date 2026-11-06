"""Synthetic-only reproducible OCR benchmark (not collected by pytest)."""

import json
import statistics
import time
from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from app.extraction import extractor


def receipt(angle: float, brightness: float, blur: float) -> bytes:
    background = Image.new("RGB", (1200, 1600), (218, 214, 205))
    paper = Image.new("RGB", (820, 1250), "white")
    draw = ImageDraw.Draw(paper)
    normal = ImageFont.truetype("DejaVuSansMono.ttf", 42)
    bold = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 48)
    rows = [
        ("TRATTORIA VESUVIO", bold),
        ("SCONTRINO SINTETICO", normal),
        ("DATA 10/02/2027", normal),
        ("PASTA                 12,00", normal),
        ("ACQUA                  3,00", normal),
        ("SERVIZIO               8,40", normal),
        ("SUBTOTALE             19,18", normal),
        ("IVA                    4,22", normal),
        ("TOTALE EUR            23,40", bold),
    ]
    y = 120
    for value, font in rows:
        draw.text((65, y), value, fill="black", font=font)
        y += 105
    paper = paper.rotate(angle, expand=True, fillcolor="white")
    background.paste(paper, (max(0, (1200 - paper.width) // 2), 100))
    background = ImageEnhance.Brightness(background).enhance(brightness)
    if blur:
        background = background.filter(ImageFilter.GaussianBlur(blur))
    output = BytesIO()
    background.save(output, "JPEG", quality=80)
    return output.getvalue()


def main() -> None:
    variants = [
        (-2.0, 0.68, 0.0),
        (-1.2, 0.75, 0.3),
        (-0.5, 0.85, 0.0),
        (0.0, 1.00, 0.0),
        (0.5, 0.80, 0.4),
        (1.0, 0.72, 0.0),
        (1.5, 0.90, 0.5),
        (2.0, 0.78, 0.2),
        (-1.8, 0.88, 0.6),
        (-0.8, 0.70, 0.3),
        (0.8, 0.95, 0.0),
        (1.8, 0.82, 0.4),
    ]
    expected = {
        "merchant": "TRATTORIA VESUVIO",
        "expense_date": "2027-02-10",
        "document_total": "23.40",
        "currency": "EUR",
    }
    latencies, correct, failures, corrections = [], {key: 0 for key in expected}, 0, []
    for angle, brightness, blur in variants:
        started = time.perf_counter()
        fields, _, _, _ = extractor().extract(receipt(angle, brightness, blur), "image/jpeg")
        latencies.append((time.perf_counter() - started) * 1000)
        errors = 0
        for key, value in expected.items():
            if fields.get(key) == value:
                correct[key] += 1
            else:
                errors += 1
        corrections.append(errors)
        failures += int(not fields)
    ordered = sorted(latencies)
    result = {
        "samples": len(variants),
        "field_accuracy": {key: round(value / len(variants), 4) for key, value in correct.items()},
        "manual_corrections_per_document_mean": round(statistics.mean(corrections), 3),
        "latency_ms_p50": round(statistics.median(ordered), 1),
        "latency_ms_p95": round(ordered[int(0.95 * (len(ordered) - 1))], 1),
        "failure_rate": round(failures / len(variants), 4),
        "variants": "angle -2..2 deg; brightness 0.68..1.0; Gaussian blur 0..0.6",
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
