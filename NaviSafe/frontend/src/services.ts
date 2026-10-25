export const API = import.meta.env.VITE_API_URL || '/api';
import { supabase } from './supabase';
export function readLocal<T>(key: string, fallback: T): T {
  try { return JSON.parse(localStorage.getItem(key) || 'null') ?? fallback; } catch { return fallback; }
}
export function writeLocal(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new Event('safepath-data'));
}
export function clientId() {
  let id = localStorage.getItem('safepath-device');
  if (!id) { id = crypto.randomUUID(); localStorage.setItem('safepath-device', id); }
  return id;
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const session = supabase ? (await supabase.auth.getSession()).data.session : null;
  const response = await fetch(API + path, { ...init, signal: init.signal || AbortSignal.timeout(15000),
    headers: { 'X-Client-ID': clientId(), ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}), ...init.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status}).`) as Error & { status: number };
    error.status = response.status; throw error;
  }
  return response.json();
}
export type Contact = { id: string; name: string; phone: string };
export type CommunityReport = { id: string; street: string; category: string; description: string; status: string; observed_at: string; submitted_at: string; expires_at: string; version: number };
export type Draft = {
  id: string; state: 'draft' | 'queued' | 'failed' | 'conflict' | 'synced';
  fields: Record<string, string>; image?: File; error?: string; updated: string; serverId?: string;
};
function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('safepath-private', 1);
    req.onupgradeneeded = () => req.result.createObjectStore('outbox', { keyPath: 'id' });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(new Error('Device storage unavailable. Your report has not been saved.'));
  });
}
export async function drafts(): Promise<Draft[]> {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction('outbox');
    const req = tx.objectStore('outbox').getAll();
    tx.oncomplete = () => { resolve(req.result); db.close(); };
    tx.onerror = () => { reject(tx.error); db.close(); };
  });
}
export async function saveDraft(draft: Draft) {
  const db = await database();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').put(draft);
    tx.oncomplete = () => { db.close(); window.dispatchEvent(new Event('safepath-data')); resolve(); };
    tx.onerror = () => { db.close(); reject(new Error('Storage full or unavailable. Keep this form open.')); };
  });
}
export async function removeDraft(id: string) {
  const db = await database();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction('outbox', 'readwrite');
    tx.objectStore('outbox').delete(id);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}
let syncing = false;
export async function syncDrafts() {
  if (syncing || !navigator.onLine) return;
  syncing = true;
  try {
    for (const draft of await drafts()) {
      if (draft.state !== 'queued') continue;
      const form = new FormData();
      Object.entries(draft.fields).forEach(([k, v]) => form.append(k, v));
      if (draft.image) form.append('file', draft.image);
      try {
        const result = await api<{ report: CommunityReport }>('/report', {
          method: 'POST', body: form, headers: { 'Idempotency-Key': draft.id },
        });
        // Release local image after the server has confirmed durable receipt.
        await saveDraft({ ...draft, image: undefined, state: 'synced', serverId: result.report.id, error: undefined });
      } catch (err) {
        const e = err as Error & { status?: number };
        await saveDraft({ ...draft, state: e.status === 409 ? 'conflict' : e.status && e.status < 500 && e.status !== 429 ? 'failed' : 'queued', error: e.message });
      }
    }
  } finally { syncing = false; }
}
export const statusLabel: Record<string, string> = {
  pending_review: 'Unverified · awaiting review', provisionally_published: 'Unverified · provisional',
  corroborated: 'Corroborated', verified: 'Verified · human reviewed', disputed: 'Disputed',
  rejected: 'Rejected', expired: 'Expired', draft: 'Device draft',
};
export function requestLocation(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error('Location is unavailable. Enter your origin manually.'));
    navigator.geolocation.getCurrentPosition(resolve, () => reject(new Error('Location was denied or unavailable. Enter an origin or select it on the map.')), { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 });
  });
}
