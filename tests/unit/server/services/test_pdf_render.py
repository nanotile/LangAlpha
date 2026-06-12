"""Unit tests for the server-side PDF renderer's SSRF allowlist.

Exercises ``_is_request_allowed`` directly (a pure predicate) — the only part
of ``pdf_render`` that runs without Chromium. CI has no browser binary, so the
render path itself is covered by mocking in the route tests.
"""

from __future__ import annotations

from src.server.services.pdf_render import _is_request_allowed

_PREFIX = "http://127.0.0.1:8000/api/v1/wsfiles/ws-abc-0001/"

_CDN_HOSTS = [
    "cdnjs.cloudflare.com",
    "cdn.jsdelivr.net",
    "unpkg.com",
    "esm.sh",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
]


# --- Workspace serve prefix -----------------------------------------------


def test_workspace_prefix_allowed():
    assert _is_request_allowed(_PREFIX + "results/report.html", _PREFIX)
    assert _is_request_allowed(_PREFIX + "results/charts/x.png", _PREFIX)


def test_other_workspace_prefix_blocked():
    # A different workspace's serve prefix is not this render's prefix.
    other = "http://127.0.0.1:8000/api/v1/wsfiles/ws-other-9999/"
    assert not _is_request_allowed(other + "results/report.html", _PREFIX)


# --- CDN allowlist (https only) -------------------------------------------


def test_each_cdn_host_allowed_over_https():
    for host in _CDN_HOSTS:
        assert _is_request_allowed(f"https://{host}/lib/x.js", _PREFIX), host


def test_cdn_host_blocked_over_http():
    for host in _CDN_HOSTS:
        assert not _is_request_allowed(f"http://{host}/lib/x.js", _PREFIX), host


# --- SSRF targets blocked --------------------------------------------------


def test_cloud_metadata_endpoint_blocked():
    assert not _is_request_allowed("http://169.254.169.254/latest/meta-data/", _PREFIX)
    assert not _is_request_allowed("https://169.254.169.254/latest/meta-data/", _PREFIX)


def test_other_internal_hosts_blocked():
    assert not _is_request_allowed("http://127.0.0.1:8003/api/auth/keys", _PREFIX)
    assert not _is_request_allowed("http://localhost:6379/", _PREFIX)
    assert not _is_request_allowed("http://10.0.0.5/internal", _PREFIX)


def test_lookalike_domains_blocked():
    # Suffix/substring tricks must not satisfy the exact-host check.
    assert not _is_request_allowed(
        "https://evil-cdnjs.cloudflare.com.attacker.io/x.js", _PREFIX
    )
    assert not _is_request_allowed("https://unpkg.com.evil.io/x.js", _PREFIX)
    assert not _is_request_allowed("https://notunpkg.com/x.js", _PREFIX)
    assert not _is_request_allowed("https://cdnjs.cloudflare.com.evil.io/x.js", _PREFIX)
