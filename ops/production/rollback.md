# Rollback operativo

Il rollback applicativo e il restore dei dati sono operazioni distinte. Registrare sempre commit, digest delle immagini, revisione delle migrazioni e backup associato al rilascio.

1. Bloccare nuovi rilasci e valutare se l'applicazione deve essere resa temporaneamente indisponibile tramite il proxy istituzionale.
2. Se lo schema resta compatibile, impostare `APP_IMAGE` al digest della release precedente, eseguire `preflight.sh`, quindi `docker compose ... up -d --no-deps app` e verificare `/ready` e gli smoke test sintetici.
3. Non eseguire automaticamente `alembic downgrade`. Ogni downgrade va revisionato; se è distruttivo, mantenere l'app precedente ferma e procedere solo con un piano dati approvato.
4. Se i dati devono tornare a un punto precedente, conservare prima una copia dello stato corrente e usare un backup verificato. Il restore di produzione richiede change approvato, finestra di fermo e doppio controllo dell'ambiente. `restore-test.sh` è deliberatamente isolato e non ripristina produzione.
5. Dopo il rollback verificare login/logout, CSRF, autorizzazione PDF, upload/OCR/download sintetico, ownership e audit; comunicare l'esito senza dati personali.
