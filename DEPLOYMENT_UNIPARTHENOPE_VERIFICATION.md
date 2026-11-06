# Verifica Sprint Infrastructure — Uniparthenope

**Data:** 7 novembre 2026
**Ambito:** repository locale `missioni-dist`, dati esclusivamente sintetici
**Esito complessivo:** **PREPARATO, NON AUTORIZZATO AL GO-LIVE**

## Sintesi dell'implementazione

- `compose.production.yml` espone una sola porta del servizio `app`, con bind predefinito `127.0.0.1`; PostgreSQL e MinIO non hanno `ports` e condividono la rete `data` marcata `internal`.
- Nessun secondo reverse proxy: un Dockerfile multi-stage costruisce Vite e copia gli asset nel backend FastAPI, che serve UI e API sulla stessa origin.
- Immagine applicativa non-root, `read_only`, capability rimosse, `no-new-privileges`, `/tmp` OCR su `tmpfs`; niente Docker socket, host networking o container privileged.
- Cookie Secure obbligatorio in produzione, allowlist Host/origin e trust degli header forwarded limitato agli IP/CIDR configurati. API marcate `private, no-store`.
- Segreti montati da file esterni al repository. `.dockerignore`, `.gitignore`, guard repository e secret scan CI evitano l'inclusione accidentale. AI esterna disabilitata e resa incompatibile con `ENVIRONMENT=production`.
- Startup senza Alembic e senza seed automatici. `deploy.sh` esegue preflight, backup, migrazione esplicita, avvio e readiness. Nessuna pipeline effettua deploy automatico.
- Backup logico PostgreSQL e mirror MinIO con checksum, commit e inventario immagini; archivio obbligatoriamente cifrato con `age`. Restore test in un progetto Compose isolato e distrutto a fine prova.
- Runbook, rollback, checklist sicurezza e scheda tecnica ICT presenti in `ops/production/`.

## SUPERATI — controlli realmente eseguiti

| Controllo | Comando/evidenza sanificata | Esito |
|---|---|---|
| Guard repository pubblico | `python3 scripts/check_public_repo.py` | PASS — soli pattern/dati sintetici rilevati |
| Preflight con secret file sintetici mode 0600 | `ops/production/preflight.sh <env-temporaneo>` | PASS — nessun deploy effettuato |
| Rendering e isolamento Compose | `docker compose ... config --format json \| python3 scripts/check_production_compose.py` | PASS — ingresso unico, reti/porte/private plane validi |
| Lint Python | `.venv/bin/ruff check backend scripts` | PASS |
| Frontend lint | `npm run lint` | PASS |
| Frontend production build | `npm run build` | PASS — bundle Vite generato |
| Immagine production multi-stage | `docker build -t missioni-dist:verification -f backend/Dockerfile .` | PASS — digest manifest locale `sha256:eaf3…64238` (non è un digest di release) |
| Esecuzione non-root | `docker run ... id -u` | PASS — UID `1000` |
| Backend regressione sintetica Linux | container effimero, `pytest -q -p no:cacheprovider /tests` | PASS — **22 passed**, incluse CSRF, RBAC/ownership, PDF/DOCX, upload, OCR locale, import e allocazioni |
| Ingresso unico UI/API | container effimero; GET `/` e GET `/health` | PASS |
| Lint patch | `git diff --check` | PASS |

Nota: un primo tentativo pytest diretto su macOS è stato bloccato dall'assenza della libreria nativa WeasyPrint `libgobject-2.0-0`; la suite è stata quindi eseguita nell'immagine Linux di destinazione con le dipendenze previste. Un primo run container ha inoltre evidenziato che lo storage test non-root doveva usare `/tmp`; il fixture è stato corretto e la suite completa è poi passata.

## IMPLEMENTATO MA NON PROVATO END-TO-END IN QUESTO AMBIENTE

| Controllo | Stato | Motivo/passo successivo |
|---|---|---|
| Backup cifrato PostgreSQL + MinIO | BLOCKED — ICT/ambiente | Il comando richiede `age`, chiave destinatario e destinazione off-host approvate; `age` non è installato su questa workstation. Eseguire in collaudo sintetico e monitorare exit code. |
| Restore DB + oggetti e corrispondenza | BLOCKED — ICT/ambiente | Eseguire `restore-test.sh` su backup sintetico; verificare checksum, conteggio righe e oggetti, poi registrare evidenza. Mai usare produzione per il test. |
| Persistenza dopo restart/upgrade | BLOCKED — ICT/collaudo | Richiede volumi e capacità del server di collaudo. Creare dati sintetici, riavviare e aggiornare immagine, verificare DB e oggetti. |
| Migrazione Alembic su PostgreSQL reale | BLOCKED — ICT/collaudo | Le regressioni SQLite passano; eseguire backup sintetico, `alembic upgrade head` e verifica schema/dati in collaudo PostgreSQL. |
| Scan vulnerabilità immagini/dipendenze | BLOCKED — ICT/CI | CI predisposta per build/audit; scegliere scanner e policy Ateneo, risolvere/accettare finding e registrare digest release. |

## BLOCKED — verifiche di competenza ICT

- Assegnare FQDN, DNS, posizione del proxy, IP/CIDR attendibili, upstream e firewall. Se proxy remoto, il bind loopback va sostituito con interfaccia privata e allowlist stretta.
- Verificare dal dominio HTTPS istituzionale login, logout, reload sessione, CSRF, upload, OCR, download e `POST /authorization/render`; controllare cookie `Secure`, assenza mixed content e redirect corretti.
- Tentare spoofing di `X-Forwarded-For`, `X-Forwarded-Proto` e `Host` da un client esterno; solo il proxy configurato deve poter influenzare gli header forwarded.
- Definire TLS/HSTS, CSP definitiva, upload limit, timeout OCR/PDF, logging centralizzato, alert e caching disabilitato per dati autenticati. WebSocket non richiesto.
- Confermare OS, CPU/RAM, storage, cifratura volumi, registry, digest immagini, aggiornamenti, backup off-host, custodia chiavi, retention backup, RPO/RTO e incident response.
- Eseguire prove di firewall: DB 5432, MinIO 9000/console e backend diretto non devono essere raggiungibili dall'esterno; solo l'upstream concordato deve esserlo dal proxy.
- Definire bootstrap amministratore one-shot e verificare che account demo e `python -m app.seed` non siano usati.
- Eseguire test manuali VoiceOver/Safari, NVDA/browser supportato, mobile reale, zoom/reflow e verifica PDF (PAC/verifica equivalente); axe da solo non certifica WCAG 2.2 AA.

## BLOCKED — decisioni DPO/istituzionali

- Titolare, soggetti autorizzati, base giuridica, informativa e processo di esercizio diritti.
- Retention/cancellazione coordinata tra PostgreSQL, MinIO, audit e backup; eventuale DPIA.
- Responsabili del trattamento, amministratori di sistema, audit retention e gestione incidenti/data breach.
- Ammissibilità di originali, OCR e dati bancari; scansione malware/quarantena e criteri per file attivi.
- Cifratura a riposo, localizzazione/custodia chiavi e autorizzazione formale a collaudo e produzione con dati personali.

## Release gate

Il gate resta **CHIUSO**. Per aprirlo devono risultare completati e firmati: collaudo HTTPS istituzionale, firewall/header trust, backup+restore sintetico, persistenza+migrazioni PostgreSQL/MinIO, test accessibilità manuali, vulnerability review, parametri operativi ICT e decisioni privacy/DPO. Solo dopo tali approvazioni può essere pianificato un go-live separato.

## Rollback

Il rollback applicativo usa il digest precedente solo se lo schema è compatibile. Nessun `alembic downgrade` distruttivo è automatico. Il restore dati richiede fermo, backup preventivo dello stato corrente, change approvato e doppio controllo dell'ambiente. La procedura completa è in `ops/production/rollback.md`.

**Dichiarazione finale:** durante questa attività non sono stati usati dati reali, non è stato configurato il reverse proxy dell'Ateneo e non è stato effettuato alcun go-live.
