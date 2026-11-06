import csv
import hashlib
import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from openpyxl import load_workbook
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pypdf import PdfReader
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .auth import current_user
from .config import settings
from .db import get_db
from .extraction import extractor
from .main_helpers import owned_mission
from .models import (
    AllocationStatus,
    AuditEvent,
    BankImport,
    BankTransaction,
    DocumentExtraction,
    DocumentStatus,
    Expense,
    ExpenseAllocation,
    ExpenseStatus,
    ReceiptDocument,
    User,
)
from .object_store import store

router = APIRouter(prefix="/api/v1")
ALLOWED = {"image/jpeg", "image/png", "image/webp", "application/pdf"}


def actual_type(body: bytes) -> str | None:
    if body.startswith(b"%PDF-"):
        return "application/pdf"
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"RIFF") and body[8:12] == b"WEBP":
        return "image/webp"
    return None


def document_out(doc: ReceiptDocument, db: Session) -> dict:
    extraction = db.scalar(
        select(DocumentExtraction)
        .where(DocumentExtraction.document_id == doc.id)
        .order_by(DocumentExtraction.created_at.desc())
    )
    return {
        "id": doc.id,
        "mission_id": doc.mission_id,
        "expense_id": doc.expense_id,
        "status": doc.status.value,
        "filename": doc.original_filename,
        "media_type": doc.media_type,
        "size_bytes": doc.size_bytes,
        "sha256": doc.sha256,
        "proposed_fields": extraction.proposed_fields if extraction else {},
        "confidences": extraction.confidences if extraction else {},
        "extraction_error": extraction.error_code if extraction else None,
    }


def owned_document(did: str, db: Session, user: User) -> ReceiptDocument:
    doc = db.scalar(
        select(ReceiptDocument).where(
            ReceiptDocument.id == did, ReceiptDocument.owner_id == user.id
        )
    )
    if not doc:
        raise HTTPException(404, "Documento non trovato")
    return doc


@router.post("/missions/{mid}/documents", status_code=201)
async def upload_document(
    mid: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned_mission(mid, db, user, write=True)
    filename = request.headers.get("x-filename", "documento")[:255]
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > settings().max_upload_bytes:
            raise HTTPException(413, "Documento troppo grande")
        chunks.append(chunk)
    body = b"".join(chunks)
    media_type = actual_type(body)
    if not body or media_type not in ALLOWED:
        raise HTTPException(415, "Formato o contenuto del documento non valido")
    pages = None
    if media_type == "application/pdf":
        try:
            reader = PdfReader(BytesIO(body), strict=True)
            pages = len(reader.pages)
            if pages > settings().max_pdf_pages:
                raise HTTPException(413, "Il PDF contiene troppe pagine")
            if reader.is_encrypted:
                raise HTTPException(422, "PDF cifrato non supportato")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(422, "PDF non integro") from exc
    else:
        try:
            image = Image.open(BytesIO(body))
            image.verify()
            if image.width * image.height > 40_000_000:
                raise HTTPException(413, "Immagine con dimensioni eccessive")
        except HTTPException:
            raise
        except (Image.DecompressionBombError, UnidentifiedImageError, OSError) as exc:
            raise HTTPException(422, "Immagine non integra") from exc
    digest = hashlib.sha256(body).hexdigest()
    existing = db.scalar(
        select(ReceiptDocument).where(
            ReceiptDocument.owner_id == user.id,
            ReceiptDocument.mission_id == mid,
            ReceiptDocument.sha256 == digest,
        )
    )
    if existing:
        return document_out(existing, db)
    key = f"{user.id}/{mid}/{uuid.uuid4()}"
    doc = ReceiptDocument(
        owner_id=user.id,
        mission_id=mid,
        object_key=key,
        original_filename=filename,
        media_type=media_type,
        size_bytes=size,
        sha256=digest,
        page_count=pages,
    )
    db.add(doc)
    db.flush()
    try:
        store().put(key, body, media_type)
        doc.status = DocumentStatus.STORED
        db.add(AuditEvent(actor_id=user.id, mission_id=mid, action="receipt.stored"))
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(503, "Salvataggio originale non disponibile; riprovare") from exc
    return document_out(doc, db)


@router.get("/missions/{mid}/documents")
def list_documents(mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_mission(mid, db, user)
    return [
        document_out(d, db)
        for d in db.scalars(
            select(ReceiptDocument)
            .where(ReceiptDocument.mission_id == mid, ReceiptDocument.owner_id == user.id)
            .order_by(ReceiptDocument.created_at.desc())
        )
    ]


@router.get("/documents/{did}/content")
def document_content(did: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = owned_document(did, db, user)
    return Response(
        store().get(doc.object_key),
        media_type=doc.media_type,
        headers={"Content-Disposition": "inline", "Cache-Control": "private, no-store"},
    )


@router.post("/documents/{did}/extract")
def extract_document(did: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    doc = owned_document(did, db, user)
    doc.status = DocumentStatus.PROCESSING
    db.commit()
    try:
        engine = extractor()
        fields, confidences, provenance, raw_text = engine.extract(
            store().get(doc.object_key), doc.media_type
        )
        doc.status = DocumentStatus.EXTRACTED if fields else DocumentStatus.EXTRACTION_FAILED
        db.add(
            DocumentExtraction(
                document_id=doc.id,
                provider=engine.provider,
                provider_version=engine.version,
                raw_text=raw_text,
                proposed_fields=fields,
                confidences=confidences,
                provenance=provenance,
                error_code=None if fields else "NO_TEXT_OR_FIELDS",
            )
        )
    except Exception as exc:
        doc.status = DocumentStatus.EXTRACTION_FAILED
        db.add(
            DocumentExtraction(
                document_id=doc.id,
                provider=extractor().provider,
                provider_version=extractor().version,
                raw_text=None,
                proposed_fields={},
                confidences={},
                provenance={},
                error_code=str(exc)[:80] or "LOCAL_EXTRACTION_FAILED",
            )
        )
    db.add(AuditEvent(actor_id=user.id, mission_id=doc.mission_id, action="receipt.extracted"))
    db.commit()
    return document_out(doc, db)


class ExpenseIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_ids: list[str] = Field(default_factory=list)
    expense_date: date | None = None
    merchant: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=80)
    document_total: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern="^[A-Z]{3}$")
    personally_paid: Decimal | None = Field(default=None, ge=0)
    reimbursement_claimed: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    verify_now: bool = False

    @model_validator(mode="after")
    def amounts(self):
        if (
            self.personally_paid is not None
            and self.document_total is not None
            and self.personally_paid > self.document_total
        ):
            raise ValueError("La quota personale non può superare il totale documento")
        if (
            self.reimbursement_claimed is not None
            and self.personally_paid is not None
            and self.reimbursement_claimed > self.personally_paid
        ):
            raise ValueError("La quota richiesta non può superare quanto pagato personalmente")
        return self


def expense_out(e: Expense, db: Session) -> dict:
    def money(value):
        return format(value, ".2f") if value is not None else None

    return {
        "id": e.id,
        "mission_id": e.mission_id,
        "status": e.status.value,
        "expense_date": e.expense_date,
        "merchant": e.merchant,
        "description": e.description,
        "category": e.category,
        "document_total": money(e.document_total),
        "currency": e.currency,
        "personally_paid": money(e.personally_paid),
        "reimbursement_claimed": money(e.reimbursement_claimed),
        "notes": e.notes,
        "document_ids": list(
            db.scalars(select(ReceiptDocument.id).where(ReceiptDocument.expense_id == e.id))
        ),
    }


@router.post("/missions/{mid}/expenses", status_code=201)
def create_expense(
    mid: str, data: ExpenseIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned_mission(mid, db, user, write=True)
    docs = (
        list(
            db.scalars(
                select(ReceiptDocument).where(
                    ReceiptDocument.id.in_(data.document_ids),
                    ReceiptDocument.owner_id == user.id,
                    ReceiptDocument.mission_id == mid,
                )
            )
        )
        if data.document_ids
        else []
    )
    if len(docs) != len(set(data.document_ids)):
        raise HTTPException(404, "Documento non trovato")
    values = data.model_dump(exclude={"document_ids", "verify_now"})
    status = ExpenseStatus.VERIFIED if data.verify_now else ExpenseStatus.NEEDS_REVIEW
    if data.verify_now and not all(
        [
            data.expense_date,
            data.merchant,
            data.document_total is not None,
            data.currency,
            data.personally_paid is not None,
            data.reimbursement_claimed is not None,
        ]
    ):
        raise HTTPException(422, "Completare i campi essenziali prima della conferma")
    e = Expense(
        **values,
        owner_id=user.id,
        mission_id=mid,
        status=status,
        confirmed_fields=list(values) if data.verify_now else [],
    )
    db.add(e)
    db.flush()
    for doc in docs:
        doc.expense_id = e.id
    db.add(
        AuditEvent(
            actor_id=user.id,
            mission_id=mid,
            action="expense.verified" if data.verify_now else "expense.deferred",
        )
    )
    db.commit()
    return expense_out(e, db)


@router.get("/missions/{mid}/expenses")
def list_expenses(mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_mission(mid, db, user)
    return [
        expense_out(e, db)
        for e in db.scalars(
            select(Expense)
            .where(Expense.mission_id == mid, Expense.owner_id == user.id)
            .order_by(Expense.created_at.desc())
        )
    ]


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    raise ValueError("data non riconosciuta")


def parse_amount(value) -> Decimal:
    raw = re.sub(r"[^0-9,.-]", "", str(value)).strip()
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", ".")
    return abs(Decimal(raw)).quantize(Decimal("0.01"))


def rows_from_bank(body: bytes, filename: str) -> list[dict]:
    if filename.lower().endswith(".xlsx"):
        sheet = load_workbook(BytesIO(body), read_only=True, data_only=True).active
        rows = list(sheet.values)
        if not rows:
            return []
        headers = [str(x or "").strip().lower() for x in rows[0]]
        return [
            dict(zip(headers, row, strict=False))
            for row in rows[1:]
            if any(x is not None for x in row)
        ]
    text = body.decode("utf-8-sig")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    return list(csv.DictReader(StringIO(text), dialect=dialect))


def pick_column(normalized: dict, aliases: dict, name: str, default=None):
    return next(
        (
            normalized[key]
            for key in aliases[name]
            if key in normalized and normalized[key] not in (None, "")
        ),
        default,
    )


@router.post("/missions/{mid}/bank-imports", status_code=201)
async def import_bank(
    mid: str, request: Request, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned_mission(mid, db, user, write=True)
    body = await request.body()
    filename = request.headers.get("x-filename", "movimenti.csv")
    if len(body) > settings().max_upload_bytes:
        raise HTTPException(413, "File troppo grande")
    digest = hashlib.sha256(body).hexdigest()
    previous = db.scalar(
        select(BankImport).where(
            BankImport.owner_id == user.id,
            BankImport.mission_id == mid,
            BankImport.file_sha256 == digest,
        )
    )
    if previous:
        return {
            "id": previous.id,
            "duplicate": True,
            "transactions": list(
                db.scalars(
                    select(BankTransaction.id).where(BankTransaction.import_id == previous.id)
                )
            ),
        }
    try:
        rows = rows_from_bank(body, filename)
    except Exception as exc:
        raise HTTPException(422, "Estratto conto non leggibile") from exc
    if not rows:
        raise HTTPException(422, "Nessun movimento trovato")
    imp = BankImport(
        owner_id=user.id,
        mission_id=mid,
        file_sha256=digest,
        institution=request.headers.get("x-bank-institution", "")[:120] or None,
        account_reference_masked=request.headers.get("x-account-reference", "")[:80] or None,
    )
    db.add(imp)
    db.flush()
    created = []
    aliases = {
        "operation_date": ("data operazione", "data", "operation_date"),
        "booking_date": ("data contabilizzazione", "booking_date"),
        "description": ("descrizione", "description", "causale"),
        "amount": ("importo", "amount"),
        "currency": ("valuta", "currency"),
        "reference": ("riferimento", "reference", "id"),
    }
    for row in rows:
        normalized = {str(k).strip().lower(): v for k, v in row.items()}
        operation_raw = pick_column(normalized, aliases, "operation_date")
        booking_raw = pick_column(normalized, aliases, "booking_date")
        description_raw = pick_column(normalized, aliases, "description", "")
        amount_raw = pick_column(normalized, aliases, "amount")
        currency_raw = pick_column(normalized, aliases, "currency", "EUR")
        reference_raw = pick_column(normalized, aliases, "reference")
        try:
            tx = BankTransaction(
                import_id=imp.id,
                owner_id=user.id,
                operation_date=parse_date(operation_raw),
                booking_date=parse_date(booking_raw) if booking_raw else None,
                full_description=str(description_raw).strip(),
                amount=parse_amount(amount_raw),
                currency=str(currency_raw).upper()[:3],
                external_reference=str(reference_raw)[:160] if reference_raw else None,
            )
        except (ValueError, InvalidOperation, TypeError) as exc:
            raise HTTPException(422, "Colonne bancarie non valide") from exc
        if not tx.full_description:
            raise HTTPException(422, "Descrizione bancaria mancante")
        db.add(tx)
        db.flush()
        created.append(tx.id)
    db.add(AuditEvent(actor_id=user.id, mission_id=mid, action="bank.imported"))
    db.commit()
    return {"id": imp.id, "duplicate": False, "transactions": created}


@router.get("/missions/{mid}/bank-transactions")
def bank_transactions(mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_mission(mid, db, user)
    q = (
        select(BankTransaction)
        .join(BankImport)
        .where(BankImport.mission_id == mid, BankTransaction.owner_id == user.id)
    )
    return [
        {
            "id": t.id,
            "operation_date": t.operation_date,
            "booking_date": t.booking_date,
            "full_description": t.full_description,
            "amount": format(t.amount, ".2f"),
            "currency": t.currency,
            "selected": t.selected,
        }
        for t in db.scalars(q)
    ]


def normalized_words(value: str | None) -> set[str]:
    return {
        word for word in re.sub(r"[^A-Z0-9 ]", " ", (value or "").upper()).split() if len(word) > 2
    }


@router.get("/missions/{mid}/matching-suggestions")
def matching_suggestions(
    mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned_mission(mid, db, user)
    transactions = list(
        db.scalars(
            select(BankTransaction)
            .join(BankImport)
            .where(BankImport.mission_id == mid, BankTransaction.owner_id == user.id)
        )
    )
    expenses = list(
        db.scalars(select(Expense).where(Expense.mission_id == mid, Expense.owner_id == user.id))
    )
    suggestions = []
    for transaction in transactions:
        for expense in expenses:
            target = (
                expense.reimbursement_claimed or expense.personally_paid or expense.document_total
            )
            if target is None or target != abs(transaction.amount):
                continue
            date_distance = (
                abs((transaction.operation_date - expense.expense_date).days)
                if expense.expense_date
                else 99
            )
            words = normalized_words(transaction.full_description) & normalized_words(
                expense.merchant
            )
            if date_distance <= settings().bank_match_date_tolerance_days or words:
                confidence = Decimal("0.75")
                if date_distance <= 3:
                    confidence += Decimal("0.10")
                if words:
                    confidence += Decimal("0.10")
                suggestions.append(
                    {
                        "transaction_id": transaction.id,
                        "expense_id": expense.id,
                        "allocated_amount": format(target, ".2f"),
                        "confidence": format(min(confidence, Decimal("0.95")), ".2f"),
                        "requires_confirmation": True,
                        "rationale": "importo; data flessibile; esercente normalizzato",
                    }
                )
        # One movement may cover multiple expenses (e.g. two tickets bought together).
        for left_index, left in enumerate(expenses):
            left_target = left.reimbursement_claimed or left.personally_paid or left.document_total
            if left_target is None:
                continue
            for right in expenses[left_index + 1 :]:
                right_target = (
                    right.reimbursement_claimed or right.personally_paid or right.document_total
                )
                if (
                    right_target is None
                    or left.currency != transaction.currency
                    or right.currency != transaction.currency
                ):
                    continue
                if left_target + right_target != abs(transaction.amount):
                    continue
                dated = [e.expense_date for e in (left, right) if e.expense_date]
                distance = min(
                    (abs((transaction.operation_date - value).days) for value in dated),
                    default=99,
                )
                if distance > settings().bank_match_date_tolerance_days:
                    continue
                suggestions.append(
                    {
                        "transaction_id": transaction.id,
                        "expense_ids": [left.id, right.id],
                        "allocations": [
                            {"expense_id": left.id, "amount": format(left_target, ".2f")},
                            {"expense_id": right.id, "amount": format(right_target, ".2f")},
                        ],
                        "requires_confirmation": True,
                        "rationale": (
                            "la somma delle due quote coincide con il movimento; "
                            f"data entro {settings().bank_match_date_tolerance_days} giorni"
                        ),
                    }
                )
    return suggestions


class AllocationIn(BaseModel):
    transaction_id: str
    expense_id: str
    allocated_amount: Decimal = Field(gt=0)
    confirm: bool = False


@router.post("/missions/{mid}/allocations", status_code=201)
def allocate(
    mid: str, data: AllocationIn, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    owned_mission(mid, db, user, write=True)
    tx = db.scalar(
        select(BankTransaction)
        .join(BankImport)
        .where(
            BankTransaction.id == data.transaction_id,
            BankTransaction.owner_id == user.id,
            BankImport.mission_id == mid,
        )
    )
    expense = db.scalar(
        select(Expense).where(
            Expense.id == data.expense_id, Expense.owner_id == user.id, Expense.mission_id == mid
        )
    )
    if not tx or not expense:
        raise HTTPException(404, "Movimento o spesa non trovato")
    active = (AllocationStatus.SUGGESTED, AllocationStatus.CONFIRMED)
    tx_used = db.scalar(
        select(func.coalesce(func.sum(ExpenseAllocation.allocated_amount), 0)).where(
            ExpenseAllocation.transaction_id == tx.id, ExpenseAllocation.status.in_(active)
        )
    )
    expense_used = db.scalar(
        select(func.coalesce(func.sum(ExpenseAllocation.allocated_amount), 0)).where(
            ExpenseAllocation.expense_id == expense.id, ExpenseAllocation.status.in_(active)
        )
    )
    expense_limit = (
        expense.reimbursement_claimed or expense.personally_paid or expense.document_total
    )
    if (
        data.allocated_amount + tx_used > abs(tx.amount)
        or expense_limit is None
        or data.allocated_amount + expense_used > expense_limit
    ):
        raise HTTPException(409, "Allocazione superiore all'importo disponibile")
    allocation = ExpenseAllocation(
        owner_id=user.id,
        transaction_id=tx.id,
        expense_id=expense.id,
        allocated_amount=data.allocated_amount,
        status=AllocationStatus.CONFIRMED if data.confirm else AllocationStatus.SUGGESTED,
        created_by=user.id,
        rationale="Corrispondenza importo confermata dall'utente"
        if data.confirm
        else "Corrispondenza deterministica da verificare",
    )
    db.add(allocation)
    tx.selected = data.confirm
    db.add(
        AuditEvent(
            actor_id=user.id,
            mission_id=mid,
            action="allocation.confirmed" if data.confirm else "allocation.suggested",
        )
    )
    db.commit()
    return {
        "id": allocation.id,
        "status": allocation.status.value,
        "allocated_amount": format(allocation.allocated_amount, ".2f"),
    }


@router.delete("/allocations/{allocation_id}", status_code=204)
def revoke_allocation(
    allocation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    allocation = db.scalar(
        select(ExpenseAllocation).where(
            ExpenseAllocation.id == allocation_id,
            ExpenseAllocation.owner_id == user.id,
        )
    )
    if not allocation:
        raise HTTPException(404, "Abbinamento non trovato")
    allocation.status = AllocationStatus.REVOKED
    transaction = db.get(BankTransaction, allocation.transaction_id)
    if transaction:
        still_confirmed = db.scalar(
            select(func.count())
            .select_from(ExpenseAllocation)
            .where(
                ExpenseAllocation.transaction_id == transaction.id,
                ExpenseAllocation.status == AllocationStatus.CONFIRMED,
                ExpenseAllocation.id != allocation.id,
            )
        )
        transaction.selected = bool(still_confirmed)
    db.add(
        AuditEvent(
            actor_id=user.id,
            mission_id=db.get(Expense, allocation.expense_id).mission_id,
            action="allocation.revoked",
        )
    )
    db.commit()


@router.get("/missions/{mid}/bank-export")
def selective_export(mid: str, db: Session = Depends(get_db), user: User = Depends(current_user)):
    owned_mission(mid, db, user)
    rows = list(
        db.scalars(
            select(BankTransaction)
            .join(BankImport)
            .where(
                BankImport.mission_id == mid,
                BankTransaction.owner_id == user.id,
                BankTransaction.selected.is_(True),
            )
        )
    )
    return {
        "title": "Estratto conto — movimenti relativi alla missione",
        "disclaimer": (
            "Estratto selettivo elaborato dall'applicazione da dati esportati dalla banca; "
            "non è un documento bancario originale o certificato."
        ),
        "movements": [
            {
                "operation_date": t.operation_date,
                "booking_date": t.booking_date,
                "full_description": t.full_description,
                "amount": format(t.amount, ".2f"),
                "currency": t.currency,
            }
            for t in rows
        ],
    }
