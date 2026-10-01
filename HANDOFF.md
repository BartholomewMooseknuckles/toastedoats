# Toasted Oats — deploy handoff

This repo is the whole site. Target URL: **https://2birds1joint.org/oats/**

Tested: 22/22 pytest, every page renders under the prefix, zero console errors, pre-order
flow end to end, static export. Not done: the actual deploy (no server access from the
build sandbox) and the Cloudflare tunnel rule.

## 1. On the server, as root (the box that runs cloudflared)

```bash
# code
test -d /opt/toastedoats || git clone https://github.com/BartholomewMooseknuckles/toastedoats /opt/toastedoats
cd /opt/toastedoats && git pull
# (private repo with no git creds on the box? download the zip from GitHub and unzip to /opt/toastedoats instead)

# install: /opt/oats (venv, env file, sqlite, units) — idempotent, re-run after every pull
bash install.sh

# settings — the defaults are already right for 2birds1joint.org on port 8090
cat /opt/oats/oats.env

# run
systemctl enable --now toasted-oats
curl -s 127.0.0.1:8090/healthz            # -> {"db":true,"ok":true}
curl -sI 127.0.0.1:8090/oats/ | head -1   # -> HTTP/1.1 200 OK
```

Needs `python3 -m venv` (Debian/Ubuntu: `apt-get install -y python3-venv`). The service
runs as the `newsfeed` user if it exists, creating it otherwise; `OATS_USER=someone bash
install.sh` to change.

## 2. Cloudflare — route the path to the service

Dashboard-managed tunnel: Zero Trust → Networks → Tunnels → *your tunnel* → Public
Hostname → **Add a public hostname**:

| field | value |
|---|---|
| Subdomain | *(blank)* |
| Domain | `2birds1joint.org` |
| Path | `^/?oats(/\|$)` |
| Type / URL | `HTTP` / `127.0.0.1:8090` |

Drag it **above** any rule for `2birds1joint.org` with an empty path (the catch-all),
otherwise the catch-all wins.

Config-file tunnel instead: paste the block from `deploy/cloudflared-ingress.yml` into
`/etc/cloudflared/config.yml` above the existing site rule, then
`systemctl restart cloudflared`.

Then two more clicks:
- Zero Trust → Access → Applications: make sure **no Access app covers `/oats`**.
- Cloudflare → Rules → Configuration Rules → create for *URI Path starts with `/oats`*:
  turn **off** Rocket Loader, Auto Minify, Email Obfuscation (they rewrite JS and break
  the site's strict Content-Security-Policy).

## 3. Verify

```bash
curl -sI https://2birds1joint.org/oats/ | grep -iE "^HTTP|cf-cache-status|cache-control"
# HTTP/2 200, cf-cache-status: DYNAMIC, cache-control: no-cache
curl -sI "https://2birds1joint.org/oats/static/css/base.css?v=1" | grep -i cache-control
# public, max-age=31536000, immutable
```

Open https://2birds1joint.org/oats/ on a phone and a laptop: add a 7-pack, build a box,
reserve it with a test email, land on /thanks. Then:

```bash
cd /opt/oats/app && sudo -u newsfeed env $(grep -v '^#' /opt/oats/oats.env | xargs) \
  /opt/oats/venv/bin/python -m oats stats
```

## 4. Day to day

| | |
|---|---|
| Export pre-orders / signups | `… python -m oats export-csv preorders > preorders.csv` (same env prefix as above; `signups` likewise, `--since 2026-11-01` optional) |
| Logs | `journalctl -u toasted-oats -f` (no emails or IPs are ever logged) |
| Update | `cd /opt/toastedoats && git pull && bash install.sh` (restarts the service) |
| Backups | nightly to `/opt/oats/backup/`, 30 days (`toasted-oats-backup.timer`) |
| Edit copy / prices / flags | `oats/content/*.json`, see `README.md`; run `python -m oats check` before pushing |

## 5. Before you call it launched

All in `oats/content/site.json` unless noted:
- `contact.email` is `hello@2birds1joint.org`, Instagram/TikTok are `toastedoats`, `launch.eta` is "Spring 2027" — placeholders.
- Pricing is a category-norm placeholder: Starter 7 = $29, Build-a-Box 14 = $54, 28 = $99, 7-packs $29, subscribe 15% off, free shipping over $45 (`products.json → boxes[]`, `subscribe.discount_pct`, `shipping`).
- Nutrition numbers are **hidden** (`claims_locked: false`) until the formula is final; the site says "Protein-forward / Fiber-rich" instead. Flip it to true when the co-packer signs off, and replace each flavor's placeholder allergen line in `products.json`.
- No reviews, no star ratings, on purpose. `reviews_enabled` stays false until there are real ones.
- Terms/privacy are plain-English drafts — have counsel read them. Prop 65 (acrylamide in toasted grains) may need a California warning.
- Real photos: `shots.md` is the shot list; drop files in `art/`, point `oats/content/images.json` at them, `python -m oats images`, `python -m oats.tools.og`.

Coming-soon mode (`site.json → mode: "coming_soon"`) is reserved but not built yet — that's
the next job.

## 6. Paste this into Claude Code (or any agent) running as root on the server

```
Deploy the Toasted Oats site from the GitHub repo BartholomewMooseknuckles/toastedoats
(branch main). Follow HANDOFF.md in that repo exactly: clone or update it at
/opt/toastedoats, run `bash install.sh`, check /opt/oats/oats.env
(OATS_PUBLIC_ORIGIN=https://2birds1joint.org, OATS_PORT=8090), then
`systemctl enable --now toasted-oats` and confirm `curl -s 127.0.0.1:8090/healthz` returns
ok:true and `curl -sI 127.0.0.1:8090/oats/` returns 200. If this box runs cloudflared from
/etc/cloudflared/config.yml, add the ingress rule from deploy/cloudflared-ingress.yml above
the existing 2birds1joint.org rule and restart cloudflared; if the tunnel is
dashboard-managed, stop and tell me the exact Public Hostname rule to add (domain
2birds1joint.org, path ^/?oats(/|$), service http://127.0.0.1:8090). Do not touch any
other service, do not change anything else on the server, and report every command you
ran and its output.
```
