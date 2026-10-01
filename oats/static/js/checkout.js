// Checkout. In "preorder" mode the cart and the form go to /api/preorder and the customer
// lands on /thanks with a reference. The stripe and shopify adapters are stubs that
// receive the exact same payload, so flipping site.json's checkout.mode is the only change.
import { config } from "./config.js";
import { postJSON } from "./api.js";
import { store } from "./store.js";

const adapters = {
  async preorder(payload) {
    return postJSON("/preorder", payload);
  },
  async stripe() {
    // TODO when Stripe exists: POST payload to /api/checkout/stripe, which creates a
    // Checkout Session from products.json's stripe price ids and returns {url}; then
    // location.assign(url).
    return { ok: false, data: { message: "Card checkout isn't switched on yet. Reserve instead?" } };
  },
  async shopify() {
    // TODO when Shopify exists: build a cart permalink from the variant ids in site.json
    // (https://{domain}/cart/{variant}:{qty},...) and location.assign it.
    return { ok: false, data: { message: "Checkout isn't switched on yet. Reserve instead?" } };
  },
};

export function checkout(el) {
  const form = el.querySelector("#preorder");
  const status = form.querySelector("[data-status]");
  const emailErr = form.querySelector('[data-err-for="email"]');
  const submit = form.querySelector("[data-co-submit]");
  const cadenceWrap = form.querySelector("[data-co-cadence]");
  const planInputs = form.querySelectorAll('input[name="plan"]');

  const isSub = () => form.querySelector('input[name="plan"]:checked')?.value === "subscribe";
  const syncPlan = () => {
    cadenceWrap.hidden = !isSub();
    store.setSubscribeAll(isSub(), form.cadence.value);
  };
  // reflect what the cart already says
  if (store.lines.some((l) => l.subscribe)) {
    planInputs.forEach((p) => (p.checked = p.value === "subscribe"));
    const c = store.lines.find((l) => l.subscribe)?.cadence;
    if (c) form.cadence.value = c;
    cadenceWrap.hidden = false;
  }
  planInputs.forEach((p) => p.addEventListener("change", syncPlan));
  form.cadence.addEventListener("change", syncPlan);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    status.classList.remove("is-err");
    status.textContent = "";
    emailErr.textContent = "";
    const email = form.email.value.trim();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email)) {
      emailErr.textContent = "That email doesn't look right.";
      form.email.focus();
      return;
    }
    if (store.lines.length === 0) {
      status.classList.add("is-err");
      status.textContent = "Your box is empty - add a flavor first.";
      return;
    }
    const payload = {
      email,
      name: form.name.value.trim(),
      zip: form.zip.value.trim(),
      notes: form.notes.value.trim(),
      website: form.website.value,
      cadence: isSub() ? form.cadence.value : null,
      source: "checkout",
      lines: store.lines.map(({ sku, qty, subscribe, cadence, flavor, picks }) => ({ sku, qty, subscribe, cadence, flavor, picks })),
    };
    submit.classList.add("is-busy");
    submit.textContent = "Reserving…";
    try {
      const res = await adapters[config.checkoutMode || "preorder"](payload);
      if (res.ok) {
        store.clear();
        location.assign(`${config.prefix}/thanks?ref=${encodeURIComponent(res.data.ref || "")}`);
        return;
      }
      status.classList.add("is-err");
      status.textContent = res.data?.message || "That didn't go through. Try again?";
    } catch {
      status.classList.add("is-err");
      status.textContent = "No connection. Try again in a moment.";
    }
    submit.classList.remove("is-busy");
    submit.textContent = "Reserve my box";
  });
}

export function thanks(el) {
  const ref = new URLSearchParams(location.search).get("ref");
  const out = el.querySelector("[data-ref]");
  if (ref && out) out.textContent = ref.replace(/[^A-Z0-9-]/gi, "").slice(0, 16);
}
