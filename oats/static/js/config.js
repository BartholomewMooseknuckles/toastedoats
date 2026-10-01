// The server embeds the catalog slice the browser needs on every page: prices, flavors,
// prefix, API base. One source of truth, no extra request, works in the frozen copy too.
const el = document.getElementById("oats-config");
export const config = el ? JSON.parse(el.textContent) : { prefix: "", apiBase: "/api", flavors: [], boxes: [] };
export const flavorsBySlug = Object.fromEntries(config.flavors.map((f) => [f.slug, f]));
export const boxesBySku = Object.fromEntries(config.boxes.map((b) => [b.sku, b]));
export const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

export function money(cents, trim = true) {
  const d = cents / 100;
  if (trim && Number.isInteger(d)) return "$" + d.toLocaleString("en-US");
  return "$" + d.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
