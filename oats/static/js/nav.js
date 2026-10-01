// Header: the mobile menu and the shop section's subscribe switch.
export function nav(header) {
  const toggle = header.querySelector(".nav-toggle");
  const menu = header.querySelector(".nav");
  if (!toggle || !menu) return;
  const set = (open) => {
    toggle.setAttribute("aria-expanded", String(open));
    menu.classList.toggle("is-open", open);
  };
  toggle.addEventListener("click", () => set(toggle.getAttribute("aria-expanded") !== "true"));
  document.addEventListener("keydown", (e) => e.key === "Escape" && set(false));
  menu.addEventListener("click", (e) => e.target.closest("a") && set(false));
  window.matchMedia("(min-width: 900px)").addEventListener("change", () => set(false));
}

export function subtoggle(el) {
  const sw = el.querySelector("[data-sub-switch]");
  const apply = (on) => {
    sw.setAttribute("aria-checked", String(on));
    document.querySelectorAll("[data-price-once], [data-per-once]").forEach((x) => (x.hidden = on));
    document.querySelectorAll("[data-price-sub], [data-per-sub]").forEach((x) => (x.hidden = !on));
  };
  sw.addEventListener("click", () => apply(sw.getAttribute("aria-checked") !== "true"));
  apply(false);
}
