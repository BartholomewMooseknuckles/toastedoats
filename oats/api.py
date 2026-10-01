"""api.py - the three things a visitor can send us: a signup, a message, a pre-order.

Signups and messages accept JSON or a plain form post, so the forms still work with
JavaScript off (they redirect back with ?ok=1). Pre-orders are JSON only: they need the cart,
which lives in the browser, and insisting on application/json means a cross-site form can
never post one.

Every response to a signup looks the same whether the address was new, a repeat, or a bot
filling the honeypot. There is nothing to learn by probing it.
"""
import base64
import hashlib
import json
import secrets

from flask import Blueprint, current_app, jsonify, redirect, request

from . import db
from .catalog import CatalogError
from .guard import Bucket, clean_email, clean_text, client_ip, same_site

bp = Blueprint("api", __name__, url_prefix="/api")
bucket = Bucket()

SIGNUP_KINDS = ("waitlist", "newsletter")


def _settings():
    return current_app.config["OATS"]


def _wants_json():
    return request.is_json or request.accept_mimetypes.best == "application/json"


def _payload():
    if request.is_json:
        data = request.get_json(silent=True)
        return data if isinstance(data, dict) else {}
    return request.form.to_dict()


def _back(ok=True, err=None):
    """Where a no-JS form goes after posting: back to the page it came from, under our prefix."""
    nxt = request.form.get("next") or request.headers.get("Referer", "") or ""
    prefix = _settings().prefix
    # Only ever redirect to our own paths - never to a host someone put in the form.
    path = nxt
    for o in _settings().allowed_origins:
        if path.startswith(o + "/"):
            path = path[len(o):]
            break
    if not path.startswith("/") or path.startswith("//") or not path.startswith(prefix + "/" if prefix else "/"):
        path = (prefix or "") + "/"
    path = path.split("#")[0].split("?")[0]
    return redirect(f"{path}?{'ok=1' if ok else 'err=' + err}#signup", code=303)


def _reject(status, code, message):
    if _wants_json() or request.is_json:
        return jsonify({"ok": False, "error": code, "message": message}), status
    return _back(ok=False, err=code)


def _gate():
    """The checks shared by every endpoint. Returns a response to send, or None to continue."""
    s = _settings()
    if not same_site(request, s.allowed_origins):
        db.bump(db.db(), "cross_origin")
        return jsonify({"ok": False, "error": "origin", "message": "Post this from the site."}), 403
    if not bucket.allow(client_ip(request)):
        db.bump(db.db(), "rate_limited")
        resp = jsonify({"ok": False, "error": "slow_down", "message": "Too many requests. Try again in a moment."})
        resp.status_code = 429
        resp.headers["Retry-After"] = str(bucket.retry_after())
        return resp
    return None


@bp.post("/signup")
def signup():
    blocked = _gate()
    if blocked:
        return blocked
    data = _payload()
    if clean_text(data.get("website"), 10):           # the honeypot
        db.bump(db.db(), "honeypot")
        return jsonify({"ok": True}) if _wants_json() else _back()
    email = clean_email(data.get("email"))
    if not email:
        db.bump(db.db(), "invalid")
        return _reject(400, "email", "That email doesn't look right.")
    kind = data.get("kind") if data.get("kind") in SIGNUP_KINDS else "waitlist"
    db.upsert_signup(db.db(), email, kind,
                     source=clean_text(data.get("source"), 80),
                     flavor=clean_text(data.get("flavor"), 60))
    print(f"signup ok kind={kind}", flush=True)
    return jsonify({"ok": True}) if _wants_json() else _back()


@bp.post("/message")
def message():
    blocked = _gate()
    if blocked:
        return blocked
    data = _payload()
    if clean_text(data.get("website"), 10):
        db.bump(db.db(), "honeypot")
        return jsonify({"ok": True}) if _wants_json() else _back()
    email = clean_email(data.get("email"))
    body = clean_text(data.get("message"), 2000)
    if not email:
        return _reject(400, "email", "That email doesn't look right.")
    if not body or len(body) < 3:
        return _reject(400, "message", "Say a little more than that.")
    db.upsert_signup(db.db(), email, "contact",
                     source=clean_text(data.get("source"), 80),
                     name=clean_text(data.get("name"), 80),
                     message=body)
    print("message ok", flush=True)
    return jsonify({"ok": True}) if _wants_json() else _back()


@bp.post("/preorder")
def preorder():
    if not request.is_json:
        return jsonify({"ok": False, "error": "json", "message": "Send JSON."}), 415
    blocked = _gate()
    if blocked:
        return blocked
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "json", "message": "Send a JSON object."}), 400
    if clean_text(data.get("website"), 10):
        db.bump(db.db(), "honeypot")
        return jsonify({"ok": True, "ref": "TO-" + secrets.token_hex(4).upper()}), 201
    email = clean_email(data.get("email"))
    if not email:
        return jsonify({"ok": False, "error": "email", "message": "That email doesn't look right."}), 400

    s = _settings()
    try:
        summary = current_app.catalog.summarise(data.get("lines"), s.site["shipping"])
    except CatalogError as e:
        db.bump(db.db(), "invalid")
        return jsonify({"ok": False, "error": "cart", "message": str(e)}), 400

    cadences = {c["id"] for c in s.site["subscribe"]["cadences"]}
    cadence = data.get("cadence") if data.get("cadence") in cadences else None
    subscribe = any(l["subscribe"] for l in summary["lines"])
    picks_json = json.dumps(summary["lines"], sort_keys=True, separators=(",", ":"))
    picks_hash = hashlib.sha256(picks_json.encode()).hexdigest()[:24]

    conn = db.db()
    ref = db.recent_preorder(conn, email, picks_hash)
    if not ref:
        ref = "TO-" + base64.b32encode(secrets.token_bytes(5)).decode().rstrip("=")
        db.insert_preorder(conn, ref, email,
                           clean_text(data.get("name"), 80), clean_text(data.get("zip"), 12),
                           picks_json, summary["subtotal_cents"], summary["shipping_cents"],
                           subscribe, cadence if subscribe else None,
                           clean_text(data.get("notes"), 500), picks_hash,
                           clean_text(data.get("source"), 80))
        db.bump(conn, "preorder")
        print(f"preorder ok ref={ref} lines={len(summary['lines'])} total={summary['total_cents']}", flush=True)
    return jsonify({"ok": True, "ref": ref, "subtotal_cents": summary["subtotal_cents"],
                    "shipping_cents": summary["shipping_cents"], "total_cents": summary["total_cents"]}), 201
