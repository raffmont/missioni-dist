# Policy repository pubblico

Ogni commit, branch, tag, issue, log e artifact è pubblico. Sono vietati dati reali, segreti, token, cookie, chiavi, certificati, backup e documenti amministrativi. I riferimenti esterni restano fuori dal workspace Git.

Sono ammessi soltanto fixture sintetiche con domini `example.org`. `.gitignore` è una difesa aggiuntiva: pre-commit e CI eseguono Gitleaks sull'intera cronologia e un controllo PII. Le dipendenze sono controllate automaticamente e `main` richiede review e check verdi.

## Risposta a leak

1. Revoca/rotazione immediata e contenimento.
2. Rimozione da repository, artifact, cache e sistemi collegati.
3. Riscrittura cronologia quando appropriato, sapendo che copie esterne possono persistere.
4. Valutazione dell'incidente, registrazione e notifiche con responsabili/DPO.
5. Correzione dei gate che non hanno intercettato l'evento.
