"""views.py - every page, plus the generated theme.css, sitemap and robots.

Pages are thin: they pick a template and hand it the catalog. All the copy lives in the
templates and content/*.json so changing a sentence never means touching Python.
"""
import json
import os

from flask import Blueprint, Response, abort, current_app, render_template, url_for

from .config import ROOT

bp = Blueprint("pages", __name__)


def _faq():
    with open(os.path.join(ROOT, "content", "faq.json")) as f:
        return json.load(f)


@bp.get("/")
def home():
    return render_template("pages/home.html", faq=_faq()[:4])


@bp.get("/flavors")
def flavors():
    return render_template("pages/flavors.html")


@bp.get("/flavors/<slug>")
def flavor(slug):
    cat = current_app.catalog
    f = cat.by_slug.get(slug)
    if not f:
        abort(404)
    others = [x for x in cat.flavors if x["slug"] != slug]
    # "Also in rotation": the two neighbours in the lineup, wrapping around.
    i = cat.flavors.index(f)
    n = len(cat.flavors)
    neighbours = [cat.flavors[(i + 1) % n], cat.flavors[(i + 2) % n], cat.flavors[(i - 1) % n]]
    return render_template("pages/flavor.html", f=f, others=others, neighbours=neighbours,
                           faq=[q for q in _faq() if q["q"] in ("How do I make it?", "What are the macros?",
                                                                 "How does pre-ordering work?")])


@bp.get("/build")
def build():
    return render_template("pages/build.html")


@bp.get("/how-it-works")
def how():
    return render_template("pages/how.html")


@bp.get("/our-story")
def story():
    return render_template("pages/story.html")


@bp.get("/faq")
def faq():
    items = _faq()
    faq_ld = [{"@type": "Question", "name": q["q"],
               "acceptedAnswer": {"@type": "Answer", "text": q["a"]}} for q in items]
    return render_template("pages/faq.html", faq=items, faq_ld=faq_ld)


@bp.get("/checkout")
def checkout():
    return render_template("pages/checkout.html")


@bp.get("/thanks")
def thanks():
    return render_template("pages/thanks.html")


@bp.get("/contact")
def contact():
    return render_template("pages/contact.html")


@bp.get("/privacy")
def privacy():
    return render_template("pages/privacy.html")


@bp.get("/terms")
def terms():
    return render_template("pages/terms.html")


@bp.get("/accessibility")
def accessibility():
    return render_template("pages/accessibility.html")


@bp.get("/theme.css")
def theme_css():
    body = render_template("theme.css.j2")
    resp = Response(body, mimetype="text/css")
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp


# Which pages belong in the sitemap, in the order a crawler should see them.
SITEMAP = ("pages.home", "pages.flavors", "pages.build", "pages.how", "pages.story", "pages.faq",
           "pages.contact")


@bp.get("/sitemap.xml")
def sitemap():
    s = current_app.config["OATS"]
    urls = [s.public_origin + url_for(e) for e in SITEMAP]
    urls += [s.public_origin + url_for("pages.flavor", slug=f["slug"]) for f in current_app.catalog.flavors]
    body = render_template("sitemap.xml.j2", urls=urls, updated=s.site["legal"]["updated_iso"])
    return Response(body, mimetype="application/xml")


@bp.get("/robots.txt")
def robots():
    s = current_app.config["OATS"]
    lines = ["User-agent: *", f"Disallow: {s.prefix}/checkout", f"Disallow: {s.prefix}/thanks",
             f"Disallow: {s.prefix}/api/", f"Sitemap: {s.public_origin}{url_for('pages.sitemap')}", ""]
    return Response("\n".join(lines), mimetype="text/plain")
