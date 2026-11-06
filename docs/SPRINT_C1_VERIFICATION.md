# Rapporto di implementazione e collaudo Sprint C.1

Data: 6 novembre 2026. Tutti i documenti, utenti e movimenti usati sono sintetici.

## Esito

Il criterio bloccante C.1 è soddisfatto: una fotografia JPEG sintetica di uno scontrino,
inclinata e con luminosità ridotta, viene elaborata dal vero Tesseract installato nel
container backend e genera una proposta con data, esercente, totale, valuta, categoria,
importo pagato e quota richiesta precompilati. Nessuna API esterna è configurata o
invocata. I flag `OPENAI_EXTRACTION_ENABLED` e
`OPENAI_DATA_PROCESSING_AUTHORIZED` restano `false` per default.

## Incrementi verificati

- OCR locale Tesseract 5.5.0, pacchetti lingua `ita` e `eng`, Poppler per PDF scansionati;
  licenze Apache-2.0 (Tesseract) e GPL/LGPL secondo i componenti Poppler distribuiti da
  Debian. L'incremento osservato durante la build è circa 139 MB installati per OCR,
  rendering PDF, font e dipendenze di sistema complessive.
- Priorità al testo nativo dei PDF; OCR solo per immagini e PDF senza testo. Correzione
  EXIF, scala, autocontrasto e lieve contrasto operano esclusivamente su copie in `/tmp`.
- Timeout: 30 s per pagina OCR e 45 s per rendering PDF; massimo upload 15 MB, 30 pagine
  e 40 megapixel. Il container è read-only, usa `tmpfs /tmp` e
  `no-new-privileges`.
- Output OCR grezzo separato dalla proposta strutturata tramite migrazione additiva e
  reversibile `0005`; versione motore, provenienza, box e confidenze osservate sono
  persistiti, ma il testo integrale non viene scritto nei log.
- Parser deterministico: etichette `TOTALE/TOTAL/IMPORTO/AMOUNT/PAGATO/PAID` hanno
  precedenza; subtotale, IVA/tax e resto/change vengono esclusi. Nessuna scelta usa
  semplicemente il numero massimo. Sono classificati ristorazione, ricevuta POS,
  biglietto ferroviario e altro; per treni sono proposti tratta e orari quando leggibili.
- UI mobile documento/campi nello stesso contesto, messaggi italiani, quote precompilate
  solo con totale etichettato univoco, correzione dei singoli campi, conferma immediata o
  verifica differita. Più file caricati insieme vengono collegati a una sola spesa senza
  sommare automaticamente gli importi.
- Matching bancario solo suggerito: importo/valuta, finestra data configurabile (14
  giorni), parole merchant e combinazioni di due spese. È coperto il caso 52+52 EUR su
  un movimento da 104 EUR. L'utente deve confermare; può rifiutare o scegliere
  manualmente. I controlli di sovra-allocazione esistenti restano autoritativi.

## Prove e risultati effettivi

Comandi eseguiti:

```text
docker compose build backend
docker run ... python -m pytest -q tests
.venv/bin/ruff check backend
cd frontend && npm run lint && npm run build
docker compose up --build -d
curl -fsS http://localhost:5173/health
docker compose exec -T backend alembic current
docker compose exec -T backend tesseract --list-langs
docker run ... python /bench/benchmark_ocr.py
```

Risultati:

- backend nel container: **19 passed**, 2 avvisi di deprecazione non bloccanti;
- Ruff: superato; ESLint: superato; TypeScript/Vite: superato;
- Compose: PostgreSQL healthy, MinIO attivo, health `{"status":"ok"}`;
- Alembic: `0005 (head)`; lingue OCR: `eng`, `ita`, `osd`;
- test di isolamento: un secondo utente riceve 404 su originale/proposta altrui;
- upload non immagine/PDF e contenuti corrotti sono rifiutati; il controllo pubblico non
  include documenti reali, segreti o output OCR personali.

Il test Playwright/axe automatico comprende tre scenari per login/reflow 320 px, flusso
Sprint A e acquisizione mobile precompilata. Il primo tentativo di questa sessione non è
partito perché Chromium non era installato nel runner macOS; questa è un'assenza del
browser di test, non un esito WCAG. Le verifiche manuali Safari/VoiceOver, NVDA, zoom su
dispositivi reali e contrasto restano aperte; non viene dichiarata conformità WCAG 2.2 AA.

## Benchmark OCR sintetico

Metodo ripetibile: `backend/tests/benchmark_ocr.py`, 12 fotografie JPEG generate senza
dati personali, angolo da -2° a +2°, luminosità 0,68–1,00 e sfocatura gaussiana 0–0,6.
Il benchmark è stato eseguito nell'immagine backend read-only con Tesseract reale; non usa
mock. Campi misurati: esercente, data, totale e valuta.

| Metrica | Risultato osservato |
|---|---:|
| Correttezza esercente | 12/12 (100%) |
| Correttezza data | 12/12 (100%) |
| Correttezza totale | 12/12 (100%) |
| Correttezza valuta | 12/12 (100%) |
| Correzioni manuali medie sui 4 campi | 0,000/documento |
| Latenza p50 | 245,2 ms |
| Latenza p95 (nearest-rank sul campione) | 263,5 ms |
| Fallimenti | 0/12 (0%) |

Il campione prova il percorso sintetico controllato, non generalizza a ricevute reali,
fotografie molto degradate o layout sconosciuti e non costituisce un target garantito.

## GDPR, sicurezza e attività aperte

Originali e OCR restano nel deployment locale/MinIO privato, senza URL pubblici
persistenti; i controlli proprietario/missione sono lato server. La minimizzazione,
retention/cancellazione coordinata con backup, DPIA, base giuridica e autorizzazione per
eventuali provider futuri richiedono decisioni Ateneo/DPO. Non viene dichiarata conformità
GDPR automatica. La coda è sincrona nel pilota: lo stato `PROCESSING` rende visibile un
job interrotto, ma recupero automatico e worker persistente restano miglioramenti futuri.
Sprint B e fascicolo finale C4 non sono stati implementati.
