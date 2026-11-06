# Changelog

## Sprint C.1 — 2026-11-06

- OCR locale Tesseract 5 italiano/inglese e Poppler installati nel container backend.
- Preprocessing non distruttivo, parser totale/data/valuta/merchant, classificazione e
  proposte ferroviarie; output OCR grezzo separato con migrazione additiva `0005`.
- Precompilazione mobile di spesa e quote, conferma/differimento e più allegati per spesa.
- Matching suggerito per merchant/date/importo e combinazioni 1:N, mai automatico.
- Fixture OCR reale e benchmark sintetico a 12 campioni documentato.

## 0.3.0 — Sprint C: acquisizione intelligente e riconciliazione

- Aggiunta migrazione additiva `0004` per originali, estrazioni, spese, import bancari e allocazioni.
- Aggiunti upload document-first privati MinIO, validazione contenuto, SHA-256 e deduplicazione idempotente.
- Aggiunti parser PDF nativo locale, fallback manuale e UI mobile con anteprima, conferma o verifica differita.
- Aggiunti import CSV/XLSX, allocazioni many-to-many e limite anti-sovra-allocazione.
- Aggiunti isolamento per utente, audit senza contenuti sensibili e test sintetici Sprint C.
- Adapter AI esterno non attivato; nessuna approvazione o responsabilità amministrativa modificata.

## 0.2.0 — Sprint A: mezzi multipli e date civili

- Aggiunta la selezione multipla di Aereo, Treno, Auto a noleggio, Auto personale e Auto dipartimentale.
- Convertite le date previste da timestamp a date civili, senza orario né conversioni di fuso.
- Aggiornati PDF e DOCX per mostrare tutti i mezzi selezionati e le sole date.
- Aggiunta la migrazione Alembic `0003`, che conserva tutte le missioni e proietta ogni mezzo preesistente nel nuovo elenco.
- Mantenuto `transport_mode` come campo API deprecato e proiezione del primo mezzo per i client Sprint A esistenti.
- Aggiunti test API, documentali, Playwright, tastiera e axe WCAG 2.2 AA.

## 0.1.0 — Sprint A (in verifica)

- Protezioni repository pubblico, gate segreti/PII e documentazione privacy/security.
- Autenticazione locale, RBAC/object-level, missioni, autorizzazione PDF/DOCX e protocollo manuale.
- UI accessibile italiana e pipeline axe/Playwright; verifica manuale ancora obbligatoria.
