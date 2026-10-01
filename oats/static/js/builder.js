// Build-a-box: pick a size, fill it with flavors, add the whole thing as one line.
import { config, money } from "./config.js";
import { unitCents } from "./cart.js";
import { store } from "./store.js";
import { openDrawer } from "./drawer.js";

export function builder(el) {
  const sizes = el.querySelectorAll('input[name="size"]');
  const picks = el.querySelectorAll(".pick");
  const count = el.querySelector("[data-count]");
  const unitsLabel = el.querySelector("[data-units-label]");
  const progress = el.querySelector("[data-progress]");
  const fill = el.querySelector("[data-progress-fill]");
  const summary = el.querySelector("[data-summary]");
  const total = el.querySelector("[data-total]");
  const addBtn = el.querySelector("[data-builder-add]");
  const sub = el.querySelector("[data-builder-sub]");
  const cadence = el.querySelector("[data-builder-cadence]");
  const cadenceLabel = el.querySelector("[data-cadence-label]");
  const state = Object.fromEntries([...picks].map((p) => [p.dataset.slug, 0]));

  const sku = () => [...sizes].find((s) => s.checked)?.value;
  const units = () => Number([...sizes].find((s) => s.checked)?.dataset.units || 0);
  const picked = () => Object.values(state).reduce((a, b) => a + b, 0);

  // ?size=28 from the shop cards
  const want = new URLSearchParams(location.search).get("size");
  if (want) sizes.forEach((s) => (s.checked = s.dataset.units === want));

  function render() {
    const u = units();
    const n = picked();
    count.textContent = String(n);
    unitsLabel.textContent = String(u);
    progress.setAttribute("aria-valuemax", String(u));
    progress.setAttribute("aria-valuenow", String(n));
    progress.classList.toggle("is-full", n === u);
    fill.style.width = Math.min(100, (n / u) * 100) + "%";
    summary.replaceChildren();
    Object.entries(state)
      .filter(([, v]) => v > 0)
      .forEach(([slug, v]) => {
        const li = document.createElement("li");
        const name = document.createElement("span");
        name.textContent = config.flavors.find((f) => f.slug === slug)?.name || slug;
        const num = document.createElement("strong");
        num.textContent = "× " + v;
        li.append(name, num);
        summary.append(li);
      });
    picks.forEach((p) => {
      p.querySelector("[data-pick-n]").textContent = String(state[p.dataset.slug]);
      p.classList.toggle("is-max", n >= u);
    });
    const isSub = sub.checked;
    el.querySelectorAll("[data-size-price-once], [data-size-per-once]").forEach((x) => (x.hidden = isSub));
    el.querySelectorAll("[data-size-price-sub], [data-size-per-sub]").forEach((x) => (x.hidden = !isSub));
    cadence.hidden = !isSub;
    cadenceLabel.textContent = (config.cadences.find((c) => c.id === cadence.value)?.label || "").replace(/^Every /, "");
    total.textContent = money(unitCents(sku(), isSub));
    const full = n === u;
    addBtn.disabled = !full;
    addBtn.textContent = full ? "Add this box" : n === 0 ? "Fill the box first" : `${u - n} more to go`;
  }

  picks.forEach((p) => {
    const slug = p.dataset.slug;
    p.querySelector("[data-pick-inc]").addEventListener("click", () => {
      if (picked() < units()) state[slug] += 1;
      render();
    });
    p.querySelector("[data-pick-dec]").addEventListener("click", () => {
      if (state[slug] > 0) state[slug] -= 1;
      render();
    });
  });
  sizes.forEach((s) =>
    s.addEventListener("change", () => {
      // shrinking the box: trim picks from the end
      while (picked() > units()) {
        const last = Object.keys(state).reverse().find((k) => state[k] > 0);
        state[last] -= 1;
      }
      render();
    })
  );
  sub.addEventListener("change", render);
  cadence.addEventListener("change", render);
  el.querySelector("[data-builder-fill]")?.addEventListener("click", () => {
    const slugs = Object.keys(state);
    Object.keys(state).forEach((k) => (state[k] = 0));
    for (let i = 0; i < units(); i++) state[slugs[i % slugs.length]] += 1;
    render();
  });
  addBtn.addEventListener("click", () => {
    if (picked() !== units()) return;
    const line = { sku: sku(), qty: 1, picks: Object.fromEntries(Object.entries(state).filter(([, v]) => v > 0)) };
    if (sub.checked) {
      line.subscribe = true;
      line.cadence = cadence.value;
    }
    store.add(line);
    openDrawer();
  });
  render();
}
