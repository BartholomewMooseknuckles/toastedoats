"""freeze.py - write the site out as static files.

Not used in production (gunicorn serves the pages), but it means the whole site can move to
Cloudflare Pages or any static host in an afternoon: `freeze` renders every page through the
test client, copies static/, and points the inline config at wherever the API ends up.
"""
import os
import shutil

from flask import url_for


def pages(app):
    """Every GET route with no parameters, plus one PDP per flavor."""
    urls = []
    s = app.config["OATS"]
    # base_url carries the prefix, so url_for() returns the same paths a browser would use
    with app.test_request_context(base_url="http://localhost" + s.prefix):
        for rule in app.url_map.iter_rules():
            if "GET" not in rule.methods or rule.arguments or rule.endpoint == "static":
                continue
            if rule.endpoint in ("healthz",):
                continue
            urls.append(url_for(rule.endpoint))
        for f in app.catalog.flavors:
            urls.append(url_for("pages.flavor", slug=f["slug"]))
    return urls


def freeze(app, out_dir, api_base=None, log=print):
    s = app.config["OATS"]
    if api_base:
        app.config["OATS_API_BASE"] = api_base.rstrip("/")
    client = app.test_client()
    root = os.path.join(out_dir, s.prefix.strip("/")) if s.prefix else out_dir
    os.makedirs(root, exist_ok=True)

    n = 0
    for url in pages(app):
        r = client.get(url)
        rel = url[len(s.prefix):] if s.prefix else url
        rel = rel.strip("/")
        if rel == "" or "." not in rel.rsplit("/", 1)[-1]:
            path = os.path.join(root, rel, "index.html")
        else:
            path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(r.data)
        n += 1
    # A 404 page for hosts that look for one at the root.
    r = client.get((s.prefix or "") + "/this-page-does-not-exist")
    with open(os.path.join(out_dir, "404.html"), "wb") as f:
        f.write(r.data)

    static_out = os.path.join(root, "static")
    if os.path.isdir(static_out):
        shutil.rmtree(static_out)
    shutil.copytree(app.static_folder, static_out)
    log(f"froze {n} pages + static -> {out_dir}", flush=True)
    return n
