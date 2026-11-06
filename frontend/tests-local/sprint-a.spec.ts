import { expect, test } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('Sprint A reale: login, persistenza, documenti e protocollo', async ({ page }) => {
  const marker = `Collaudo sintetico ${Date.now()}`;
  await page.goto('/');
  await page.getByLabel('Email').fill('richiedente@example.org');
  await page.getByLabel('Password').fill('Demo-Richiedente-2026!');
  await page.getByRole('button', { name: 'Accedi' }).click();
  await expect(page.getByRole('heading', { name: 'Nuova missione' })).toBeVisible();
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()).violations).toEqual([]);

  await page.getByLabel('Destinazione').fill(marker);
  await page.getByLabel('Motivazione').fill('Evento di collaudo con soli dati sintetici');
  await page.getByRole('checkbox', { name: 'Aereo' }).check();
  await page.getByRole('checkbox', { name: 'Treno' }).check();
  await page.getByRole('checkbox', { name: 'Auto personale' }).check();
  await page.getByLabel('Codice fondo').fill('FONDO-COLLAUDO');
  await page.getByLabel('Responsabile del fondo').fill('Responsabile Sintetico');
  await page.getByLabel('Data prevista di inizio').fill('2027-03-10');
  await page.getByLabel('Data prevista di fine').fill('2027-03-12');
  await page.getByRole('button', { name: 'Salva bozza' }).click();
  await expect(page.getByRole('heading', { name: marker })).toBeVisible();

  await page.reload();
  await expect(page.getByRole('heading', { name: marker })).toBeVisible();
  const card = page.getByRole('article').filter({ hasText: marker });
  await expect(card).toContainText('Aereo, Treno, Auto personale');
  await expect(card).toContainText('2027-03-10 – 2027-03-12');
  const pdf = page.waitForEvent('download');
  await card.getByRole('button', { name: 'Scarica PDF' }).click();
  expect((await pdf).suggestedFilename()).toMatch(/autorizzazione.*\.pdf$/);
  await expect(card).toContainText('AUTHORIZATION_READY');
  const docx = page.waitForEvent('download');
  await card.getByRole('button', { name: 'Scarica DOCX' }).click();
  expect((await docx).suggestedFilename()).toMatch(/autorizzazione.*\.docx$/);

  await card.getByLabel('Numero').fill(`PROT-SYN-${Date.now()}`);
  await card.getByLabel('Data').fill('2027-03-01');
  await card.getByRole('button', { name: 'Registra protocollo' }).click();
  await expect(card).toContainText('AUTHORIZED');
  expect((await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag22aa']).analyze()).violations).toEqual([]);
});
