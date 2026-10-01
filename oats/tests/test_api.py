"""The three endpoints: what they accept, what they refuse, what they store."""
import json

from oats import db

from .conftest import PREFIX

SIGNUP = PREFIX + "/api/signup"
PREORDER = PREFIX + "/api/preorder"
MESSAGE = PREFIX + "/api/message"


def rows(app, table):
    with app.app_context():
        c = db.connect(app.config["OATS_DB"])
        try:
            return [dict(r) for r in c.execute(f"SELECT * FROM {table}")]
        finally:
            c.close()


def test_signup_ok_then_duplicate_counts(client, app, same_site):
    r = client.post(SIGNUP, json={"email": "Someone@Example.com", "source": "hero"}, headers=same_site)
    assert r.status_code == 200 and r.get_json() == {"ok": True}
    r = client.post(SIGNUP, json={"email": "someone@example.com"}, headers=same_site)
    assert r.status_code == 200
    got = rows(app, "signups")
    assert len(got) == 1 and got[0]["email"] == "someone@example.com" and got[0]["hits"] == 2
    assert got[0]["kind"] == "waitlist" and got[0]["source"] == "hero"


def test_signup_honeypot_is_a_silent_success(client, app, same_site):
    r = client.post(SIGNUP, json={"email": "bot@example.com", "website": "http://spam"}, headers=same_site)
    assert r.status_code == 200 and r.get_json()["ok"] is True
    assert rows(app, "signups") == []
    assert rows(app, "events")[0]["kind"] == "honeypot"


def test_signup_bad_email(client, same_site):
    r = client.post(SIGNUP, json={"email": "nope"}, headers=same_site)
    assert r.status_code == 400 and r.get_json()["error"] == "email"


def test_signup_form_post_redirects_back(client, app):
    r = client.post(SIGNUP, data={"email": "form@example.com", "kind": "newsletter", "next": PREFIX + "/our-story"},
                    headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 303
    assert r.headers["Location"] == PREFIX + "/our-story?ok=1#signup"
    assert rows(app, "signups")[0]["kind"] == "newsletter"
    # a bad email on a form post comes back with ?err=
    r = client.post(SIGNUP, data={"email": "x", "next": PREFIX + "/"}, headers={"Sec-Fetch-Site": "same-origin"})
    assert r.status_code == 303 and "err=email" in r.headers["Location"]
    # and never off-site
    r = client.post(SIGNUP, data={"email": "a@b.co", "next": "https://evil.example/"}, headers={"Sec-Fetch-Site": "same-origin"})
    assert r.headers["Location"].startswith(PREFIX + "/")


def test_cross_site_is_refused(client):
    r = client.post(SIGNUP, json={"email": "a@b.co"}, headers={"Sec-Fetch-Site": "cross-site", "Origin": "https://evil.example"})
    assert r.status_code == 403
    r = client.post(SIGNUP, json={"email": "a@b.co"})            # no browser headers at all
    assert r.status_code == 403
    r = client.post(SIGNUP, json={"email": "a@b.co"}, headers={"Origin": "https://example.test"})
    assert r.status_code == 200                                   # a bare matching Origin is enough


def test_preorder_requires_json(client, same_site):
    r = client.post(PREORDER, data={"email": "a@b.co"}, headers=same_site)
    assert r.status_code == 415


def test_preorder_stores_server_prices(client, app, same_site):
    body = {
        "email": "box@example.com", "name": "Sam", "zip": "90210",
        "lines": [
            {"sku": "starter-7", "qty": 1, "unit_cents": 1},                              # client price is ignored
            {"sku": "single-7", "flavor": "blueberry-cobbler", "qty": 2, "subscribe": True, "cadence": "4w"},
            {"sku": "byo-14", "qty": 1, "picks": {"vanilla-crunch": 7, "birthday-cake": 7}},
        ],
        "cadence": "4w",
    }
    r = client.post(PREORDER, json=body, headers=same_site)
    assert r.status_code == 201, r.get_json()
    data = r.get_json()
    assert data["ref"].startswith("TO-")
    assert data["subtotal_cents"] == 2900 + 2 * 2465 + 5400
    assert data["shipping_cents"] == 0
    stored = rows(app, "preorders")
    assert len(stored) == 1 and stored[0]["subscribe"] == 1 and stored[0]["cadence"] == "4w"
    picks = json.loads(stored[0]["picks"])
    assert picks[2]["picks"] == {"vanilla-crunch": 7, "birthday-cake": 7}
    # the same cart again within minutes returns the same reference, not a second row
    r2 = client.post(PREORDER, json=body, headers=same_site)
    assert r2.get_json()["ref"] == data["ref"]
    assert len(rows(app, "preorders")) == 1


def test_preorder_shipping_below_threshold(client, same_site):
    r = client.post(PREORDER, json={"email": "a@b.co", "lines": [{"sku": "starter-7", "qty": 1}]}, headers=same_site)
    assert r.status_code == 201 and r.get_json()["shipping_cents"] == 695


def test_preorder_rejects_bad_carts(client, same_site):
    bad = [
        [{"sku": "nope", "qty": 1}],
        [{"sku": "starter-7", "qty": 0}],
        [{"sku": "starter-7", "qty": 99}],
        [{"sku": "single-7", "qty": 1}],                                   # no flavor
        [{"sku": "byo-14", "qty": 1, "picks": {"vanilla-crunch": 13}}],    # wrong sum
        [{"sku": "byo-14", "qty": 1, "picks": {"made-up": 14}}],
        [],
    ]
    for lines in bad:
        r = client.post(PREORDER, json={"email": "a@b.co", "lines": lines}, headers=same_site)
        assert r.status_code == 400, lines
        assert r.get_json()["error"] == "cart"


def test_rate_limit(client, same_site):
    from oats import api
    from oats.guard import Bucket
    api.bucket = Bucket(burst=2, every=60)
    ok = [client.post(SIGNUP, json={"email": f"u{i}@example.com"}, headers=same_site).status_code for i in range(3)]
    assert ok == [200, 200, 429]


def test_too_large_body(client, same_site):
    r = client.post(PREORDER, data="x" * 9000, headers={**same_site, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_message(client, app, same_site):
    r = client.post(MESSAGE, json={"email": "hi@example.com", "name": "Jo", "message": "Make a banana one."}, headers=same_site)
    assert r.status_code == 200
    r = client.post(MESSAGE, json={"email": "hi@example.com", "message": "And a mint one."}, headers=same_site)
    got = rows(app, "signups")
    assert len(got) == 1 and got[0]["kind"] == "contact" and "banana" in got[0]["message"] and "mint" in got[0]["message"]
    r = client.post(MESSAGE, json={"email": "hi@example.com", "message": "x"}, headers=same_site)
    assert r.status_code == 400


def test_export_csv_and_stats(client, app, same_site, capsys):
    client.post(SIGNUP, json={"email": "csv@example.com"}, headers=same_site)
    import io
    from oats import db as dbm
    c = dbm.connect(app.config["OATS_DB"])
    out = io.StringIO()
    n = dbm.export_csv(c, "signups", out=out)
    assert n == 1 and "csv@example.com" in out.getvalue()
    s = dbm.stats(c)
    assert s["signups"] == 1 and s["preorders"] == 0
