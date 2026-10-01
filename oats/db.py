"""db.py - SQLite for signups and pre-orders.

Same shape as the rest of the repo: one file, WAL, CREATE IF NOT EXISTS run on every open,
UTC ISO-8601 text timestamps, a connection per request on flask.g.

What is deliberately NOT stored: IP addresses, user agents, anything about the visitor
beyond what they typed. The `events` table only counts things (honeypot hits, rate limits)
so abuse can be noticed without keeping a log of people.
"""
import csv
import datetime as dt
import os
import sqlite3
import sys

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS signups (
    id         INTEGER PRIMARY KEY,
    email      TEXT NOT NULL,
    kind       TEXT NOT NULL DEFAULT 'waitlist',   -- waitlist | newsletter | contact
    source     TEXT,                               -- page or form the signup came from
    flavor     TEXT,                               -- flavor they were looking at, if any
    name       TEXT,
    message    TEXT,
    hits       INTEGER NOT NULL DEFAULT 1,         -- how many times this address signed up
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE (email, kind)
);
CREATE TABLE IF NOT EXISTS preorders (
    id             INTEGER PRIMARY KEY,
    ref            TEXT NOT NULL UNIQUE,            -- TO-XXXXXXXX, shown to the customer
    email          TEXT NOT NULL,
    name           TEXT,
    zip            TEXT,
    picks          TEXT NOT NULL,                   -- JSON: the normalised lines
    subtotal_cents INTEGER NOT NULL,
    shipping_cents INTEGER NOT NULL,
    subscribe      INTEGER NOT NULL DEFAULT 0,
    cadence        TEXT,
    notes          TEXT,
    picks_hash     TEXT NOT NULL,                   -- double-submit guard
    status         TEXT NOT NULL DEFAULT 'new',     -- new | invoiced | paid | cancelled
    source         TEXT,
    created_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS preorders_email ON preorders (email);
CREATE INDEX IF NOT EXISTS preorders_created ON preorders (created_at);
CREATE TABLE IF NOT EXISTS events (
    day  TEXT NOT NULL,
    kind TEXT NOT NULL,
    n    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, kind)
);
"""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def connect(path):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(path, timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.executescript(SCHEMA)
    return c


def db():
    if "db" not in g:
        g.db = connect(current_app.config["OATS_DB"])
    return g.db


def close(_=None):
    c = g.pop("db", None)
    if c is not None:
        c.close()


def bump(conn, kind):
    """Count an event for today. Never raises - counting must not break a request."""
    try:
        conn.execute("INSERT INTO events (day, kind, n) VALUES (?, ?, 1) "
                     "ON CONFLICT(day, kind) DO UPDATE SET n = n + 1",
                     (now()[:10], kind))
        conn.commit()
    except sqlite3.Error:
        pass


def upsert_signup(conn, email, kind, source=None, flavor=None, name=None, message=None):
    """Insert, or on a repeat count it. For contact messages, keep every message."""
    ts = now()
    conn.execute(
        """INSERT INTO signups (email, kind, source, flavor, name, message, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(email, kind) DO UPDATE SET
             hits = hits + 1,
             updated_at = excluded.updated_at,
             source = COALESCE(excluded.source, source),
             flavor = COALESCE(excluded.flavor, flavor),
             name = COALESCE(excluded.name, name),
             message = CASE WHEN excluded.message IS NULL THEN message
                            WHEN message IS NULL THEN excluded.message
                            ELSE message || char(10) || '---' || char(10) || excluded.message END""",
        (email, kind, source, flavor, name, message, ts, ts))
    conn.commit()


def recent_preorder(conn, email, picks_hash, minutes=10):
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutes)).isoformat(timespec="seconds").replace("+00:00", "Z")
    row = conn.execute("SELECT ref FROM preorders WHERE email = ? AND picks_hash = ? AND created_at >= ? "
                       "ORDER BY id DESC LIMIT 1", (email, picks_hash, cutoff)).fetchone()
    return row["ref"] if row else None


def insert_preorder(conn, ref, email, name, zip_code, picks_json, subtotal, shipping, subscribe,
                    cadence, notes, picks_hash, source):
    conn.execute(
        """INSERT INTO preorders (ref, email, name, zip, picks, subtotal_cents, shipping_cents,
                                  subscribe, cadence, notes, picks_hash, source, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ref, email, name, zip_code, picks_json, subtotal, shipping, int(subscribe), cadence, notes,
         picks_hash, source, now()))
    conn.commit()


# ------------------------------------------------------------------------- CLI helpers
def export_csv(conn, table, since=None, out=sys.stdout):
    if table not in ("signups", "preorders"):
        raise SystemExit("table must be signups or preorders")
    where, args = "", ()
    if since:
        where, args = " WHERE created_at >= ?", (since,)
    rows = conn.execute(f"SELECT * FROM {table}{where} ORDER BY id", args).fetchall()
    if not rows:
        return 0
    w = csv.writer(out)
    w.writerow(rows[0].keys())
    for r in rows:
        w.writerow(list(r))
    return len(rows)


def stats(conn):
    out = {}
    for table in ("signups", "preorders"):
        out[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    out["signups_by_kind"] = {r["kind"]: r["n"] for r in conn.execute(
        "SELECT kind, COUNT(*) AS n FROM signups GROUP BY kind")}
    out["preorder_value_cents"] = conn.execute(
        "SELECT COALESCE(SUM(subtotal_cents), 0) FROM preorders WHERE status != 'cancelled'").fetchone()[0]
    out["events_last_7_days"] = {r["kind"]: r["n"] for r in conn.execute(
        "SELECT kind, SUM(n) AS n FROM events WHERE day >= date('now', '-7 days') GROUP BY kind")}
    return out
