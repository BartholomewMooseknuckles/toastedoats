import { config } from "./config.js";

// Same-origin JSON post. No credentials, no cookies - there are none.
export async function postJSON(path, body) {
  const r = await fetch(config.apiBase + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    credentials: "omit",
    body: JSON.stringify(body),
  });
  let data = {};
  try {
    data = await r.json();
  } catch {
    /* non-JSON error page */
  }
  return { ok: r.ok && data.ok !== false, status: r.status, data };
}
