// Tiny REST client. Vite proxies /api → http://localhost:8000.

const json = (r) => {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
  return r.json()
}

export const api = {
  health:  ()              => fetch('/api/health').then(json),
  memory:  ()              => fetch('/api/memory').then(json),
  observe: (force_vlm=false) =>
    fetch('/api/observe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ force_vlm }),
    }).then(json),
  chat:    (prompt, history=[]) =>
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, history }),
    }).then(json),
}
