# Missioni DIST — Sprint A

Vertical slice per preparare richieste di autorizzazione senza modificare i processi amministrativi. Il repository e la demo usano esclusivamente dati sintetici.

## Stato verificato

Implementati: login locale Argon2id con sessione revocabile, CSRF e rate limit persistente; reset amministrato; isolamento per-oggetto; export/cancellazione; retention verificabile; CRUD missione con più mezzi di trasporto e date civili; PDF/UA-1 e DOCX; protocollo manuale; PWA italiana; PostgreSQL/MinIO e controlli CI. Lo sprint **non è dichiarato completo** finché NVDA, VoiceOver, PAC e le decisioni Ateneo/DPO in `docs/OPEN_QUESTIONS.md` non sono registrati con evidenza.

Non è una certificazione GDPR/WCAG. Base giuridica, DPIA, retention definitiva, accettazione documenti e quadro normativo devono essere verificati con Ateneo/DPO/IT prima di dati reali o rilascio pubblico.

## Avvio

```bash
docker compose up --build
```

UI: `http://localhost:5173`; health: `http://localhost:5173/health`; OpenAPI: `http://localhost:5173/api/docs`.

Credenziali demo sintetiche: `richiedente@example.org` / `Demo-Richiedente-2026!`. Scenario: accesso → nuova missione → scarica PDF/DOCX → registra numero/data di protocollo ricevuti.

## Contratto missione Sprint A

`planned_start` e `planned_end` sono stringhe ISO 8601 `YYYY-MM-DD` con formato OpenAPI `date`: non contengono orario e non subiscono conversioni di fuso. `transport_modes` è un elenco non vuoto, senza duplicati, composto da `Aereo`, `Treno`, `Auto a noleggio`, `Auto personale` e `Auto dipartimentale`.

Per compatibilità transitoria l'API accetta ancora `transport_mode` singolo e lo restituisce come proiezione del primo mezzo. I nuovi client devono usare `transport_modes`. La migrazione `0003` mantiene il campo storico e copia ogni valore preesistente nel nuovo elenco senza eliminare missioni.

## Verifica locale

```bash
python3 scripts/check_public_repo.py
cd backend && pytest && ruff check .
cd ../frontend && npm ci && npm run lint && npm run build && npm run test:e2e
docker compose up --build -d
curl -fsS http://localhost:5173/health
```

Policy e limitazioni: `docs/PUBLIC_REPO_POLICY.md`, `docs/PRIVACY_SECURITY.md`, `docs/OPEN_QUESTIONS.md`.
