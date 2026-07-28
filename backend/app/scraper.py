"""Fetches a product page and pulls out the handful of fields ad copy needs:
title, description, price and a hero image. Uses Open Graph / Twitter Card
meta tags first — nearly every e-commerce platform (Shopify, WooCommerce,
Amazon, etc.) sets these for link-preview purposes, which makes them a far
more reliable generic signal than trying to guess a site's own CSS classes.
Falls back to <title>/<meta name="description"> when OG tags are missing."""

import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fastapi import HTTPException

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
PRICE_PATTERN = re.compile(r"[\$€£]\s?\d[\d.,]*|\d[\d.,]*\s?(?:kr|SEK|USD|EUR|GBP)\b", re.IGNORECASE)


@dataclass
class ProductInfo:
    url: str
    title: str
    description: str
    price: str | None
    image: str | None
    site_name: str | None


def _meta(soup: BeautifulSoup, *keys: str) -> str | None:
    for key in keys:
        tag = soup.find("meta", property=key) or soup.find("meta", attrs={"name": key})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return None


def _find_price(soup: BeautifulSoup) -> str | None:
    og_price = _meta(soup, "product:price:amount", "og:price:amount")
    og_currency = _meta(soup, "product:price:currency", "og:price:currency")
    if og_price:
        return f"{og_price} {og_currency}".strip() if og_currency else og_price

    itemprop_price = soup.find(attrs={"itemprop": "price"})
    if itemprop_price:
        value = itemprop_price.get("content") or itemprop_price.get_text(strip=True)
        if value:
            return value

    text_match = PRICE_PATTERN.search(soup.get_text(" ", strip=True)[:5000])
    return text_match.group(0) if text_match else None


def _raise_if_private_target(hostname: str) -> None:
    """Blocks SSRF into internal infrastructure. Without this, "paste a
    product URL" is an open invitation to make the backend fetch whatever a
    caller wants server-side — most dangerously the cloud metadata endpoint
    (169.254.169.254 / metadata.google.internal on GCP), which can hand back
    this service's own credentials to anyone who can point the scraper at
    it. Resolves DNS and rejects any private/loopback/link-local/reserved
    address rather than trying to blocklist hostnames by name."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise HTTPException(status_code=400, detail="Couldn't resolve that URL's host.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(
                status_code=400, detail="That URL points to a private/internal address, which isn't allowed."
            )


MAX_REDIRECTS = 5


def fetch_product_info(url: str) -> ProductInfo:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="That doesn't look like a valid product URL.")
    _raise_if_private_target(parsed.hostname)

    # Redirects are followed manually (rather than httpx's follow_redirects=True)
    # so every hop gets the same private-address check as the original URL —
    # a validated URL that 302s to the metadata endpoint would otherwise
    # sail straight through, a well-known SSRF bypass technique.
    current_url = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            response = httpx.get(
                current_url,
                headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
                follow_redirects=False,
                timeout=15.0,
            )
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    break
                next_url = urljoin(str(response.url), location)
                next_hostname = urlparse(next_url).hostname
                if next_hostname:
                    _raise_if_private_target(next_hostname)
                current_url = next_url
                continue
            response.raise_for_status()
            break
        else:
            raise HTTPException(status_code=422, detail="Too many redirects while fetching that URL.")
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=422, detail=f"Couldn't fetch that URL: {exc}") from exc

    soup = BeautifulSoup(response.text, "html.parser")

    title = _meta(soup, "og:title", "twitter:title")
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    title = title or url

    description = _meta(soup, "og:description", "twitter:description", "description") or ""

    return ProductInfo(
        url=url,
        title=title,
        description=description,
        price=_find_price(soup),
        image=_meta(soup, "og:image", "twitter:image"),
        site_name=_meta(soup, "og:site_name") or parsed.netloc,
    )
