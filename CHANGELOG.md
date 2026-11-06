# Changelog

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
