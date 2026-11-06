# Privacy e sicurezza — Sprint A

Questo documento descrive misure tecniche, non certifica conformità legale.

## Flussi e minimizzazione

Il browser invia credenziali e dati missione all'API; l'API conserva record in PostgreSQL e documenti in storage privato. Nessun analytics, tracing esterno, OCR/AI cloud o email automatica. I log includono solo request-id, esito e route normalizzata: mai corpo, email, token o documenti.

## Matrice accessi

| Risorsa | Richiedente | Protocollo | Missioni | Direttore/segretario |
|---|---|---|---|---|
| propria missione e autorizzazione | CRUD | lettura pertinente | nessuno | nessuno |
| protocollo | inserimento propria | lettura | nessuno | nessuno |
| elenco autorizzazioni pronte | proprie | sola lettura | nessuno | nessuno |

Ogni query applica scope per ruolo e proprietario; l'ID non concede accesso. I download passano dall'API autenticata e non hanno URL pubblici.

## Threat model sintetico

- IDOR: scope object-level e test incrociati.
- Furto sessione/CSRF: cookie HttpOnly, Secure in produzione, SameSite=Strict, token CSRF, scadenza e revoca server-side.
- Brute force: rate limit login, Argon2id, risposta uniforme.
- Injection/XSS: ORM parametrico, validazione Pydantic, CSP restrittiva, escaping React.
- Leak: storage privato, log minimali, scansione cronologia/PII/segreti, credenziali effimere CI.
- Supply chain: lock file, Dependabot, audit dipendenze, permessi workflow read-only.

## Conservazione e diritti

Retention configurabile (`RETENTION_DAYS`, predefinita 365 in demo); job idempotente elimina record scaduti e relativi oggetti e produce solo conteggi. Export e cancellazione sono disponibili all'utente quando legalmente applicabili, con eventuale blocco di conservazione documentato. Backup cifrati e test di ripristino sono responsabilità del deployment.

Implementazione Sprint A: `GET /api/v1/users/me/export`, `DELETE /api/v1/users/me` con frase di conferma, e `python -m app.retention` in dry-run oppure `--execute`. Ogni esecuzione registra cutoff, candidati, eliminati e SHA-256 degli identificativi ordinati. Il reset credenziali è riservato ad `ADMIN`, usa una password temporanea e revoca tutte le sessioni del destinatario. Il rate limit login è persistente nel database, usa una chiave SHA-256 di email normalizzata e indirizzo remoto e non conserva i due valori originali.

## Decisioni obbligatorie prima di dati reali

Titolare e autorizzati, base giuridica (non presunta come consenso), informativa, responsabili art. 28, localizzazione/trasferimenti, retention, DPIA, gestione breach e adeguatezza dei documenti devono essere confermati da Ateneo/DPO/IT.
