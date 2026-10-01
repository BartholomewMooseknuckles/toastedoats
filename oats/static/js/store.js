// Cart state. Lives in localStorage so a box survives a reload; falls back to memory when
// storage throws (Safari private mode) so the site never breaks over a cart.
const KEY = "oats.cart.v1";
const MAX_LINES = 20;
const MAX_QTY = 24;

let lines = load();
const listeners = new Set();

function load() {
  try {
    const raw = localStorage.getItem(KEY);
    const data = raw ? JSON.parse(raw) : null;
    return Array.isArray(data?.lines) ? data.lines.filter(valid) : [];
  } catch {
    return [];
  }
}

function save() {
  try {
    localStorage.setItem(KEY, JSON.stringify({ lines, updated: Date.now() }));
  } catch {
    /* memory only - fine */
  }
}

function valid(l) {
  return l && typeof l.sku === "string" && Number.isInteger(l.qty) && l.qty > 0;
}

// Two lines are the same line when everything but the quantity matches.
export function keyOf(l) {
  const picks = l.picks ? Object.keys(l.picks).sort().map((k) => k + ":" + l.picks[k]).join(",") : "";
  return [l.sku, l.flavor || "", picks, l.subscribe ? "sub:" + (l.cadence || "") : "once"].join("|");
}

function emit() {
  save();
  listeners.forEach((fn) => fn(lines));
  document.dispatchEvent(new CustomEvent("cart:change", { detail: { lines } }));
}

export const store = {
  get lines() {
    return lines;
  },
  count() {
    return lines.reduce((n, l) => n + l.qty, 0);
  },
  subscribe(fn) {
    listeners.add(fn);
    fn(lines);
    return () => listeners.delete(fn);
  },
  add(line) {
    const l = { ...line, qty: Math.max(1, Math.min(MAX_QTY, line.qty || 1)), subscribe: !!line.subscribe };
    l.key = keyOf(l);
    const existing = lines.find((x) => x.key === l.key);
    if (existing) existing.qty = Math.min(MAX_QTY, existing.qty + l.qty);
    else if (lines.length < MAX_LINES) lines.push(l);
    emit();
    return l.key;
  },
  setQty(key, qty) {
    const l = lines.find((x) => x.key === key);
    if (!l) return;
    if (qty <= 0) lines = lines.filter((x) => x.key !== key);
    else l.qty = Math.min(MAX_QTY, qty);
    emit();
  },
  remove(key) {
    lines = lines.filter((x) => x.key !== key);
    emit();
  },
  setSubscribeAll(on, cadence) {
    lines.forEach((l) => {
      l.subscribe = on;
      l.cadence = on ? cadence : undefined;
      l.key = keyOf(l);
    });
    // merge any lines that collapsed into each other
    const merged = [];
    lines.forEach((l) => {
      const m = merged.find((x) => x.key === l.key);
      if (m) m.qty = Math.min(MAX_QTY, m.qty + l.qty);
      else merged.push(l);
    });
    lines = merged;
    emit();
  },
  clear() {
    lines = [];
    emit();
  },
};

// Another tab changed the cart: pick it up.
window.addEventListener("storage", (e) => {
  if (e.key === KEY) {
    lines = load();
    listeners.forEach((fn) => fn(lines));
    document.dispatchEvent(new CustomEvent("cart:change", { detail: { lines } }));
  }
});
