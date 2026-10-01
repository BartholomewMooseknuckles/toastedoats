import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ORIGIN = "https://example.test"
PREFIX = "/oats"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("OATS_PREFIX", PREFIX)
    monkeypatch.setenv("OATS_PUBLIC_ORIGIN", ORIGIN)
    monkeypatch.setenv("OATS_DB", str(tmp_path / "test.db"))
    from oats import api, config
    from oats.app import create_app
    from oats.guard import Bucket
    # The limiter is a module global, so every test starts fresh - and roomy, except the one
    # test that is about the limiter and installs its own.
    api.bucket = Bucket(burst=100, every=1)
    application = create_app(config.load())
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def same_site():
    """Headers a browser on our own site sends with a fetch()."""
    return {"Sec-Fetch-Site": "same-origin", "Origin": ORIGIN}
