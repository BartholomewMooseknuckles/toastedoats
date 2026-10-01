"""guard.py - the checks every /api/* request goes through.

Cheap, boring, and in this order on purpose:
  1. Is the request from our own site?  (Sec-Fetch-Site, then Origin, then Referer)
  2. Is this IP sending too much?        (token bucket, in memory, one process)
  3. Did a bot fill the field humans cannot see?  (honeypot - answered with a fake success)
  4. Is the input sane?                  (length caps, an email regex that errs liberal)

Behind cloudflared every request arrives from 127.0.0.1, so the client IP is taken from
CF-Connecting-IP - but only when the peer really is loopback, the same rule dashboard.py
uses for the Access header. From the LAN that header could be forged, so there we use the
socket address.
"""
import re
import threading
import time

TRUSTED_PROXIES = {"127.0.0.1", "::1"}

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def client_ip(request):
    if request.remote_addr in TRUSTED_PROXIES:
        cf = request.headers.get("CF-Connecting-IP", "").strip()
        if cf:
            return cf
        xff = request.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()
    return request.remote_addr or "?"


def same_site(request, allowed_origins):
    """True if a browser on our own site sent this. Nothing else gets to post."""
    sfs = request.headers.get("Sec-Fetch-Site", "").lower()
    if sfs == "same-origin":
        return True
    if sfs in ("cross-site", "same-site"):
        return False
    origin = request.headers.get("Origin", "").rstrip("/")
    if origin:
        return origin in allowed_origins
    referer = request.headers.get("Referer", "")
    if referer:
        return any(referer == o or referer.startswith(o + "/") for o in allowed_origins)
    return False


class Bucket:
    """Per-IP token bucket. `burst` requests at once, then one every `every` seconds."""

    def __init__(self, burst=5, every=12.0, max_keys=10000):
        self.burst, self.every, self.max_keys = burst, every, max_keys
        self._lock = threading.Lock()
        self._state = {}   # ip -> [tokens, last_refill]

    def allow(self, ip, now=None):
        now = time.monotonic() if now is None else now
        with self._lock:
            if len(self._state) > self.max_keys:
                # Forget the quiet ones rather than grow without bound.
                stale = [k for k, (_, t) in self._state.items() if now - t > self.every * self.burst]
                for k in stale:
                    del self._state[k]
                if len(self._state) > self.max_keys:
                    self._state.clear()
            tokens, last = self._state.get(ip, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) / self.every)
            if tokens >= 1:
                self._state[ip] = [tokens - 1, now]
                return True
            self._state[ip] = [tokens, now]
            return False

    def retry_after(self):
        return int(self.every)


def clean_email(value):
    if not isinstance(value, str):
        return None
    e = value.strip().lower()
    if len(e) > 254 or not EMAIL_RE.match(e):
        return None
    return e


def clean_text(value, maxlen):
    if value is None:
        return None
    s = CONTROL_RE.sub("", str(value)).strip()
    return s[:maxlen] or None
