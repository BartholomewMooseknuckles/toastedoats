"""oats - the Toasted Oats marketing + pre-order site, served at /oats on 2birds1joint.org.

A small Flask app: Jinja renders every page from content/*.json, two JSON endpoints take
waitlist signups and pre-orders into SQLite, and `python -m oats freeze` can write the whole
thing out as static files if it ever needs to live on a static host instead.
"""
