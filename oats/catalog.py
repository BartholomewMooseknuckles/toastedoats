"""catalog.py - the product data and the price math.

content/products.json is the one price table. The templates render it, the cart JS gets a
copy of it inline, and this module recomputes every line the client sends back - the browser's
numbers are never trusted, only its choices.
"""
import json
import os
import re

from .config import ROOT

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_QTY = 24
MAX_LINES = 20


class CatalogError(ValueError):
    """A line the client sent does not describe a real product."""


class Catalog:
    def __init__(self, data, subscribe_pct):
        self.data = data
        self.subscribe_pct = int(subscribe_pct)
        self.flavors = sorted(data["flavors"], key=lambda f: f["sort"])
        self.by_slug = {f["slug"]: f for f in self.flavors}
        self.boxes = list(data["boxes"])
        self.by_sku = {b["sku"]: b for b in self.boxes}

    # ------------------------------------------------------------------ prices
    def unit_cents(self, sku, subscribe=False):
        box = self.by_sku[sku]
        cents = box["price_cents"]
        if subscribe:
            cents = round(cents * (100 - self.subscribe_pct) / 100)
        return cents

    def per_serving_cents(self, sku, subscribe=False):
        box = self.by_sku[sku]
        return round(self.unit_cents(sku, subscribe) / box["units"])

    def savings_cents(self, sku):
        box = self.by_sku[sku]
        return (box["compare_cents"] or 0) - box["price_cents"] if box.get("compare_cents") else 0

    # ------------------------------------------------------------------- lines
    def normalise_line(self, raw):
        """Validate one cart line from the client and return a clean copy with prices.

        Raises CatalogError with a message safe to show the user.
        """
        if not isinstance(raw, dict):
            raise CatalogError("bad line")
        sku = str(raw.get("sku", ""))
        box = self.by_sku.get(sku)
        if not box:
            raise CatalogError(f"unknown product {sku[:40]!r}")
        try:
            qty = int(raw.get("qty", 1))
        except (TypeError, ValueError):
            raise CatalogError("bad quantity")
        if not 1 <= qty <= MAX_QTY:
            raise CatalogError(f"quantity must be between 1 and {MAX_QTY}")
        subscribe = bool(raw.get("subscribe"))
        line = {"sku": sku, "name": box["name"], "qty": qty, "subscribe": subscribe,
                "units": box["units"]}

        if box["type"] == "single":
            flavor = self.by_slug.get(str(raw.get("flavor", "")))
            if not flavor:
                raise CatalogError("pick a flavor for the 7-pack")
            line["flavor"] = flavor["slug"]
            line["label"] = f"{box['name']} · {flavor['name']}"
        elif box["type"] == "byo":
            picks = raw.get("picks")
            if not isinstance(picks, dict) or not picks:
                raise CatalogError("choose your flavors first")
            clean = {}
            for slug, n in picks.items():
                if slug not in self.by_slug:
                    raise CatalogError(f"unknown flavor {str(slug)[:40]!r}")
                try:
                    n = int(n)
                except (TypeError, ValueError):
                    raise CatalogError("bad pick count")
                if n > 0:
                    clean[slug] = n
            if sum(clean.values()) != box["units"]:
                raise CatalogError(f"a {box['name']} holds exactly {box['units']} pouches")
            line["picks"] = clean
            line["label"] = box["name"] + " · " + ", ".join(
                f"{n} {self.by_slug[s]['short_name'] if 'short_name' in self.by_slug[s] else self.by_slug[s]['name']}"
                for s, n in clean.items())
        else:
            line["label"] = box["name"]

        line["unit_cents"] = self.unit_cents(sku, subscribe)
        line["total_cents"] = line["unit_cents"] * qty
        return line

    def summarise(self, raw_lines, shipping):
        if not isinstance(raw_lines, list) or not raw_lines:
            raise CatalogError("your cart is empty")
        if len(raw_lines) > MAX_LINES:
            raise CatalogError("too many lines")
        lines = [self.normalise_line(r) for r in raw_lines]
        subtotal = sum(l["total_cents"] for l in lines)
        ship = 0 if subtotal >= shipping["free_threshold_cents"] else shipping["flat_cents"]
        return {"lines": lines, "subtotal_cents": subtotal, "shipping_cents": ship,
                "total_cents": subtotal + ship}

    # ----------------------------------------------------------------- clients
    def client_json(self, site, prefix, api_base):
        """The slice of the catalog the browser needs, embedded inline on every page."""
        return {
            "prefix": prefix,
            "apiBase": api_base,
            "checkoutMode": site["checkout"]["mode"],
            "subscribePct": self.subscribe_pct,
            "cadences": site["subscribe"]["cadences"],
            "defaultCadence": site["subscribe"]["default"],
            "freeShipCents": site["shipping"]["free_threshold_cents"],
            "flatShipCents": site["shipping"]["flat_cents"],
            "flavors": [{"slug": f["slug"], "name": f["name"], "short": f["short"],
                         "theme": f["theme"]} for f in self.flavors],
            "boxes": [{"sku": b["sku"], "name": b["name"], "type": b["type"], "units": b["units"],
                       "price_cents": b["price_cents"], "compare_cents": b.get("compare_cents"),
                       "popular": b.get("popular", False)} for b in self.boxes],
        }

    # ------------------------------------------------------------------- check
    def problems(self):
        """Everything `oats check` can prove wrong with the data, as a list of strings."""
        out = []
        slugs = [f["slug"] for f in self.flavors]
        if len(set(slugs)) != len(slugs):
            out.append("duplicate flavor slug")
        if len({f["sort"] for f in self.flavors}) != len(slugs):
            out.append("duplicate flavor sort order")
        for f in self.flavors:
            t = f["theme"]
            for k in ("bg", "soft", "ink", "accent", "accent_ink", "swirl"):
                if not HEX.match(t.get(k, "")):
                    out.append(f"{f['slug']}: theme.{k} is not a #rrggbb colour")
            for fg, bg, what in ((t["ink"], t["bg"], "ink on bg"), (t["accent_ink"], t["accent"], "accent_ink on accent")):
                if HEX.match(fg) and HEX.match(bg):
                    c = contrast(fg, bg)
                    if c < 4.5:
                        out.append(f"{f['slug']}: {what} contrast {c:.2f} < 4.5")
            for k in ("name", "short", "tagline", "description", "base", "swirl", "crunch", "claims"):
                if not f.get(k):
                    out.append(f"{f['slug']}: missing {k}")
        skus = [b["sku"] for b in self.boxes]
        if len(set(skus)) != len(skus):
            out.append("duplicate box sku")
        for b in self.boxes:
            if b["units"] <= 0 or b["price_cents"] <= 0:
                out.append(f"{b['sku']}: units and price must be positive")
            if b.get("compare_cents") and b["compare_cents"] <= b["price_cents"]:
                out.append(f"{b['sku']}: compare price must exceed the price")
            if b["type"] not in ("fixed", "byo", "single"):
                out.append(f"{b['sku']}: unknown type {b['type']}")
        if sum(1 for b in self.boxes if b.get("popular")) > 1:
            out.append("more than one box marked popular")
        return out


def _lum(hexcol):
    r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(fg, bg):
    a, b = _lum(fg), _lum(bg)
    hi, lo = max(a, b), min(a, b)
    return (hi + 0.05) / (lo + 0.05)


def load(site):
    with open(os.path.join(ROOT, "content", "products.json")) as f:
        data = json.load(f)
    return Catalog(data, site["subscribe"]["discount_pct"])
