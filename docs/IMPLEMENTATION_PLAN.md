# Piano di implementazione

## Ordine vincolante

1. Protezioni repository pubblico: ignore preventivo, policy, scansioni segreti/PII e cronologia, branch protection e dipendenze.
2. Fondazioni privacy/security: threat model, matrice accessi, retention, sessioni, audit minimizzato e separazione ambienti.
3. Sprint A verticale: autenticazione locale, CRUD missioni, rendering DOCX/PDF, protocollo manuale, UI italiana/PWA.
4. Verifica bloccante: test backend/object-level, frontend, E2E, axe, controlli PDF e checklist manuali.

## Dipendenze e rischi

- PostgreSQL e MinIO sono servizi locali Docker; SQLite e filesystem non sono configurazioni di produzione.
- I PDF sono generati come PDF/UA best-effort con metadati e struttura logica; la verifica manuale con PAC/assistive technology rimane obbligatoria.
- Il quadro normativo, la base giuridica, retention definitiva e l'accettazione dei documenti richiedono conferma Ateneo/DPO.
- Nessun documento di riferimento o dato reale entra nel repository, nei log o nella CI.

## Milestone Sprint A

- Gate repository e CI attivi.
- Migrazione e seed esclusivamente sintetico.
- Percorso riproducibile: login → nuova missione → anteprima → DOCX/PDF → protocollo.
- Tutti i controlli automatici superati e verifiche manuali registrate; in caso contrario lo sprint resta aperto.

## Evoluzione interna 0.2.0

- `transport_modes` è il campo canonico multivalore; `transport_mode` resta una proiezione deprecata per compatibilità.
- `planned_start` e `planned_end` sono `DATE` in PostgreSQL e `date` nei contratti Pydantic/OpenAPI.
- La migrazione `0003` aggiunge l'elenco, copia il valore singolo senza perdita e converte le colonne temporali senza cancellare record.
- L'auto personale non attiva dichiarazioni, moduli o rami amministrativi aggiuntivi in Sprint A.
- PDF e DOCX derivano esclusivamente dai dati della missione e mostrano l'intero elenco dei mezzi e date prive di orario.
