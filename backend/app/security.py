"""Input validation & SSRF defence for submitted URLs.

The single most important server-side control: a user-supplied URL must never be
allowed to reach internal infrastructure or cloud metadata endpoints.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}

# Networks we must never fetch from (SSRF). Covers loopback, private RFC1918,
# link-local (incl. 169.254.169.254 cloud metadata), CGNAT, and unique-local v6.
_BLOCKED_NETS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class UnsafeURLError(ValueError):
    """Raised when a URL fails validation or SSRF checks."""


def _is_blocked_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return any(addr in net for net in _BLOCKED_NETS)


def validate_url(raw: str) -> str:
    """Return a cleaned URL or raise UnsafeURLError.

    Checks: non-empty, http/https scheme, has a hostname, and every resolved IP
    of that hostname is public (not private/loopback/link-local/metadata).
    """
    if not raw or len(raw) > 2048:
        raise UnsafeURLError("Please paste a valid video link.")

    url = raw.strip()
    parsed = urlparse(url)

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeURLError("Only http and https links are supported.")
    if not parsed.hostname:
        raise UnsafeURLError("That link is missing a website address.")

    # Resolve and verify every address (defends against DNS-rebinding to internal).
    try:
        infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:  # pragma: no cover - network dependent
        raise UnsafeURLError("That website address could not be found.") from exc

    for info in infos:
        ip = info[4][0]
        if _is_blocked_ip(ip):
            raise UnsafeURLError("That link points to a private or blocked address.")

    return url
