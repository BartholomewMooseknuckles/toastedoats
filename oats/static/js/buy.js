// The product page purchase block: plan, quantity, add.
import { config, money } from "./config.js";
import { unitCents } from "./cart.js";
import { store } from "./store.js";
import { openDrawer } from "./drawer.js";

export function buy(form) {
  const sku = form.dataset.sku;
  const flavor = form.dataset.flavor;
  const qty = form.querySelector('input[name="qty"]');
  const total = form.querySelector("[data-buy-total]");
  const plan = () => form.querySelector('input[name="plan"]:checked')?.value === "subscribe";
  const render = () => {
    const q = Math.max(1, Math.min(24, Number(qty.value) || 1));
    qty.value = String(q);
    total.textContent = money(unitCents(sku, plan()) * q);
  };
  form.querySelector("[data-qty-inc]").addEventListener("click", () => {
    qty.value = String(Number(qty.value) + 1);
    render();
  });
  form.querySelector("[data-qty-dec]").addEventListener("click", () => {
    qty.value = String(Number(qty.value) - 1);
    render();
  });
  qty.addEventListener("input", render);
  form.querySelectorAll('input[name="plan"]').forEach((r) => r.addEventListener("change", render));
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const line = { sku, flavor, qty: Number(qty.value) || 1 };
    if (plan()) {
      line.subscribe = true;
      line.cadence = config.defaultCadence;
    }
    store.add(line);
    openDrawer();
  });
  render();
}
