from html import escape
from io import BytesIO

from docx import Document
from weasyprint import HTML

from .models import Mission, User


def lines(m: Mission, u: User):
    return [
        "Richiesta di autorizzazione alla missione",
        f"Richiedente: {u.name}",
        f"Destinazione: {m.destination}, {m.country}",
        f"Periodo: {m.planned_start:%d/%m/%Y} – {m.planned_end:%d/%m/%Y}",
        f"Motivazione: {m.purpose}",
        f"Mezzi di trasporto: {', '.join(m.transport_modes)}",
        f"Fondo: {m.fund_code}",
        "Documento generato dall'applicazione — non protocollato",
    ]


def docx(m: Mission, u: User) -> bytes:
    d = Document()
    d.core_properties.title = "Richiesta di autorizzazione alla missione"
    d.core_properties.language = "it-IT"
    d.add_heading(lines(m, u)[0], 0)
    for line in lines(m, u)[1:]:
        d.add_paragraph(line)
    b = BytesIO()
    d.save(b)
    return b.getvalue()


def pdf(m: Mission, u: User) -> bytes:
    values = lines(m, u)
    rows = "".join(
        "<div><dt>{}</dt><dd>{}</dd></div>".format(
            escape(item.split(":", 1)[0]), escape(item.split(":", 1)[1].strip())
        )
        for item in values[1:-1]
    )
    html = f"""<!doctype html><html lang="it"><head>
      <meta charset="utf-8"><title>{escape(values[0])}</title>
      <meta name="author" content="Missioni DIST">
      <style>@page{{size:A4;margin:22mm}} body{{font:12pt sans-serif;line-height:1.5}}
      h1{{font-size:20pt}} dl div{{margin:.6rem 0}} dt{{font-weight:bold}} dd{{margin:0}}
      .warning{{border:2px solid #333;padding:8px}}</style></head><body>
      <main><h1>{escape(values[0])}</h1><dl>{rows}</dl>
      <p class="warning"><strong>Stato:</strong> {escape(values[-1])}</p></main>
      </body></html>"""
    return HTML(string=html).write_pdf(pdf_variant="pdf/ua-1")
