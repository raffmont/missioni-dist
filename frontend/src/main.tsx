import React, { FormEvent, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const TRANSPORT_MODES = [
  'Aereo', 'Treno', 'Auto a noleggio', 'Auto personale', 'Auto dipartimentale',
] as const;

type Mission = {
  id: string; destination: string; purpose: string; status: string;
  transport_modes: string[]; planned_start: string; planned_end: string;
};
type Receipt = { id: string; status: string; filename: string; media_type: string; proposed_fields: Record<string, string>; confidences: Record<string, number> };
type Expense = { id: string; merchant: string; reimbursement_claimed: string; status: string };
type BankTransaction = { id: string; operation_date: string; full_description: string; amount: string; currency: string; selected: boolean };
type MatchSuggestion = { transaction_id: string; expense_id?: string; expense_ids?: string[]; allocated_amount?: string; allocations?: Array<{expense_id: string; amount: string}>; rationale: string; requires_confirmation: boolean };

let csrf = '';
function csrfToken() {
  return csrf || decodeURIComponent(
    document.cookie.split('; ').find(value => value.startsWith('missioni_csrf='))?.split('=')[1] || '',
  );
}

async function api(path: string, init: RequestInit = {}) {
  const token = csrfToken();
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'include', ...init,
    headers: { 'Content-Type': 'application/json', ...(token ? { 'X-CSRF-Token': token } : {}), ...init.headers },
  });
  if (response.headers.get('x-csrf-token')) csrf = response.headers.get('x-csrf-token')!;
  if (!response.ok) {
    const problem = await response.json();
    throw new Error(problem.title || 'Errore');
  }
  return response;
}

function ReceiptPanel({ mission, announce }: { mission: Mission; announce: (message: string) => void }) {
  const [documents, setDocuments] = useState<Receipt[]>([]);
  const [selected, setSelected] = useState<Receipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [pendingIds, setPendingIds] = useState<string[]>([]);
  const [error, setError] = useState('');
  const loadDocuments = () => api(`/missions/${mission.id}/documents`).then(r => r.json()).then(setDocuments);
  useEffect(() => { loadDocuments().catch(() => {}); }, [mission.id]);

  async function upload(event: React.ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files || []); if (!files.length) return;
    setBusy(true); setError('');
    try {
      const uploadedIds: string[] = [];
      for (const file of files) {
        const saved = await api(`/missions/${mission.id}/documents`, { method: 'POST', body: file, headers: { 'Content-Type': file.type, 'X-Filename': file.name } });
        const doc = await saved.json();
        uploadedIds.push(doc.id);
        announce(`${file.name}: originale salvato. Analisi locale in corso.`);
        const extracted = await api(`/documents/${doc.id}/extract`, { method: 'POST' });
        setSelected(await extracted.json());
      }
      setPendingIds(uploadedIds);
      await loadDocuments(); announce('Acquisizione completata. Verifica i dati proposti.');
    } catch (caught) { setError((caught as Error).message); }
    finally { setBusy(false); event.target.value = ''; }
  }

  async function saveExpense(element: HTMLFormElement, verifyNow: boolean) {
    if (!selected) return;
    const form = new FormData(element);
    const value = (name: string) => form.get(name) || null;
    try {
      await api(`/missions/${mission.id}/expenses`, { method: 'POST', body: JSON.stringify({
        document_ids: pendingIds.length ? pendingIds : [selected.id], expense_date: value('expense_date'), merchant: value('merchant'), description: value('description'),
        category: value('category'), document_total: value('document_total'), currency: value('currency'),
        personally_paid: value('personally_paid'), reimbursement_claimed: value('reimbursement_claimed'),
        notes: value('notes'), verify_now: verifyNow,
      }) });
      announce(verifyNow ? 'Spesa verificata e confermata.' : 'Spesa salvata: potrai verificarla più tardi.');
      setSelected(null); setPendingIds([]); await loadDocuments();
    } catch (caught) { setError((caught as Error).message); }
  }

  const proposed = selected?.proposed_fields || {};
  return <details className="receipts"><summary>Giustificativi <span className="counter">{documents.length}</span></summary>
    <div className="upload-zone">
      <label>Aggiungi giustificativi
        <input type="file" accept="image/jpeg,image/png,image/webp,application/pdf" capture="environment" multiple onChange={upload} disabled={busy} />
      </label>
      <p className="help">Scatta una foto oppure scegli PDF/immagini. L’originale viene salvato prima dell’analisi.</p>
      {busy && <p role="status" aria-live="polite">Salvataggio e analisi in corso…</p>}{error && <p role="alert">{error}</p>}
    </div>
    {documents.length > 0 && <ul className="document-list">{documents.map(doc => <li key={doc.id}><button type="button" className="link-button" onClick={() => { setSelected(doc); setPendingIds([doc.id]); }}>{doc.filename}</button> — {doc.status === 'STORED' ? 'Documento salvato' : doc.status === 'PROCESSING' ? 'Riconoscimento in corso' : doc.status === 'EXTRACTED' ? 'Controlla questi dati' : 'Errore di estrazione: da verificare'}</li>)}</ul>}
    {selected && <div className="verification"><div className="preview"><h4>Originale</h4>{selected.media_type.startsWith('image/') ? <img src={`/api/v1/documents/${selected.id}/content`} alt={`Anteprima ${selected.filename}`} /> : <a href={`/api/v1/documents/${selected.id}/content`} target="_blank" rel="noreferrer">Apri PDF originale</a>}</div>
      <form onSubmit={event => { event.preventDefault(); saveExpense(event.currentTarget, true); }}><h4>Verifica dati proposti</h4><p className="help">I campi incerti restano modificabili. Il totale documento non determina automaticamente la quota richiesta.</p>
        <label>Data<input name="expense_date" type="date" defaultValue={proposed.expense_date || ''} required /></label>
        <label>Esercente<input name="merchant" defaultValue={proposed.merchant || ''} required /></label>
        <label>Categoria<input name="category" defaultValue={proposed.category || ''} /></label>
        <label>Descrizione<textarea name="description" defaultValue={proposed.description || ''} /></label>
        <label>Totale documento<input name="document_total" type="number" min="0" step="0.01" inputMode="decimal" defaultValue={proposed.document_total || ''} required /></label>
        <label>Valuta<input name="currency" pattern="[A-Z]{3}" maxLength={3} defaultValue={proposed.currency || 'EUR'} required /></label>
        <label>Pagato personalmente<input name="personally_paid" type="number" min="0" step="0.01" inputMode="decimal" defaultValue={proposed.personally_paid || ''} required /></label>
        <label>Quota richiesta a rimborso<input name="reimbursement_claimed" type="number" min="0" step="0.01" inputMode="decimal" defaultValue={proposed.reimbursement_claimed || ''} required /></label>
        <label>Note<textarea name="notes" /></label><div className="actions"><button type="submit">Conferma spesa</button><button type="button" className="secondary" onClick={event => saveExpense(event.currentTarget.form!, false)}>Verifica più tardi</button></div>
      </form></div>}
  </details>;
}

function BankPanel({ mission, announce }: { mission: Mission; announce: (message: string) => void }) {
  const [transactions, setTransactions] = useState<BankTransaction[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [suggestions, setSuggestions] = useState<MatchSuggestion[]>([]);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [error, setError] = useState('');
  const refresh = async () => {
    const [tx, ex, matches] = await Promise.all([api(`/missions/${mission.id}/bank-transactions`), api(`/missions/${mission.id}/expenses`), api(`/missions/${mission.id}/matching-suggestions`)]);
    setTransactions(await tx.json()); setExpenses(await ex.json()); setSuggestions(await matches.json());
  };
  useEffect(() => { refresh().catch(() => {}); }, [mission.id]);
  async function importFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]; if (!file) return; setError('');
    try {
      const result = await api(`/missions/${mission.id}/bank-imports`, { method: 'POST', body: file, headers: { 'Content-Type': file.type || 'application/octet-stream', 'X-Filename': file.name } });
      const data = await result.json(); announce(data.duplicate ? 'Estratto già importato: nessun duplicato creato.' : 'Movimenti importati. Seleziona e conferma gli abbinamenti.'); await refresh();
    } catch (caught) { setError((caught as Error).message); }
  }
  async function allocate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try {
      await api(`/missions/${mission.id}/allocations`, { method: 'POST', body: JSON.stringify({ transaction_id: form.get('transaction'), expense_id: form.get('expense'), allocated_amount: form.get('amount'), confirm: true }) });
      announce('Abbinamento confermato.'); event.currentTarget.reset(); await refresh();
    } catch (caught) { setError((caught as Error).message); }
  }
  async function acceptSuggestion(suggestion: MatchSuggestion) {
    const allocations = suggestion.allocations || (suggestion.expense_id && suggestion.allocated_amount ? [{ expense_id: suggestion.expense_id, amount: suggestion.allocated_amount }] : []);
    try {
      for (const item of allocations) await api(`/missions/${mission.id}/allocations`, { method: 'POST', body: JSON.stringify({ transaction_id: suggestion.transaction_id, expense_id: item.expense_id, allocated_amount: item.amount, confirm: true }) });
      announce('Abbinamento suggerito confermato esplicitamente.'); await refresh();
    } catch (caught) { setError((caught as Error).message); }
  }
  return <details className="receipts"><summary>Riconciliazione bancaria <span className="counter">{transactions.filter(t => !t.selected).length}</span></summary>
    <label>Importa estratto conto CSV o XLSX<input type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={importFile} /></label>
    <p className="help">Il file resta nel backend locale: nessun estratto conto viene inviato a servizi AI esterni.</p>{error && <p role="alert">{error}</p>}
    {suggestions.filter(item => !dismissed.includes(`${item.transaction_id}:${item.expense_id || item.expense_ids?.join(',')}`)).length > 0 && <section aria-labelledby={`matches-${mission.id}`}><h4 id={`matches-${mission.id}`}>Abbinamenti suggeriti da verificare</h4><ul>{suggestions.filter(item => !dismissed.includes(`${item.transaction_id}:${item.expense_id || item.expense_ids?.join(',')}`)).map(item => { const key = `${item.transaction_id}:${item.expense_id || item.expense_ids?.join(',')}`; return <li key={key}><p>{item.rationale}. Nessuna associazione automatica.</p><div className="actions"><button type="button" onClick={() => acceptSuggestion(item)}>Conferma suggerimento</button><button type="button" className="secondary" onClick={() => setDismissed(current => [...current, key])}>Rifiuta suggerimento</button></div></li>; })}</ul></section>}
    {transactions.length > 0 && <form onSubmit={allocate}><label>Movimento<select name="transaction" required defaultValue=""><option value="" disabled>Seleziona movimento</option>{transactions.map(tx => <option key={tx.id} value={tx.id}>{tx.operation_date} — {tx.amount} {tx.currency} — {tx.full_description}</option>)}</select></label>
      <label>Spesa<select name="expense" required defaultValue=""><option value="" disabled>Seleziona spesa</option>{expenses.map(ex => <option key={ex.id} value={ex.id}>{ex.merchant || 'Spesa'} — {ex.reimbursement_claimed || 'quota da verificare'} EUR</option>)}</select></label>
      <label>Importo allocato<input name="amount" type="number" min="0.01" step="0.01" inputMode="decimal" required /></label><button>Conferma abbinamento</button></form>}
  </details>;
}

function App() {
  const [user, setUser] = useState(false);
  const [items, setItems] = useState<Mission[]>([]);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const load = () => api('/missions').then(response => response.json()).then(setItems);

  useEffect(() => { api('/auth/me').then(() => { setUser(true); load(); }).catch(() => {}); }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    try {
      await api('/auth/login', { method: 'POST', body: JSON.stringify({ email: form.get('email'), password: form.get('password') }) });
      setUser(true); setNotice('Accesso effettuato'); await load();
    } catch (caught) { setError((caught as Error).message); }
  }

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError('');
    const element = event.currentTarget;
    const form = new FormData(element);
    const payload = {
      destination: form.get('destination'), country: 'Italia', purpose: form.get('purpose'),
      transport_modes: form.getAll('transport_modes'), fund_code: form.get('fund'), cup: null,
      fund_manager: form.get('manager'),
      // Date strings are sent verbatim. No Date object or timezone conversion is involved.
      planned_start: form.get('start'), planned_end: form.get('end'),
    };
    try {
      await api('/missions', { method: 'POST', body: JSON.stringify(payload) });
      element.reset(); setNotice('Bozza salvata'); await load();
    } catch (caught) { setError((caught as Error).message); }
  }

  async function render(mission: Mission, format: 'pdf' | 'docx') {
    const response = await api(`/missions/${mission.id}/authorization/render?format=${format}`, { method: 'POST' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(await response.blob()); anchor.download = `autorizzazione.${format}`; anchor.click();
    setNotice(`Autorizzazione ${format.toUpperCase()} generata; non risulta inviata né protocollata`); await load();
  }

  async function protocol(event: FormEvent<HTMLFormElement>, mission: Mission) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    try {
      await api(`/missions/${mission.id}/protocol`, { method: 'PUT', body: JSON.stringify({ protocol_number: form.get('number'), protocol_date: form.get('date') }) });
      setNotice('Protocollo registrato manualmente; non è una verifica ufficiale'); await load();
    } catch (caught) { setError((caught as Error).message); }
  }

  if (!user) return <>
    <a className="skip" href="#main">Vai al contenuto</a><header><h1>Missioni DIST</h1></header>
    <main id="main"><h2>Accesso</h2><p>Ambiente dimostrativo con soli dati sintetici.</p>
      {error && <p role="alert">{error}</p>}
      <form onSubmit={login}><label>Email<input name="email" type="email" autoComplete="username" required defaultValue="richiedente@example.org" /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label><button>Accedi</button></form>
    </main>
  </>;

  return <>
    <a className="skip" href="#main">Vai al contenuto</a>
    <header><h1>Missioni DIST</h1><nav aria-label="Navigazione principale"><a href="#missioni">Le mie missioni</a><a href="#nuova">Nuova missione</a></nav></header>
    <main id="main"><p className="notice" role="status" aria-live="polite">{notice}</p>{error && <p role="alert">{error}</p>}
      <section id="nuova"><h2>Nuova missione</h2><form onSubmit={create}>
        <label>Destinazione<input name="destination" required /></label>
        <label>Motivazione<textarea name="purpose" required minLength={5} /></label>
        <fieldset className="transport-options"><legend>Mezzi di trasporto</legend><p id="transport-help">Seleziona uno o più mezzi.</p>
          {TRANSPORT_MODES.map(mode => <label key={mode}><input type="checkbox" name="transport_modes" value={mode} aria-describedby="transport-help" /><span>{mode}</span></label>)}
        </fieldset>
        <label>Codice fondo<input name="fund" required /></label>
        <label>Responsabile del fondo<input name="manager" required /></label>
        <label>Data prevista di inizio<input name="start" type="date" required /></label>
        <label>Data prevista di fine<input name="end" type="date" required /></label>
        <button>Salva bozza</button>
      </form></section>
      <section id="missioni"><h2>Le mie missioni</h2>{items.length === 0 ? <p>Nessuna missione presente.</p> : <ul className="cards">
        {items.map(mission => <li key={mission.id}><article><h3>{mission.destination}</h3><p>{mission.purpose}</p>
          <p><strong>Periodo:</strong> {mission.planned_start} – {mission.planned_end}</p>
          <p><strong>Mezzi:</strong> {mission.transport_modes.join(', ')}</p><p><strong>Stato:</strong> {mission.status}</p>
          <div className="actions"><button onClick={() => render(mission, 'pdf')}>Scarica PDF</button><button onClick={() => render(mission, 'docx')}>Scarica DOCX</button></div>
          <ReceiptPanel mission={mission} announce={setNotice} />
          <BankPanel mission={mission} announce={setNotice} />
          {mission.status !== 'DRAFT' && mission.status !== 'AUTHORIZED' && <form onSubmit={event => protocol(event, mission)}><fieldset><legend>Registra protocollo ricevuto</legend><label>Numero<input name="number" required /></label><label>Data<input name="date" type="date" required /></label><button>Registra protocollo</button></fieldset></form>}
        </article></li>)}
      </ul>}</section>
    </main><footer><p>Prototipo: nessun invio automatico e nessun dato reale.</p></footer>
  </>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
