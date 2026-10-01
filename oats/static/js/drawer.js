// The cart drawer (a <dialog>, so focus trapping, Esc and the backdrop are the browser's
// job) plus every [data-cart-lines] summary on the page, including the checkout one.
import { config, money } from "./config.js";
import { lineLabel, lineMeta, lineSwatch, totals, unitCents } from "./cart.js";
import { store } from "./store.js";

const dialog = document.getElementById("cart-drawer");
let lastFocus = null;

export function openDrawer() {
  if (!dialog || dialog.open) return;
  lastFocus = document.activeElement;
  dialog.showModal();
  dialog.querySelector("[data-close-cart]")?.focus();
}

export function closeDrawer() {
  if (dialog?.open) dialog.close();
}

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}

function renderLines(container, lines, editable) {
  container.replaceChildren();
  lines.forEach((l) => {
    const li = el("li", "cart-line");
    const sw = lineSwatch(l);
    const swatch = el("div", "cart-line-sw", sw.text);
    if (sw.flavor) swatch.dataset.flavor = sw.flavor;
    li.append(swatch);

    const body = el("div");
    body.append(el("div", "cart-line-name", lineLabel(l)));
    const meta = lineMeta(l);
    if (meta) body.append(el("div", "cart-line-meta", meta));
    if (editable) {
      const ctl = el("div", "cart-line-ctl");
      const qty = el("div", "qty qty-sm");
      const dec = el("button", "qty-btn", "−");
      dec.type = "button";
      dec.setAttribute("aria-label", "Fewer");
      dec.addEventListener("click", () => store.setQty(l.key, l.qty - 1));
      const n = el("output", "pick-n", String(l.qty));
      n.setAttribute("aria-label", "Quantity");
      const inc = el("button", "qty-btn", "+");
      inc.type = "button";
      inc.setAttribute("aria-label", "More");
      inc.addEventListener("click", () => store.setQty(l.key, l.qty + 1));
      qty.append(dec, n, inc);
      const rm = el("button", "cart-line-rm", "Remove");
      rm.type = "button";
      rm.addEventListener("click", () => store.remove(l.key));
      ctl.append(qty, rm);
      body.append(ctl);
    } else {
      body.append(el("div", "cart-line-meta", `× ${l.qty}`));
    }
    li.append(body);
    li.append(el("div", "cart-line-price", money(unitCents(l.sku, l.subscribe) * l.qty)));
    container.append(li);
  });
}

export function renderCart(lines) {
  const t = totals(lines);
  document.querySelectorAll("[data-cart-lines]").forEach((c) => {
    renderLines(c, lines, c.closest(".drawer") !== null);
  });
  document.querySelectorAll("[data-cart-empty]").forEach((c) => (c.hidden = lines.length > 0));
  document.querySelectorAll("[data-cart-footer]").forEach((c) => (c.hidden = lines.length === 0));
  document.querySelectorAll("[data-cart-subtotal]").forEach((c) => (c.textContent = money(t.subtotal)));
  document.querySelectorAll("[data-cart-shipping]").forEach((c) => (c.textContent = t.shipping ? money(t.shipping, false) : "Free"));
  document.querySelectorAll("[data-cart-total]").forEach((c) => (c.textContent = money(t.total, false)));
  document.querySelectorAll("[data-cart-ship]").forEach((c) => {
    c.textContent = lines.length === 0 ? "" : t.shipping === 0 ? "Free shipping, nice." : `${money(t.toFree, false)} more for free shipping.`;
  });
  const count = store.count();
  document.querySelectorAll("[data-cart-count]").forEach((c) => {
    if (c.textContent !== String(count)) {
      c.textContent = String(count);
      c.classList.remove("bump");
      void c.offsetWidth;
      c.classList.add("bump");
    }
  });
}

export function initDrawer() {
  if (!dialog) return;
  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-open-cart]")) openDrawer();
    if (e.target.closest("[data-close-cart], [data-close-cart-nav]")) closeDrawer();
  });
  // click on the backdrop = outside the panel
  dialog.addEventListener("click", (e) => {
    const r = dialog.getBoundingClientRect();
    const inside = e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom;
    if (!inside) closeDrawer();
  });
  dialog.addEventListener("close", () => lastFocus?.focus?.());
  store.subscribe(renderCart);
}

export { config };
