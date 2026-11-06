from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance, ImageFont
from reportlab.pdfgen.canvas import Canvas
from test_sprint_a import MISSION


def make_mission(client, auth):
    csrf = auth(client, "uno@example.org", "Password-uno!")
    headers = {"X-CSRF-Token": csrf}
    mid = client.post("/api/v1/missions", json=MISSION, headers=headers).json()["id"]
    return mid, headers


def synthetic_pdf():
    output = BytesIO()
    canvas = Canvas(output)
    canvas.drawString(72, 760, "TRENI SINTETICI SPA")
    canvas.drawString(72, 730, "Data 10/02/2027 Totale EUR 52,00")
    canvas.save()
    return output.getvalue()


def synthetic_png():
    output = BytesIO()
    Image.new("RGB", (40, 40), "white").save(output, "PNG")
    return output.getvalue()


def synthetic_receipt_photo(total="23,40", date="10/02/2027"):
    image = Image.new("RGB", (1200, 1600), (218, 214, 205))
    receipt = Image.new("RGB", (820, 1250), "white")
    draw = ImageDraw.Draw(receipt)
    try:
        font = ImageFont.truetype("DejaVuSansMono.ttf", 42)
        bold = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 48)
    except OSError:
        font = bold = ImageFont.load_default()
    rows = [
        ("TRATTORIA VESUVIO", bold),
        ("SCONTRINO SINTETICO", font),
        (f"DATA {date}", font),
        ("PASTA                 12,00", font),
        ("ACQUA                  3,00", font),
        ("SERVIZIO               8,40", font),
        ("SUBTOTALE             19,18", font),
        ("IVA                    4,22", font),
        (f"TOTALE EUR            {total}", bold),
    ]
    y = 120
    for value, row_font in rows:
        draw.text((65, y), value, fill="black", font=row_font)
        y += 105
    receipt = receipt.rotate(1.2, expand=True, fillcolor="white")
    image.paste(receipt, (170, 130))
    image = ImageEnhance.Brightness(image).enhance(0.83)
    output = BytesIO()
    image.save(output, "JPEG", quality=82)
    return output.getvalue()


def test_document_first_pdf_extract_duplicate_and_partial_share(client, auth):
    mid, headers = make_mission(client, auth)
    body = synthetic_pdf()
    upload_headers = {**headers, "Content-Type": "application/pdf", "X-Filename": "demo.pdf"}
    uploaded = client.post(
        f"/api/v1/missions/{mid}/documents", content=body, headers=upload_headers
    )
    assert uploaded.status_code == 201
    assert uploaded.json()["status"] == "STORED"
    did = uploaded.json()["id"]
    repeated = client.post(
        f"/api/v1/missions/{mid}/documents", content=body, headers=upload_headers
    )
    assert repeated.json()["id"] == did
    extracted = client.post(f"/api/v1/documents/{did}/extract", headers=headers)
    assert extracted.json()["proposed_fields"]["document_total"] == "52.00"
    expense = client.post(
        f"/api/v1/missions/{mid}/expenses",
        headers=headers,
        json={
            "document_ids": [did],
            "expense_date": "2027-02-10",
            "merchant": "TRENI SINTETICI SPA",
            "document_total": "52.00",
            "currency": "EUR",
            "personally_paid": "40.00",
            "reimbursement_claimed": "40.00",
            "verify_now": True,
        },
    )
    assert expense.status_code == 201
    assert expense.json()["reimbursement_claimed"] == "40.00"
    # Reprocessing creates another extraction, never overwriting confirmed expense data.
    assert client.post(f"/api/v1/documents/{did}/extract", headers=headers).status_code == 200
    persisted = client.get(f"/api/v1/missions/{mid}/expenses", headers=headers).json()[0]
    assert persisted["merchant"] == "TRENI SINTETICI SPA"
    assert persisted["reimbursement_claimed"] == "40.00"


def test_real_local_ocr_prefills_synthetic_receipt_and_other_user_isolated(client, auth):
    mid, headers = make_mission(client, auth)
    uploaded = client.post(
        f"/api/v1/missions/{mid}/documents",
        content=synthetic_receipt_photo(),
        headers={**headers, "Content-Type": "image/jpeg", "X-Filename": "scontrino.jpg"},
    )
    did = uploaded.json()["id"]
    result = client.post(f"/api/v1/documents/{did}/extract", headers=headers)
    assert result.json()["status"] == "EXTRACTED"
    proposal = result.json()["proposed_fields"]
    assert proposal["merchant"] == "TRATTORIA VESUVIO"
    assert proposal["expense_date"] == "2027-02-10"
    assert proposal["document_total"] == "23.40"
    assert proposal["currency"] == "EUR"
    assert proposal["personally_paid"] == "23.40"
    assert proposal["reimbursement_claimed"] == "23.40"
    assert client.get(f"/api/v1/documents/{did}/content").status_code == 200
    client.post("/api/v1/auth/logout", headers=headers)
    auth(client, "due@example.org", "Password-due!")
    assert client.get(f"/api/v1/documents/{did}/content").status_code == 404


def test_ocr_failure_can_be_deferred_and_two_attachments_make_one_expense(client, auth):
    mid, headers = make_mission(client, auth)
    ids = []
    for name, body, media_type in (
        ("vuoto.png", synthetic_png(), "image/png"),
        ("conto.pdf", synthetic_pdf(), "application/pdf"),
    ):
        uploaded = client.post(
            f"/api/v1/missions/{mid}/documents",
            content=body,
            headers={**headers, "Content-Type": media_type, "X-Filename": name},
        ).json()
        ids.append(uploaded["id"])
    failed = client.post(f"/api/v1/documents/{ids[0]}/extract", headers=headers).json()
    assert failed["status"] == "EXTRACTION_FAILED"
    deferred = client.post(
        f"/api/v1/missions/{mid}/expenses",
        headers=headers,
        json={"document_ids": ids, "verify_now": False},
    )
    assert deferred.status_code == 201
    assert deferred.json()["status"] == "NEEDS_REVIEW"
    assert set(deferred.json()["document_ids"]) == set(ids)
    assert deferred.json()["reimbursement_claimed"] is None


def test_many_expenses_one_transaction_no_overallocation_and_selective_export(client, auth):
    mid, headers = make_mission(client, auth)
    expense_ids = []
    for merchant in ("TRATTA A", "TRATTA B"):
        response = client.post(
            f"/api/v1/missions/{mid}/expenses",
            headers=headers,
            json={
                "expense_date": "2027-02-10",
                "merchant": merchant,
                "document_total": "52.00",
                "currency": "EUR",
                "personally_paid": "52.00",
                "reimbursement_claimed": "52.00",
                "verify_now": True,
            },
        )
        expense_ids.append(response.json()["id"])
    csv_body = (
        "data operazione;data contabilizzazione;descrizione;importo;valuta\n"
        "11/02/2027;12/02/2027;PAGAMENTO COMPLETO DUE BIGLIETTI;104,00;EUR\n"
    ).encode()
    imported = client.post(
        f"/api/v1/missions/{mid}/bank-imports",
        content=csv_body,
        headers={**headers, "Content-Type": "text/csv", "X-Filename": "sintetico.csv"},
    )
    assert imported.status_code == 201
    txid = imported.json()["transactions"][0]
    suggestions = client.get(
        f"/api/v1/missions/{mid}/matching-suggestions", headers=headers
    ).json()
    grouped = next(item for item in suggestions if item.get("expense_ids"))
    assert grouped["transaction_id"] == txid
    assert set(grouped["expense_ids"]) == set(expense_ids)
    assert grouped["requires_confirmation"] is True
    for eid in expense_ids:
        allocation = client.post(
            f"/api/v1/missions/{mid}/allocations",
            headers=headers,
            json={
                "transaction_id": txid,
                "expense_id": eid,
                "allocated_amount": "52.00",
                "confirm": True,
            },
        )
        assert allocation.status_code == 201
    rejected = client.post(
        f"/api/v1/missions/{mid}/allocations",
        headers=headers,
        json={
            "transaction_id": txid,
            "expense_id": expense_ids[0],
            "allocated_amount": "0.01",
            "confirm": True,
        },
    )
    assert rejected.status_code == 409
    export = client.get(f"/api/v1/missions/{mid}/bank-export").json()
    assert len(export["movements"]) == 1
    assert export["movements"][0]["full_description"] == "PAGAMENTO COMPLETO DUE BIGLIETTI"
    duplicate = client.post(
        f"/api/v1/missions/{mid}/bank-imports",
        content=csv_body,
        headers={**headers, "Content-Type": "text/csv", "X-Filename": "sintetico.csv"},
    )
    assert duplicate.json()["duplicate"] is True
