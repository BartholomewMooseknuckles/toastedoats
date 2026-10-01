// Entry point. Each [data-module] element names the function that wires it.
import { initAddButtons } from "./cart.js";
import { initDrawer, openDrawer } from "./drawer.js";
import { initForms } from "./forms.js";
import { hero, morph, ritual, initReveal } from "./scroll.js";
import { builder } from "./builder.js";
import { buy } from "./buy.js";
import { checkout, thanks } from "./checkout.js";
import { nav, subtoggle } from "./nav.js";

const modules = { hero, morph, ritual, builder, buy, checkout, thanks, nav, subtoggle };

initDrawer();
initAddButtons(openDrawer);
initForms();
document.querySelectorAll("[data-module]").forEach((el) => {
  const fn = modules[el.dataset.module];
  if (fn) {
    try {
      fn(el);
    } catch (err) {
      console.error(`module ${el.dataset.module}:`, err);
    }
  }
});
initReveal();
document.documentElement.classList.add("js");
