import socket

import httpx
import pytest

from app.scraper import fetch_product_info

SAMPLE_HTML = """
<html><head>
<title>Fallback Title</title>
<meta property="og:title" content="Wireless Noise-Cancelling Headphones">
<meta property="og:description" content="Immersive sound, 30-hour battery life.">
<meta property="og:image" content="https://example.com/headphones.jpg">
<meta property="og:site_name" content="ExampleShop">
<meta property="product:price:amount" content="199.00">
<meta property="product:price:currency" content="USD">
</head><body></body></html>
"""

FALLBACK_HTML = """
<html><head>
<title>Only A Title</title>
<meta name="description" content="A plain meta description, no OG tags.">
</head><body>Price: $49.99 today only</body></html>
"""


def _fake_get(html: str):
    def _get(url, headers=None, follow_redirects=True, timeout=None):
        return httpx.Response(200, text=html, request=httpx.Request("GET", url))

    return _get


def test_fetch_product_info_prefers_open_graph_tags(monkeypatch):
    monkeypatch.setattr(httpx, "get", _fake_get(SAMPLE_HTML))
    info = fetch_product_info("https://example.com/product/123")
    assert info.title == "Wireless Noise-Cancelling Headphones"
    assert info.description == "Immersive sound, 30-hour battery life."
    assert info.image == "https://example.com/headphones.jpg"
    assert info.site_name == "ExampleShop"
    assert info.price == "199.00 USD"


def test_fetch_product_info_falls_back_without_open_graph(monkeypatch):
    monkeypatch.setattr(httpx, "get", _fake_get(FALLBACK_HTML))
    info = fetch_product_info("https://example.com/plain")
    assert info.title == "Only A Title"
    assert info.description == "A plain meta description, no OG tags."
    assert info.image is None
    assert "49.99" in info.price


def test_fetch_product_info_rejects_invalid_url():
    with pytest.raises(Exception):
        fetch_product_info("not-a-url")


def test_fetch_product_info_raises_on_network_error(monkeypatch):
    def _raise(url, headers=None, follow_redirects=True, timeout=None):
        raise httpx.ConnectError("boom", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", _raise)
    with pytest.raises(Exception):
        fetch_product_info("https://example.com/unreachable")


def _fake_getaddrinfo(ip: str):
    def _resolve(hostname, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _resolve


def test_fetch_product_info_blocks_cloud_metadata_ip(monkeypatch):
    """169.254.169.254 is the GCP/AWS metadata endpoint — letting the
    scraper fetch it would leak this service's own cloud credentials to
    anyone who can submit a "product URL"."""
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("169.254.169.254"))
    with pytest.raises(Exception):
        fetch_product_info("http://metadata.google.internal/computeMetadata/v1/")


def test_fetch_product_info_blocks_localhost(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("127.0.0.1"))
    with pytest.raises(Exception):
        fetch_product_info("http://localhost:8000/admin")


def test_fetch_product_info_blocks_private_network(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("10.0.0.5"))
    with pytest.raises(Exception):
        fetch_product_info("http://internal.example.com/")


def test_fetch_product_info_blocks_redirect_to_private_address(monkeypatch):
    """A URL that resolves publicly but 302s to an internal address must be
    blocked too — otherwise the up-front hostname check is a no-op bypassed
    by anything the attacker can make redirect."""
    monkeypatch.setattr(socket, "getaddrinfo", _fake_getaddrinfo("93.184.216.34"))  # example.com's real public IP

    def _get(url, headers=None, follow_redirects=False, timeout=None):
        if url == "https://example.com/redirect-me":
            request = httpx.Request("GET", url)
            return httpx.Response(302, headers={"Location": "http://169.254.169.254/"}, request=request)
        raise AssertionError(f"should never actually fetch the redirect target: {url}")

    monkeypatch.setattr(httpx, "get", _get)
    with pytest.raises(Exception):
        fetch_product_info("https://example.com/redirect-me")
