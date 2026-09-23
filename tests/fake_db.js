// Fake `db` capability shared by the Node tests and the local harness.
// It mimics the real one where it matters: snapshots are deep-frozen, set() echoes a snapshot to
// listeners, and a missing document reads as exists:false. Writes are recorded in window.__writes.
// Seed the store by defining window.__seed before this script runs; the default seeds one check.
(function () {
  window.__writes = [];
  window.__errors = [];
  window.addEventListener("error", (e) => window.__errors.push(String(e.message)));
  const store = window.__seed
    ? JSON.parse(JSON.stringify(window.__seed))
    : { "progress/c1-blu": { done: { 17: true }, updatedAt: "seed" } };
  const listeners = {};
  const deepFreeze = (o) => { Object.values(o).forEach((v) => { if (v && typeof v === "object") deepFreeze(v); }); return Object.freeze(o); };
  const snap = (path) => {
    const d = store[path];
    return { id: path.split("/").pop(), exists: !!d, data: () => (d ? deepFreeze(JSON.parse(JSON.stringify(d))) : undefined), metadata: { fromCache: false, hasPendingWrites: false } };
  };
  const doc = (path) => ({
    id: path.split("/").pop(),
    path,
    get: async () => snap(path),
    set: async (data) => {
      window.__writes.push({ path, data: JSON.parse(JSON.stringify(data)) });
      store[path] = JSON.parse(JSON.stringify(data));
      (listeners[path] || []).forEach((fn) => fn(snap(path)));
    },
    update: async (data) => { store[path] = Object.assign(store[path] || {}, data); },
    delete: async () => { delete store[path]; },
    onSnapshot: (next) => { (listeners[path] = listeners[path] || []).push(next); setTimeout(() => next(snap(path)), 30); return () => {}; },
    collection: () => { throw new Error("n/a"); },
  });
  window.__db = { doc, collection: () => { throw new Error("n/a"); } };
  window.claude = { use: async (name) => (name === "db" ? window.__db : null) };
})();
