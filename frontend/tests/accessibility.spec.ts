import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
const tags = ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'];
test('login WCAG AA e reflow 320px', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 }); await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Accesso' })).toBeVisible();
  expect((await new AxeBuilder({ page }).withTags(tags).analyze()).violations).toEqual([]);
  await page.keyboard.press('Tab'); await expect(page.locator('.skip')).toBeFocused();
});
test('flusso principale WCAG AA', async ({ page }) => {
  let missions: Array<Record<string, string>> = [];
  await page.route('**/api/v1/**', async (route) => {
    const url = route.request().url(), method = route.request().method();
    if (url.endsWith('/auth/me')) return route.fulfill({ status: 401, json: { title: 'Sessione richiesta' } });
    if (url.endsWith('/auth/login')) return route.fulfill({ status: 200, headers: { 'x-csrf-token': 'synthetic' }, json: { id: 'u1', email: 'richiedente@example.org', name: 'Ada Esempio', role: 'REQUESTER' } });
    if (url.endsWith('/missions') && method === 'GET') return route.fulfill({ json: missions });
    if (url.endsWith('/missions') && method === 'POST') { missions = [{ id: 'm1', destination: 'Città Esempio', purpose: 'Convegno sintetico', status: 'DRAFT', transport_modes: ['Aereo', 'Treno'], planned_start: '2027-02-10', planned_end: '2027-02-12' }]; return route.fulfill({ status: 201, json: missions[0] }); }
    if (url.includes('/authorization/render')) { missions[0].status = 'AUTHORIZATION_READY'; return route.fulfill({ body: 'synthetic', contentType: 'application/pdf' }); }
    if (url.endsWith('/protocol')) { missions[0].status = 'AUTHORIZED'; return route.fulfill({ json: missions[0] }); }
    return route.fulfill({ status: 404, json: { title: 'Non trovato' } });
  });
  await page.goto('/'); await page.getByLabel('Password').fill('Demo-Richiedente-2026!');
  await page.getByRole('button', { name: 'Accedi' }).click();
  expect((await new AxeBuilder({ page }).withTags(tags).analyze()).violations).toEqual([]);
  await page.getByLabel('Destinazione').fill('Città Esempio');
  await page.getByLabel('Motivazione').fill('Convegno sintetico');
  const transports = page.getByRole('group', { name: 'Mezzi di trasporto' });
  await expect(transports).toBeVisible();
  const airplane = page.getByRole('checkbox', { name: 'Aereo' });
  await airplane.focus(); await page.keyboard.press('Space'); await expect(airplane).toBeChecked();
  await page.getByRole('checkbox', { name: 'Treno' }).check();
  await page.getByLabel('Codice fondo').fill('FONDO-DEMO');
  await page.getByLabel('Responsabile del fondo').fill('Responsabile Esempio');
  await page.getByLabel('Data prevista di inizio').fill('2027-02-10');
  await page.getByLabel('Data prevista di fine').fill('2027-02-12');
  await page.getByRole('button', { name: 'Salva bozza' }).click();
  await expect(page.getByRole('heading', { name: 'Città Esempio' })).toBeVisible();
  await expect(page.getByText('Aereo, Treno')).toBeVisible();
  expect((await new AxeBuilder({ page }).withTags(tags).analyze()).violations).toEqual([]);
});

test('acquisizione mobile precompilata WCAG AA', async ({ page }) => {
  const mission = { id: 'm-c', destination: 'Città Sintetica', purpose: 'Collaudo acquisizione', status: 'DRAFT', transport_modes: ['Treno'], planned_start: '2027-02-10', planned_end: '2027-02-12' };
  let documents: Array<Record<string, unknown>> = [];
  await page.route('**/api/v1/**', async route => {
    const url = route.request().url(), method = route.request().method();
    if (url.endsWith('/auth/me')) return route.fulfill({ status: 401, json: { title: 'Sessione richiesta' } });
    if (url.endsWith('/auth/login')) return route.fulfill({ status: 200, headers: { 'x-csrf-token': 'synthetic' }, json: { id: 'u1', role: 'REQUESTER' } });
    if (url.endsWith('/missions') && method === 'GET') return route.fulfill({ json: [mission] });
    if (url.endsWith('/documents') && method === 'GET') return route.fulfill({ json: documents });
    if (url.endsWith('/documents') && method === 'POST') { documents = [{ id: 'd1', filename: 'ricevuta-sintetica.png', media_type: 'image/png', status: 'STORED', proposed_fields: {}, confidences: {} }]; return route.fulfill({ status: 201, json: documents[0] }); }
    if (url.endsWith('/documents/d1/extract')) { documents[0] = { ...documents[0], status: 'EXTRACTED', proposed_fields: { expense_date: '2027-02-10', merchant: 'FORNITORE SINTETICO', document_total: '100.00', currency: 'EUR' } }; return route.fulfill({ json: documents[0] }); }
    if (url.endsWith('/expenses') && method === 'GET') return route.fulfill({ json: [] });
    if (url.endsWith('/bank-transactions')) return route.fulfill({ json: [] });
    if (url.endsWith('/expenses') && method === 'POST') return route.fulfill({ status: 201, json: { id: 'e1', status: 'VERIFIED' } });
    return route.fulfill({ status: 404, json: { title: 'Non trovato' } });
  });
  await page.setViewportSize({ width: 320, height: 700 }); await page.goto('/');
  await page.getByLabel('Password').fill('Demo-Richiedente-2026!'); await page.getByRole('button', { name: 'Accedi' }).click();
  const card = page.getByRole('article'); await card.locator('summary').filter({ hasText: 'Giustificativi' }).click();
  await card.getByLabel('Aggiungi giustificativi').setInputFiles({ name: 'ricevuta-sintetica.png', mimeType: 'image/png', buffer: Buffer.from('synthetic') });
  await expect(card.getByLabel('Totale documento')).toHaveValue('100.00');
  await card.getByLabel('Pagato personalmente').fill('40'); await card.getByLabel('Quota richiesta a rimborso').fill('40');
  expect((await new AxeBuilder({ page }).withTags(tags).analyze()).violations).toEqual([]);
  await card.getByRole('button', { name: 'Conferma spesa' }).click(); await expect(page.getByRole('status')).toContainText('Spesa verificata');
});
