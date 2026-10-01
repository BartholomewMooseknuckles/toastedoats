"""config.py - settings from the environment plus content/site.json.

Two sources on purpose. site.json is brand content that is safe in git and that the owner
edits (prices, copy flags, social handles). oats.env holds what differs per machine or must
stay out of git (port, public origin, one day Stripe keys). Nothing here reads a secret.
"""
import json
import os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.abspath(__file__))


@dataclass(frozen=True)
class Settings:
    prefix: str            # URL path the site lives under, e.g. "/oats" ("" = site root)
    public_origin: str     # scheme + host the public sees, used for canonical/OG/sitemap URLs
    allowed_origins: tuple # Origins allowed to POST to /api/*
    db_path: str
    port: int
    dev: bool
    site: dict


def _site():
    with open(os.path.join(ROOT, "content", "site.json")) as f:
        return json.load(f)


def load():
    prefix = os.environ.get("OATS_PREFIX", "/oats").strip().rstrip("/")
    if prefix and not prefix.startswith("/"):
        prefix = "/" + prefix
    port = int(os.environ.get("OATS_PORT", "8090"))

    # No public origin means we are on a laptop: trust the two ways a browser reaches a dev
    # server. In production the origin is the one place a form may be posted from.
    origin = os.environ.get("OATS_PUBLIC_ORIGIN", "").strip().rstrip("/")
    dev = not origin
    if dev:
        origin = f"http://127.0.0.1:{port}"
        allowed = (origin, f"http://localhost:{port}")
    else:
        extra = [o.strip().rstrip("/") for o in os.environ.get("OATS_ALLOWED_ORIGINS", "").split(",")]
        allowed = tuple(dict.fromkeys([origin] + [o for o in extra if o]))

    return Settings(
        prefix=prefix,
        public_origin=origin,
        allowed_origins=allowed,
        db_path=os.environ.get("OATS_DB", os.path.join(ROOT, "oats.db")),
        port=port,
        dev=dev,
        site=_site(),
    )
