import type { Tender, EligibilityStatus } from './types';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? '/api';

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(',')[1] ?? '');
    r.onerror = () => reject(new Error(`Could not read ${file.name}`));
    r.readAsDataURL(file);
  });
}

const status = (n: number): EligibilityStatus => (n >= 75 ? 'eligible' : n >= 40 ? 'partial' : 'not-eligible');

interface Result {
  id: string;
  matchPercentage: number;
  summary: string;
  met: string[];
  gaps: string[];
}

/** Sends the uploaded company PDFs + the tenders on screen to /api/cloud-analyze and merges the scores back. */
export async function analyzeInCloud(tenders: Tender[], files: File[]): Promise<Tender[]> {
  const pdfs = files.filter((f) => f.name.toLowerCase().endsWith('.pdf')).slice(0, 5);
  if (pdfs.length === 0) throw new Error('Pehle "My Company" tab mein apni PDF upload karein, phir analysis chalayein.');
  if (pdfs.reduce((s, f) => s + f.size, 0) > 3_000_000) {
    throw new Error('PDFs bohat bari hain (total 3 MB se kam rakhein).');
  }
  if (tenders.length === 0) throw new Error('Koi tender maujood nahi.');

  const payload = {
    files: await Promise.all(
      pdfs.map(async (f) => ({ name: f.name, mimeType: 'application/pdf', data: await toBase64(f) })),
    ),
    tenders: tenders.map((t) => ({
      id: t.id,
      title: t.title,
      organization: t.organization,
      description: t.description,
      budget: t.budgetLabel,
      deadline: t.deadline,
      requirements: t.requirements.map((r) => r.label),
    })),
  };

  const res = await fetch(`${BASE}/cloud-analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || body.error || `Analysis failed (${res.status})`);

  const byId = new Map<string, Result>((body.results as Result[]).map((r) => [String(r.id), r]));
  return tenders.map((t) => {
    const r = byId.get(t.id);
    if (!r) return t;
    const score = Math.max(0, Math.min(100, Math.round(Number(r.matchPercentage) || 0)));
    return {
      ...t,
      matchPercentage: score,
      eligibilityStatus: status(score),
      aiSummary: r.summary || t.aiSummary,
      requirements: [
        ...(r.met ?? []).map((l, i) => ({ id: `m${i}`, label: l, matched: true, category: 'Met' })),
        ...(r.gaps ?? []).map((l, i) => ({ id: `g${i}`, label: l, matched: false, category: 'Gap' })),
      ],
    };
  });
}
