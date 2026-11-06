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
          {mission.status !== 'DRAFT' && mission.status !== 'AUTHORIZED' && <form onSubmit={event => protocol(event, mission)}><fieldset><legend>Registra protocollo ricevuto</legend><label>Numero<input name="number" required /></label><label>Data<input name="date" type="date" required /></label><button>Registra protocollo</button></fieldset></form>}
        </article></li>)}
      </ul>}</section>
    </main><footer><p>Prototipo: nessun invio automatico e nessun dato reale.</p></footer>
  </>;
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><App /></React.StrictMode>);
