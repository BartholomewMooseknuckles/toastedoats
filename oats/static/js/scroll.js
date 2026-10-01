// Scroll-driven sections: the hero flavor cycle, the pinned flavor morph, the five-step
// ritual, and the small reveal-on-enter fades. One passive scroll listener, one rAF.
import { reducedMotion } from "./config.js";

const sections = [];
let ticking = false;

function progressOf(el) {
  // 0 when the section's top hits the viewport top, 1 when its bottom leaves the pinned stage.
  const r = el.getBoundingClientRect();
  const span = r.height - window.innerHeight;
  if (span <= 0) return r.top < 0 ? 1 : 0;
  return Math.min(1, Math.max(0, -r.top / span));
}

function tick() {
  ticking = false;
  sections.forEach((s) => s.update());
}

function onScroll() {
  if (!ticking) {
    ticking = true;
    requestAnimationFrame(tick);
  }
}

function register(section) {
  sections.push(section);
  if (sections.length === 1) {
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
  }
  section.update();
}

function setActive(el, i) {
  el.querySelectorAll(".is-active").forEach((n) => n.classList.remove("is-active"));
  el.querySelectorAll(`[data-i="${i}"]`).forEach((n) => n.classList.add("is-active"));
  const slide = el.querySelector(`.hero-slide[data-i="${i}"], .morph-slide[data-i="${i}"]`);
  if (slide?.dataset.flavor) el.dataset.flavor = slide.dataset.flavor;
}

// ---------------------------------------------------------------- hero
export function hero(el) {
  const n = el.querySelectorAll(".hero-slide").length;
  const dots = el.querySelectorAll("[data-goto]");
  let i = 0;
  let timer = null;
  const show = (k) => {
    i = (k + n) % n;
    setActive(el, i);
    dots.forEach((d, j) => (j === i ? d.setAttribute("aria-current", "true") : d.removeAttribute("aria-current")));
  };
  const start = () => {
    if (reducedMotion.matches || timer) return;
    timer = setInterval(() => show(i + 1), 3200);
  };
  const stop = () => {
    clearInterval(timer);
    timer = null;
  };
  dots.forEach((d) =>
    d.addEventListener("click", () => {
      show(Number(d.dataset.goto));
      stop();
    })
  );
  el.addEventListener("pointerenter", stop);
  el.addEventListener("pointerleave", start);
  el.addEventListener("focusin", stop);
  document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
  show(0);
  start();
}

// --------------------------------------------------------------- morph
export function morph(el) {
  const n = el.querySelectorAll(".morph-slide").length;
  let current = -1;
  register({
    update() {
      const p = progressOf(el);
      const i = Math.min(n - 1, Math.floor(p * n));
      if (i !== current) {
        current = i;
        setActive(el, i);
      }
    },
  });
}

// -------------------------------------------------------------- ritual
export function ritual(el) {
  const steps = el.querySelectorAll(".step");
  const n = steps.length;
  const sideBySide = window.matchMedia("(min-width: 900px)");
  let current = 0;
  register({
    update() {
      // Side by side, the copy scrolls next to the stage, so the active step is the one at
      // the stage's centre. Stacked (phones, tablets), the copy scrolls *under* the sticky
      // stage, so the active step is the one in the band you can actually read below it.
      const stage = el.querySelector(".ritual-stage");
      const sr = stage && stage.getBoundingClientRect();
      let focus = window.innerHeight / 2;
      if (sr && sideBySide.matches) focus = sr.top + sr.height / 2;
      else if (sr) focus = sr.bottom + Math.max(0, window.innerHeight - sr.bottom) * 0.45;
      let best = 1;
      let bestD = Infinity;
      let stepP = 0;
      steps.forEach((s, k) => {
        const r = s.getBoundingClientRect();
        const c = r.top + r.height / 2;
        const d = Math.abs(c - focus);
        if (d < bestD) {
          bestD = d;
          best = k + 1;
          // progress through this step: 0 when its top reaches the focus line, 1 when its bottom does
          stepP = Math.min(1, Math.max(0, (focus - r.top) / r.height));
        }
      });
      if (best !== current) {
        current = best;
        el.dataset.active = String(best);
      }
      el.style.setProperty("--step-p", stepP.toFixed(3));
      el.style.setProperty("--p", ((best - 1 + stepP) / n).toFixed(3));
    },
  });
}

// -------------------------------------------------------------- reveal
export function initReveal() {
  const targets = document.querySelectorAll(".section > .wrap > .eyebrow, .section-head, .fcard, .tile, .box, .tip, .ingredients li, .story-cell, .steps3 li");
  if (reducedMotion.matches || !("IntersectionObserver" in window)) return;
  targets.forEach((t, i) => {
    t.classList.add("reveal");
    if (t.matches(".fcard, .tile, .box, .tip, .ingredients li, .story-cell, .steps3 li")) {
      t.classList.add("reveal-d" + ((i % 3) + 1));
    }
  });
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("is-in");
          io.unobserve(e.target);
        }
      });
    },
    { rootMargin: "0px 0px -8% 0px", threshold: 0.08 }
  );
  targets.forEach((t) => io.observe(t));
  // Whatever the observer has not reached by now gets shown anyway: a fade-in is a
  // nicety, invisible content is a bug.
  setTimeout(() => targets.forEach((t) => t.classList.add("is-in")), 3000);
}
