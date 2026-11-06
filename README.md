# Missioni DIST — Sprint C.1 (incrementale su Sprint A e C)

Vertical slice per preparare richieste di autorizzazione senza modificare i processi amministrativi. Il repository e la demo usano esclusivamente dati sintetici.

## Stato verificato

Implementati: il percorso Sprint A esistente; acquisizione JPEG/PNG/WebP/PDF; originale privato in MinIO prima dell'estrazione; deduplicazione SHA-256; testo PDF nativo e OCR locale Tesseract italiano/inglese realmente installato nel container; proposta precompilata e verifica immediata/differita; più documenti per spesa; quote personali e richieste distinte; import CSV/XLSX; matching suggerito (anche 1:N) sempre confermato dall'utente; allocazioni many-to-many senza sovra-allocazione; estratto selettivo. L'AI esterna è disabilitata e non viene invocata.

Sprint A resta **non dichiarato completo** finché NVDA, VoiceOver, PAC e le decisioni Ateneo/DPO in `docs/OPEN_QUESTIONS.md` non sono registrati. Sprint C.1 non costituisce certificazione GDPR/WCAG; limiti, benchmark ed evidenze sono in `docs/SPRINT_C1_VERIFICATION.md`.

Non è una certificazione GDPR/WCAG. Base giuridica, DPIA, retention definitiva, accettazione documenti e quadro normativo devono essere verificati con Ateneo/DPO/IT prima di dati reali o rilascio pubblico.

## Avvio

```bash
docker compose up --build
```

UI: `http://localhost:5173`; health: `http://localhost:5173/health`; OpenAPI: `http://localhost:5173/api/docs`.

Credenziali demo sintetiche: `richiedente@example.org` / `Demo-Richiedente-2026!`. Scenario C: accesso → missione → Giustificativi → foto/file → verifica dati → eventuale estratto CSV/XLSX → conferma abbinamenti.

## Contratto acquisizione Sprint C

Gli endpoint documentali accettano il file come corpo della richiesta con `Content-Type` reale e `X-Filename`; il backend verifica magic bytes, integrità, dimensione e pagine. L'oggetto usa un nome casuale in bucket privato. `receipt_documents`, `document_extractions`, `expenses`, `bank_transactions` ed `expense_allocations` restano separati: una nuova estrazione non sovrascrive i campi confermati.

Configurazione MinIO: `OBJECT_STORE_ENDPOINT`, `OBJECT_STORE_BUCKET`, `OBJECT_STORE_ACCESS_KEY`, `OBJECT_STORE_SECRET_KEY`. Senza credenziali viene usato soltanto in sviluppo/test lo storage locale ignorato da Git. `OPENAI_EXTRACTION_ENABLED=false` e `OPENAI_DATA_PROCESSING_AUTHORIZED=false` sono i default; non è presente un adapter cloud attivo.

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
docker run --rm --read-only --tmpfs /tmp -v "$PWD/backend/tests:/bench:ro" missioni-dist-backend:latest python /bench/benchmark_ocr.py
```

Policy e limitazioni: `docs/PUBLIC_REPO_POLICY.md`, `docs/PRIVACY_SECURITY.md`, `docs/OPEN_QUESTIONS.md`.

## Deployment istituzionale (preparazione, non go-live)

Gli artefatti per Docker Compose su server Uniparthenope sono in `compose.production.yml` e `ops/production/`. La produzione usa un solo ingresso applicativo: FastAPI serve anche il bundle frontend e resta dietro il reverse proxy HTTPS istituzionale; PostgreSQL e MinIO non pubblicano porte. Migrazioni, backup cifrato e deploy sono fasi manuali esplicite e non caricano dati demo.

La procedura richiede ancora parametri e approvazioni ICT/DPO. Consultare `ops/production/README.md`, `ops/production/ict-handoff.md` e `DEPLOYMENT_UNIPARTHENOPE_VERIFICATION.md`. Nessun dato reale deve essere trattato prima del release gate istituzionale.
