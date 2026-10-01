// Signup and contact forms. They work as plain POSTs without this file; with it they stay
// on the page and show the result inline.
import { postJSON } from "./api.js";

const COPY = {
  signup: "You're in. We'll email you when the first batch is ready.",
  message: "Got it. A human will reply.",
};

export function initForms() {
  document.querySelectorAll("form[data-form]").forEach((form) => {
    const kind = form.dataset.form;
    const status = form.querySelector("[data-status]");
    const btn = form.querySelector('button[type="submit"]');
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(form);
      const body = Object.fromEntries(fd.entries());
      delete body.next;
      status.classList.remove("is-err");
      status.textContent = "";
      btn.classList.add("is-busy");
      try {
        const res = await postJSON(kind === "signup" ? "/signup" : "/message", body);
        if (res.ok) {
          status.textContent = COPY[kind];
          form.querySelectorAll(".input").forEach((i) => (i.value = ""));
        } else {
          status.classList.add("is-err");
          status.textContent = res.data.message || "That didn't go through. Try again?";
        }
      } catch {
        status.classList.add("is-err");
        status.textContent = "No connection. Try again in a moment.";
      } finally {
        btn.classList.remove("is-busy");
      }
    });
  });
}
