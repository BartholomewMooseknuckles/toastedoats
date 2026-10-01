#!/usr/bin/env python3
"""python -m oats - run and maintain the Toasted Oats site.

    python -m oats serve [--port 8090] [--debug]     dev server (production is gunicorn)
    python -m oats init-db                           create the database file
    python -m oats export-csv signups|preorders [--since YYYY-MM-DD]
    python -m oats stats                             counts and pre-order value
    python -m oats images [--only SLOT]              re-cut the mockups into static/img
    python -m oats check                             content sanity: prices, colours, images, templates
    python -m oats freeze [--out oats/dist] [--api-base URL]
"""
import argparse
import json
import os
import sys

from . import config, db
from .config import ROOT


def _app():
    from .app import create_app
    return create_app()


def cmd_serve(args):
    app = _app()
    s = app.config["OATS"]
    print(f"serving at http://127.0.0.1:{args.port}{s.prefix}/  (prefix={s.prefix!r}, db={s.db_path})", flush=True)
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=args.debug)


def cmd_init_db(args):
    s = config.load()
    db.connect(s.db_path).close()
    print(f"ok {s.db_path}", flush=True)


def cmd_export(args):
    s = config.load()
    conn = db.connect(s.db_path)
    n = db.export_csv(conn, args.table, args.since)
    print(f"{n} rows", file=sys.stderr, flush=True)


def cmd_stats(args):
    s = config.load()
    print(json.dumps(db.stats(db.connect(s.db_path)), indent=1))


def cmd_images(args):
    from .tools import slice as slicer
    slicer.run(args.only)


def cmd_backup(args):
    """Copy the live database with SQLite's online backup API, keep 30 days of copies."""
    import datetime as dt
    import glob
    import sqlite3
    s = config.load()
    os.makedirs(args.dir, exist_ok=True)
    dest = os.path.join(args.dir, f"oats-{dt.date.today().isoformat()}.db")
    src = sqlite3.connect(s.db_path)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    cutoff = dt.date.today() - dt.timedelta(days=args.keep_days)
    for old in glob.glob(os.path.join(args.dir, "oats-*.db")):
        stamp = os.path.basename(old)[5:15]
        try:
            if dt.date.fromisoformat(stamp) < cutoff:
                os.remove(old)
        except ValueError:
            pass
    print(f"ok {dest}", flush=True)


def cmd_freeze(args):
    from .freeze import freeze
    freeze(_app(), args.out, args.api_base)


def cmd_check(args):
    problems = []
    s = config.load()
    try:
        app = _app()
    except Exception as e:                               # noqa: BLE001 - report, don't trace
        print(f"FAIL app will not start: {e}")
        sys.exit(1)
    problems += app.catalog.problems()

    # Every image slot the templates can ask for must exist.
    manifest = app.images
    need = ["hero-bowl", "after-hours", "lineup", "system-base", "system-swirl", "system-crunch"]
    need += [f"ritual-{i}-{n}" for i, n in enumerate(("base", "milk", "set", "swirl", "crunch"), 1)]
    for f in app.catalog.flavors:
        need += [f"card-{f['slug']}", f"pouch-{f['slug']}", f"macro-{f['slug']}"]
    for name in need:
        if name not in manifest:
            problems.append(f"image slot missing: {name} (run `python -m oats images`)")
        else:
            for w in manifest[name]["widths"]:
                for fmt in manifest[name]["formats"]:
                    p = os.path.join(ROOT, "static", "img", f"{name}-{w}.{fmt}")
                    if not os.path.exists(p):
                        problems.append(f"image file missing: {os.path.relpath(p, ROOT)}")

    # Every page renders, under the prefix, and the gate on nutrition numbers holds.
    from .freeze import pages
    client = app.test_client()
    for url in pages(app):
        r = client.get(url)
        if r.status_code != 200:
            problems.append(f"{url} -> {r.status_code}")
        elif not s.site["claims_locked"] and b"g protein" in r.data.lower():
            problems.append(f"{url}: a protein number is rendered while claims_locked is false")

    for p in problems:
        print("FAIL", p)
    if problems:
        sys.exit(1)
    print(f"ok: {len(app.catalog.flavors)} flavors, {len(app.catalog.boxes)} boxes, {len(manifest)} image slots, "
          f"{len(pages(app))} pages render under {s.prefix or '/'}")


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m oats", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    x = sp.add_parser("serve", help="dev server")
    x.add_argument("--host", default="127.0.0.1")
    x.add_argument("--port", type=int, default=int(os.environ.get("OATS_PORT", "8090")))
    x.add_argument("--debug", action="store_true")
    x.set_defaults(f=cmd_serve)

    sp.add_parser("init-db", help="create the database").set_defaults(f=cmd_init_db)

    x = sp.add_parser("export-csv", help="dump a table as CSV to stdout")
    x.add_argument("table", choices=("signups", "preorders"))
    x.add_argument("--since", help="ISO date, e.g. 2026-10-01")
    x.set_defaults(f=cmd_export)

    sp.add_parser("stats", help="counts").set_defaults(f=cmd_stats)

    x = sp.add_parser("images", help="re-cut the mockups")
    x.add_argument("--only")
    x.set_defaults(f=cmd_images)

    sp.add_parser("check", help="content and render sanity").set_defaults(f=cmd_check)

    x = sp.add_parser("backup", help="copy the database, prune old copies")
    x.add_argument("--dir", default="/opt/oats/backup")
    x.add_argument("--keep-days", type=int, default=30)
    x.set_defaults(f=cmd_backup)

    x = sp.add_parser("freeze", help="write a static copy")
    x.add_argument("--out", default=os.path.join(ROOT, "dist"))
    x.add_argument("--api-base", help="absolute URL of /api when the static copy is hosted elsewhere")
    x.set_defaults(f=cmd_freeze)

    args = p.parse_args(argv)
    try:
        args.f(args)
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
