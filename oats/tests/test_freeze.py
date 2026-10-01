"""The static export is complete and still prefixed."""
import os

from oats.freeze import freeze

from .conftest import PREFIX


def test_freeze_writes_everything(app, tmp_path):
    out = tmp_path / "dist"
    n = freeze(app, str(out), api_base="https://api.example.test/oats/api", log=lambda *a, **k: None)
    assert n >= 20
    root = out / PREFIX.strip("/")
    assert (root / "index.html").exists()
    assert (root / "flavors" / "strawberry-shortcake" / "index.html").exists()
    assert (root / "theme.css").exists()
    assert (root / "sitemap.xml").exists()
    assert (root / "static" / "css" / "base.css").exists()
    assert (out / "404.html").exists()
    html = (root / "index.html").read_text()
    assert '"apiBase":"https://api.example.test/oats/api"' in html
    assert f'href="{PREFIX}/static/css/base.css?v=' in html
    assert os.path.getsize(root / "static" / "img" / "manifest.json") > 100
