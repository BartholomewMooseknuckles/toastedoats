// Price math and labels, mirroring catalog.py. The server recomputes everything on
// submit; this is only so the drawer shows the right numbers instantly.
import { boxesBySku, config, flavorsBySlug, money } from "./config.js";
import { store } from "./store.js";

export function unitCents(sku, subscribe) {
  const box = boxesBySku[sku];
  if (!box) return 0;
  return subscribe ? Math.round((box.price_cents * (100 - config.subscribePct)) / 100) : box.price_cents;
}

export function lineLabel(l) {
  const box = boxesBySku[l.sku];
  if (!box) return l.sku;
  if (box.type === "single") return `${box.name} · ${flavorsBySlug[l.flavor]?.name || l.flavor}`;
  return box.name;
}

export function lineMeta(l) {
  const box = boxesBySku[l.sku];
  const bits = [];
  if (box?.type === "byo" && l.picks) {
    bits.push(
      Object.entries(l.picks)
        .filter(([, n]) => n > 0)
        .map(([s, n]) => `${n} ${flavorsBySlug[s]?.name || s}`)
        .join(", ")
    );
  } else if (box?.type === "fixed") {
    bits.push("One of each flavor");
  }
  if (l.subscribe) {
    const c = config.cadences.find((x) => x.id === l.cadence);
    bits.push(`Subscribe & save ${config.subscribePct}%` + (c ? ` · ${c.label.toLowerCase()}` : ""));
  }
  return bits.join(" · ");
}

export function lineSwatch(l) {
  const box = boxesBySku[l.sku];
  if (box?.type === "single") return { flavor: l.flavor, text: "7" };
  if (box?.type === "byo") {
    const top = Object.entries(l.picks || {}).sort((a, b) => b[1] - a[1])[0];
    return { flavor: top ? top[0] : "", text: String(box.units) };
  }
  return { flavor: "", text: String(box?.units || "") };
}

export function totals(lines) {
  const subtotal = lines.reduce((s, l) => s + unitCents(l.sku, l.subscribe) * l.qty, 0);
  const shipping = subtotal === 0 || subtotal >= config.freeShipCents ? 0 : config.flatShipCents;
  return { subtotal, shipping, total: subtotal + shipping, toFree: Math.max(0, config.freeShipCents - subtotal) };
}

// Wire every [data-add] button on the page. The JSON in the attribute is the line to add;
// [data-add-sub] buttons also honour the shop section's subscribe switch.
export function initAddButtons(openDrawer) {
  document.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-add]");
    if (!btn) return;
    let line;
    try {
      line = JSON.parse(btn.dataset.add);
    } catch {
      return;
    }
    if (btn.hasAttribute("data-add-sub")) {
      const sw = document.querySelector("[data-sub-switch]");
      if (sw && sw.getAttribute("aria-checked") === "true") {
        line.subscribe = true;
        line.cadence = config.defaultCadence;
      }
    }
    store.add(line);
    btn.classList.add("is-added");
    setTimeout(() => btn.classList.remove("is-added"), 800);
    openDrawer();
  });
}

export { money };
