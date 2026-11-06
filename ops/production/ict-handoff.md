# Scheda tecnica per ICT Uniparthenope

## Dati richiesti

- FQDN e DNS: `DA_ASSEGNARE_ICT`.
- Posizione proxy: stesso host o remoto; IP/CIDR proxy autorizzati: `DA_ASSEGNARE_ICT`.
- Upstream applicativo: host Docker `DA_ASSEGNARE_ICT`, TCP `${APP_PORT:-8080}`. Se stesso host, bind `127.0.0.1`; se remoto, interfaccia privata e firewall limitato ai proxy.
- Health liveness: `GET /health`; readiness: `GET /ready`. Nessuna autenticazione, risposta priva di dettagli infrastrutturali.
- Limite upload applicativo predefinito: 15 MB; limite proxy e timeout OCR da concordare dopo misura. Nessun WebSocket richiesto.

## Contratto proxy

Terminare TLS sul proxy istituzionale e inoltrare la stessa origin per UI, `/api`, `/health` e `/ready`. Preservare `Host` e impostare `X-Forwarded-Proto: https`, `X-Forwarded-For` e, se usato, `X-Forwarded-Host`. L'app accetta header forwarded esclusivamente dagli IP/CIDR configurati in `FORWARDED_ALLOW_IPS`; `ALLOWED_HOSTS` deve contenere il FQDN pubblico.

Disabilitare caching pubblico per `/api`, contenuti autenticati e download. L'app aggiunge `Cache-Control: private, no-store` alle API e CSP/`nosniff`/Referrer/Permissions Policy. Concordare HSTS, versione TLS, cipher policy e ulteriori header sul terminatore istituzionale. Non riscrivere HTTPS verso redirect HTTP.

## Rete e responsabilità

Compose non pubblica PostgreSQL né MinIO e non include un reverse proxy. La rete `data` è `internal`; solo `app` partecipa anche alla rete ingress. Vietare accesso diretto alla porta applicativa da reti diverse dal proxy. Confermare OS, Docker, storage, cifratura, registry, aggiornamenti, logging, monitoraggio, backup off-host, chiavi, alert, firewall e finestra di manutenzione.

Prima del go-live ICT deve verificare login/logout, reload sessione, CSRF, upload/OCR/download e `POST /api/v1/missions/{id}/authorization/render` passando dall'HTTPS pubblico, oltre al tentativo di spoofing degli header forwarded da un client non fidato.
