"""app.py - the Flask app factory and the one piece of plumbing that matters: the prefix.

The site lives at /oats on a domain that has other things at /. Cloudflare's tunnel sends us
the full path, prefix included, and nothing strips it. PrefixMiddleware moves the prefix from
PATH_INFO into SCRIPT_NAME before Flask sees the request, which is the WSGI way of saying
"this app is mounted here". After that every url_for(), every static URL, every redirect
comes out prefixed with no template ever mentioning it - and the same code runs unprefixed on
a laptop by setting OATS_PREFIX to an empty string.
"""
import hashlib
import json
import os

from flask import Flask, jsonify, render_template, request, url_for

from . import api, catalog as catalog_mod, config, db, views
from .config import ROOT

CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
       "font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'; "
       "frame-ancestors 'none'; object-src 'none'")


class PrefixMiddleware:
    """Mount the app under `prefix`. Anything outside it is a 404, except bare /healthz."""

    def __init__(self, wsgi_app, prefix):
        self.app = wsgi_app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        # gunicorn will honour a SCRIPT_NAME *request header* if a client sends one; rebuilding
        # the full path first makes that harmless.
        full = environ.get("SCRIPT_NAME", "") + environ.get("PATH_INFO", "")
        if not self.prefix:
            environ["SCRIPT_NAME"], environ["PATH_INFO"] = "", full or "/"
            return self.app(environ, start_response)
        if full == "/healthz":
            environ["SCRIPT_NAME"], environ["PATH_INFO"] = "", "/healthz"
            return self.app(environ, start_response)
        if full == self.prefix or full.startswith(self.prefix + "/"):
            environ["SCRIPT_NAME"] = self.prefix
            environ["PATH_INFO"] = full[len(self.prefix):] or "/"
            return self.app(environ, start_response)
        if full in ("", "/"):
            start_response("302 Found", [("Location", self.prefix + "/"), ("Content-Length", "0")])
            return [b""]
        start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
        return [b"not found\n"]


def _asset_hasher(static_dir):
    cache = {}

    def asset(path):
        v = cache.get(path)
        if v is None:
            full = os.path.join(static_dir, path)
            try:
                with open(full, "rb") as f:
                    v = hashlib.sha1(f.read()).hexdigest()[:8]
            except OSError:
                v = "0"
            cache[path] = v
        return url_for("static", filename=path) + "?v=" + v
    return asset


def _money(cents, trim=True):
    d = cents / 100
    if trim and d == int(d):
        return f"${int(d):,}"
    return f"${d:,.2f}"


def create_app(settings=None):
    settings = settings or config.load()
    site = settings.site
    app = Flask(__name__, static_folder="static", template_folder="templates", static_url_path="/static")
    app.url_map.strict_slashes = False          # /oats/faq and /oats/faq/ both answer; canonical is the former
    app.config.update(
        OATS=settings,
        OATS_DB=settings.db_path,
        MAX_CONTENT_LENGTH=8 * 1024,            # the biggest legitimate pre-order is a few hundred bytes
        SEND_FILE_MAX_AGE_DEFAULT=31536000,
        OATS_API_BASE=None,                     # freeze overrides this when the API lives elsewhere
    )
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    app.catalog = catalog_mod.load(site)
    with open(os.path.join(ROOT, "static", "img", "manifest.json")) as f:
        app.images = json.load(f)

    app.wsgi_app = PrefixMiddleware(app.wsgi_app, settings.prefix)
    app.register_blueprint(views.bp)
    app.register_blueprint(api.bp)
    app.teardown_appcontext(db.close)

    asset = _asset_hasher(app.static_folder)
    theme_version = hashlib.sha1(json.dumps(app.catalog.data, sort_keys=True).encode()).hexdigest()[:8]

    # A real ISO date for the sitemap, derived once from the human-readable one in site.json.
    import datetime as dt
    try:
        site["legal"]["updated_iso"] = dt.datetime.strptime(site["legal"]["updated"], "%B %d, %Y").date().isoformat()
    except ValueError:
        site["legal"]["updated_iso"] = dt.date.today().isoformat()

    @app.context_processor
    def _globals():
        s = settings
        api_base = app.config["OATS_API_BASE"] or (s.prefix + "/api")
        return {
            "site": site,
            "catalog": app.catalog,
            "prefix": s.prefix,
            "public_origin": s.public_origin,
            "asset": asset,
            "theme_url": url_for("pages.theme_css") + "?v=" + theme_version,
            "abs_url": lambda endpoint, **kw: s.public_origin + url_for(endpoint, **kw),
            "img": lambda name: app.images[name],
            "images": app.images,
            "money": _money,
            "per_serving": lambda sku, sub=False: _money(app.catalog.per_serving_cents(sku, sub), trim=False),
            "unit": lambda sku, sub=False: _money(app.catalog.unit_cents(sku, sub)),
            "savings": lambda sku: app.catalog.savings_cents(sku),
            "claims": lambda f: f["claims"]["numbers"] if site["claims_locked"] else None,
            "client_config": json.dumps(app.catalog.client_json(site, s.prefix, api_base), separators=(",", ":")),
            "year": dt.date.today().year,
        }

    @app.get("/healthz")
    def healthz():
        ok = True
        try:
            db.db().execute("SELECT 1")
        except Exception:                        # noqa: BLE001 - any failure means "not healthy"
            ok = False
        return jsonify({"ok": ok, "db": ok}), (200 if ok else 503)

    @app.after_request
    def _headers(resp):
        resp.headers["Content-Security-Policy"] = CSP
        resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        path = request.path
        if path.startswith("/api/") or path == "/healthz":
            resp.headers["Cache-Control"] = "no-store"
        elif path.startswith("/static/"):
            resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        elif resp.mimetype == "text/html":
            # Browsers revalidate every time; Cloudflare keeps it DYNAMIC. A deploy never
            # leaves anyone looking at yesterday's prices.
            resp.headers["Cache-Control"] = "no-cache"
            if request.method == "GET" and 200 <= resp.status_code < 300:
                resp.add_etag()
                resp.make_conditional(request)
        return resp

    @app.errorhandler(404)
    def _404(_):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "error": "not_found"}), 404
        return render_template("pages/404.html"), 404

    @app.errorhandler(405)
    def _405(_):
        return jsonify({"ok": False, "error": "method"}), 405

    @app.errorhandler(413)
    def _413(_):
        return jsonify({"ok": False, "error": "too_large", "message": "That's more than a pre-order needs."}), 413

    return app
