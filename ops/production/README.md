# Deployment di produzione Uniparthenope

Questa configurazione prepara il servizio ma **non autorizza il go-live né l'uso di dati reali**. L'HTTPS termina sul reverse proxy dell'Ateneo, che inoltra verso l'unica porta pubblicata da `app`. FastAPI serve API e bundle frontend; Compose non contiene Nginx, Traefik, Caddy o certificati.

## Prerequisiti e segreti

- Docker Engine con Compose v2, `curl`, `age`, spazio persistente e destinazione backup off-host approvati dall'ICT.
- Copia non versionata di `.env.production.example` come `.env.production`, mode `0600`.
- Quattro file root-owned esterni al repository, mode `0600`: URL SQLAlchemy completo, password PostgreSQL, access key MinIO e secret key MinIO. La password nell'URL deve coincidere con quella PostgreSQL.
- File di destinatari `age` amministrato separatamente. La chiave privata di decifratura non deve risiedere con i backup.
- Immagine `APP_IMAGE` identificata da tag di release immutabile o digest. Le immagini di base sono versionate; prima del rilascio ICT deve registrare i digest effettivamente risolti.

Non usare `VITE_*` per segreti. Non eseguire `app.seed` e non inserire account demo. Il primo amministratore va creato con una procedura one-shot concordata, auditata e non versionata.

## Procedura

```bash
chmod 600 .env.production /etc/missioni-dist/secrets/*
ops/production/preflight.sh .env.production
ops/production/deploy.sh .env.production
```

`deploy.sh` effettua preflight, backup cifrato, pull, avvio dipendenze, `alembic upgrade head` esplicito, avvio app e smoke test `/ready`. Non è previsto deploy automatico da GitHub.

Per verificare un backup con dati esclusivamente sintetici:

```bash
AGE_IDENTITIES=/percorso/identita-age \
  ops/production/restore-test.sh .env.production backup.tar.age
```

`age` usa la propria configurazione/identità locale per decifrare. Lo script crea un progetto Compose separato, verifica checksum, ripristina DB e oggetti e distrugge i volumi di test. Non indicarlo mai verso una copia reale senza autorizzazione e ambiente controllato.

## Operatività

Volumi PostgreSQL e MinIO sono persistenti; `/tmp` OCR è `tmpfs`. Pianificare `backup.sh` con systemd/cron soltanto dopo aver definito destinazione off-host, retention, monitoraggio dell'exit code, RPO/RTO e custodia chiavi con ICT. Alert minimi: `/ready` indisponibile, backup fallito, disco quasi pieno e crescita 5xx; i messaggi non devono contenere payload o dati personali.

Le risorse CPU/RAM non sono fissate senza conoscere il server. Per il collaudo misurare picco RAM OCR/PDF, spazio DB/object store, concorrenza e latenza, poi concordare limiti e capacità. Consultare `security-checklist.md`, `ict-handoff.md` e `rollback.md`.
