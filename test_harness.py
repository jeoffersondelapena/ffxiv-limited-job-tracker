"""Writes tracker.test.html: the built page with a fake `db` capability that behaves like the real one
(deep-frozen snapshots, set() echoing a snapshot, one seeded check). Open it in a browser and toggle
entries; window.__writes lists the saves and window.__errors any thrown errors."""
FAKE = r'''<script>
window.__writes = []; window.__errors = [];
window.addEventListener('error', e => window.__errors.push(String(e.message)));
window.claude = { use: async (name) => {
  if (name !== 'db') return null;
  const store = { 'progress/c1-blu': { done: { 17: true }, updatedAt: 'seed' } };
  const listeners = {};
  const deepFreeze = o => { Object.values(o).forEach(v => { if (v && typeof v === 'object') deepFreeze(v); }); return Object.freeze(o); };
  const snap = path => { const d = store[path]; return { id: path.split('/').pop(), exists: !!d,
      data: () => d ? deepFreeze(JSON.parse(JSON.stringify(d))) : undefined, metadata: { fromCache: false, hasPendingWrites: false } }; };
  const doc = path => ({ id: path.split('/').pop(), path,
      get: async () => snap(path),
      set: async data => { window.__writes.push({ path, data: JSON.parse(JSON.stringify(data)) }); store[path] = JSON.parse(JSON.stringify(data)); (listeners[path] || []).forEach(fn => fn(snap(path))); },
      update: async data => { store[path] = Object.assign(store[path] || {}, data); },
      delete: async () => { delete store[path]; },
      onSnapshot: (next) => { (listeners[path] = listeners[path] || []).push(next); setTimeout(() => next(snap(path)), 30); return () => {}; },
      collection: () => { throw new Error('n/a'); } });
  window.__db = { doc, collection: () => { throw new Error('n/a'); } }; // exposed so tests can simulate another device
  return window.__db;
} };
</script>
'''
open('tracker.test.html', 'w').write(FAKE + open('tracker.html').read())
print('tracker.test.html written')
