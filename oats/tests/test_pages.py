"""Every page renders under the prefix and never leaks an unprefixed link."""
import re

from oats.freeze import pages

from .conftest import ORIGIN, PREFIX

LINK = re.compile(r'(?:href|src|action)="([^"]+)"')
SRCSET = re.compile(r'srcset="([^"]+)"')


def test_every_page_renders(client, app):
    urls = pages(app)
    assert len(urls) >= 20
    for url in urls:
        r = client.get(url)
        assert r.status_code == 200, url
        assert url.startswith(PREFIX)


def test_links_are_prefixed(client, app):
    for url in pages(app):
        html = client.get(url).get_data(as_text=True)
        for link in LINK.findall(html):
            ok = link.startswith((PREFIX + "/", "http://", "https://", "mailto:", "#", "tel:"))
            assert ok, f"{url}: unprefixed link {link!r}"
        for srcset in SRCSET.findall(html):
            for cand in srcset.split(","):
                assert cand.strip().startswith(PREFIX + "/static/"), f"{url}: {cand!r}"


def test_outside_prefix_is_404_but_healthz_and_root_work(client):
    assert client.get("/faq").status_code == 404
    assert client.get("/healthz").status_code == 200
    assert client.get(PREFIX + "/healthz").status_code == 200
    r = client.get("/")
    assert r.status_code == 302 and r.headers["Location"].endswith(PREFIX + "/")
    assert client.get(PREFIX).status_code == 200          # no trailing slash is the home page
    assert client.get(PREFIX + "/faq/").status_code == 200  # trailing slash tolerated


def test_unknown_flavor_404(client):
    r = client.get(PREFIX + "/flavors/nope")
    assert r.status_code == 404
    assert b"Just crumbs" in r.data


def test_sitemap_and_robots_use_public_origin(client):
    xml = client.get(PREFIX + "/sitemap.xml").get_data(as_text=True)
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    assert len(locs) >= 14
    assert all(l.startswith(ORIGIN + PREFIX + "/") for l in locs)
    robots = client.get(PREFIX + "/robots.txt").get_data(as_text=True)
    assert f"Sitemap: {ORIGIN}{PREFIX}/sitemap.xml" in robots


def test_headers(client):
    r = client.get(PREFIX + "/")
    assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-cache"
    assert "ETag" in r.headers
    s = client.get(PREFIX + "/static/css/base.css")
    assert s.status_code == 200
    assert "immutable" in s.headers["Cache-Control"]
    t = client.get(PREFIX + "/theme.css")
    assert t.mimetype == "text/css" and 'data-flavor="vanilla-crunch"' in t.get_data(as_text=True)


def test_claims_hidden_until_locked(client, app):
    html = client.get(PREFIX + "/flavors/vanilla-crunch").get_data(as_text=True)
    assert "g protein" not in html.lower()
    assert "Protein-forward" in html
    assert "PreOrder" in html                     # JSON-LD availability
    app.config["OATS"].site["claims_locked"] = True
    html = client.get(PREFIX + "/flavors/vanilla-crunch").get_data(as_text=True)
    assert "20g" in html and "protein" in html


def test_canonical_and_og(client):
    html = client.get(PREFIX + "/flavors/strawberry-shortcake").get_data(as_text=True)
    assert f'<link rel="canonical" href="{ORIGIN}{PREFIX}/flavors/strawberry-shortcake">' in html
    assert f'property="og:image" content="{ORIGIN}{PREFIX}/static/img/card-strawberry-shortcake-' in html
