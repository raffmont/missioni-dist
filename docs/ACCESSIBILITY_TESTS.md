# Verifica accessibilità Sprint A

## Estensione Sprint C — 6 novembre 2026

La UI di acquisizione usa input file nativo con alternativa alla fotocamera, messaggi `status`/`alert`, campi etichettati, controlli da 44 px, reflow a colonna e anteprima con testo alternativo. La riconciliazione usa select e conferma esplicita. Playwright/axe resta un controllo automatico parziale: Safari mobile/VoiceOver, NVDA e zoom su dispositivo reale sono attività manuali residue e non si dichiara conformità completa.

Target progettuale: WCAG 2.2 AA, considerando EN 301 549 e normativa italiana applicabile. I test automatici non attestano conformità.

## Gate automatici

- ESLint JSX a11y e axe-core/Playwright sui flussi login, elenco, creazione, autorizzazione e protocollo.
- Reflow viewport 320 CSS px, zoom, contrasto e focus controllati nel test E2E.
- PDF: lingua, titolo, metadati e testo estraibile verificati automaticamente.

## Esito Sprint A — 6 novembre 2026

- axe/Playwright: superato su login, reflow 320 px, creazione missione e stato applicativo.
- Selezione mezzi: `fieldset`/`legend`, cinque checkbox native con etichette, target 24x24 CSS px e attivazione da tastiera con Spazio verificata da Playwright.
- Navigazione tastiera e albero accessibilità macOS: landmark, heading, label e skip-link presenti; focus iniziale sullo skip-link verificato.
- PDF sintetico: PDF/UA-1 conforme secondo veraPDF 1.31.212, profilo PDF/UA-1, 106 regole e 1.246 check superati, zero errori. Struttura verificata: lingua `it`, `Document`, `H1`, lista dati e avviso finale in ordine.

## Checklist manuale da registrare a ogni sprint

- [ ] Solo tastiera: ordine logico, skip-link, focus visibile, nessuna trappola.
- [ ] VoiceOver Safari e NVDA Firefox/Chrome: landmark, titoli, label, errori e status annunciati.
- [ ] Zoom 200–400% e reflow 320 px senza perdita di contenuto/funzione.
- [ ] Contrasto e uso non esclusivo del colore.
- [x] PDF controllato con veraPDF e ordine dei tag ispezionato.
- [ ] PAC 2024/Windows e lettura manuale del PDF (PAC non è disponibile su macOS).

## Regressione 0.2.0 — 6 novembre 2026

- 2/2 scenari Playwright/axe superati, incluso il gruppo multiselezione e reflow a 320 CSS px.
- 1/1 scenario Playwright sui container reali superato con tre mezzi selezionati, reload, PDF, DOCX e protocollo.
- Il PDF mantiene tag, lingua e ordine logico; i test documentali verificano l'elenco completo e l'assenza di orari.

NVDA e PAC richiedono una postazione Windows. VoiceOver richiede l'attivazione esplicita dell'impostazione assistiva di macOS e una sessione umana di ascolto. Finché questi tre controlli non sono verbalizzati e registrati da un collaudatore, lo Sprint A resta **non completato**.
