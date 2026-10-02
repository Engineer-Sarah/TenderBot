import type { Tender, UploadedFile } from './types';

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

interface ApiDoc {
  id: string;
  name: string;
  chunks: number;
}

export const api = {
  health: () => request<{ status: string }>('/api/health'),

  tenders: (category = 'IT') =>
    request<Tender[]>(`/api/tenders?category=${encodeURIComponent(category)}`),

  analyze: (category = 'IT') =>
    request<Tender[]>('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ category }),
    }),

  documents: async (): Promise<UploadedFile[]> => {
    const docs = await request<ApiDoc[]>('/api/documents');
    const today = new Date().toISOString().slice(0, 10);
    return docs.map((d) => ({
      id: d.id,
      name: d.name,
      size: 0,
      type: d.name.toLowerCase().endsWith('.pdf') ? 'application/pdf' : 'application/octet-stream',
      uploadDate: today,
    }));
  },

  upload: (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    return request<{ filename: string; status: string; error?: string }[]>('/api/documents', {
      method: 'POST',
      body: form,
    });
  },

  deleteDocument: (id: string) =>
    request<{ deleted_chunks: number }>(`/api/documents/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    }),
};
