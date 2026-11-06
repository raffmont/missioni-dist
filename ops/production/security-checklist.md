# Checklist sicurezza e privacy

## Gate tecnici

- [ ] `.env.production` e secret file fuori Git, mode 0600, backup esclusi; rotazione provata.
- [ ] `APP_IMAGE` e immagini terze registrate con digest e sottoposte a vulnerability scan.
- [ ] Unica porta `app`; nessuna porta host per DB, MinIO o backend separato.
- [ ] Bind loopback, oppure firewall con allowlist degli IP proxy deliberata dall'ICT.
- [ ] `ALLOWED_HOSTS`, origin HTTPS e `FORWARDED_ALLOW_IPS` specifici; mai `*`.
- [ ] Cookie Secure/HttpOnly/SameSite e CSRF verificati passando dal proxy HTTPS.
- [ ] Bucket privato, console MinIO non esposta, nessun accesso anonimo.
- [ ] Account demo/seed assenti; bootstrap amministratore one-shot e credenziali ruotate.
- [ ] Test RBAC/ownership con due utenti sintetici superati per missioni, ricevute, OCR, movimenti e download.
- [ ] Log e alert non contengono cookie, token, OCR, IBAN, nomi o documenti.
- [ ] Backup cifrato off-host e restore isolato di DB+oggetti verificato.

## Gate istituzionali — DPO/ICT

- [ ] Titolare, autorizzati, base giuridica, informativa, retention e cancellazione approvati.
- [ ] DPIA/valutazione privacy, responsabili, amministratori di sistema e incident response definiti.
- [ ] Cifratura volumi, backup, custodia chiavi, RPO/RTO e audit retention approvati.
- [ ] Antivirus/quarantena upload e trattamento degli originali scansionati deliberati.
- [ ] Test manuali WCAG 2.2 AA e documenti (VoiceOver, NVDA, mobile, PAC/verifica PDF) registrati.

Il completamento tecnico non equivale a conformità GDPR o WCAG né ad autorizzazione al trattamento.
