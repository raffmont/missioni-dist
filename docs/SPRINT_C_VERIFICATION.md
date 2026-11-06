# Rapporto di implementazione e collaudo Sprint C

Data: 6 novembre 2026. Tutti i dati di test sono sintetici.

## Baseline accertata

Il repository conteneva Sprint A e la migrazione `0003`. Sprint B non risultava implementato. PostgreSQL e MinIO erano dichiarati in Compose, ma MinIO non era usato dall'applicazione. Il rapporto precedente mantiene aperte le prove manuali VoiceOver, NVDA e PAC e le decisioni Ateneo/DPO: Sprint A non viene quindi dichiarato integralmente completato.

## Incrementi realizzati

- C1: migrazione additiva `0004`, storage privato MinIO, upload progressivo e idempotente, proprietà utente/missione, convalida JPEG/PNG/WebP/PDF, limiti dimensione/pagine e originale immutato.
- C2: estrattore modulare locale, testo PDF nativo prima di qualsiasi OCR, proposta separata dai dati confermati, UI documento/campi nello stesso contesto, “Conferma spesa” e “Verifica più tardi”. Le immagini senza OCR configurato restano salvate e revisionabili.
- C3: import CSV/XLSX deterministico, descrizione completa, date separate, deduplicazione, allocazioni 1:N/N:1 e parziali con controllo sia sul movimento sia sulla spesa, export selettivo con disclaimer.
- C4: non realizzato. L'integrazione dei giustificativi nel fascicolo DOCX/PDF resta successiva; il generatore di autorizzazione Sprint A è preservato.

## Evidenze automatiche

- Ruff backend: superato.
- Pytest: include regressione Sprint A e casi Sprint C per duplicati, fallimento estrazione immagini, isolamento oggetti, quota personale, import ripetuto, 52+52 su movimento 104 e blocco sovra-allocazione.
- ESLint e build TypeScript/Vite: superati.
- Playwright/axe: 3 scenari su login/reflow, flusso Sprint A e acquisizione mobile precompilata; i soli controlli automatici non provano conformità WCAG 2.2 AA.
- Docker Compose: PostgreSQL healthy, Alembic `0004 (head)`, 5 missioni preesistenti conservate e 0 documenti reali; put/get MinIO superato con oggetto sintetico poi rimosso.
- `scripts/check_public_repo.py`: verifica assenza di estensioni/dati privati vietati nel repository.

## Limiti e attività residue

- OCR locale per immagini non è incluso nell'ambiente corrente: l'estrazione fallisce in modo controllato e abilita la verifica manuale senza perdere l'originale.
- Nessun adapter OpenAI è attivo. I flag sono entrambi falsi; l'eventuale implementazione richiede decisione e autorizzazione istituzionale prima di dati personali reali.
- Il matching automatico avanzato per merchant/date produce ancora soltanto contratti e allocazioni deterministiche confermate dall'utente; non viene eseguita approvazione automatica.
- Upload riprendibile a chunk, job queue persistente, proposta orari da tratte e metriche aggregate richiedono un incremento successivo.
- Restano necessari test manuali Safari/VoiceOver, NVDA, zoom/reflow su dispositivi reali e threat test dedicati. Nessuna conformità GDPR o WCAG è dichiarata.
- Retention e cancellazione coordinate tra PostgreSQL, MinIO e backup richiedono la policy definitiva dell'Ateneo.
