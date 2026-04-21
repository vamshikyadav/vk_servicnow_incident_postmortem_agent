/**
 * RCA Agent API client.
 * VITE_API_URL is set at build time for Cloud Run/GKE.
 * During local dev, Vite proxies /api → localhost:8080.
 */
const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1/rca`
  : '/api/v1/rca';

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Run all four pipeline stages in one call */
export const runFullRCA     = (req) => post('', req);

/** Run individual stages (useful for partial re-runs) */
export const runExtraction  = (req) => post('/extract', req);
export const runTimeline    = (req) => post('/timeline', req);
export const runQuality     = (req) => post('/quality', req);
export const runConfluence  = (req) => post('/confluence', req);

export const healthCheck = () =>
  fetch(`${import.meta.env.VITE_API_URL || ''}/health`).then(r => r.json());
