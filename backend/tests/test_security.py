"""Security-focused unit tests for the URL validator (SSRF defence)."""
from unittest import mock

import pytest

from app.security import UnsafeURLError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/video",
        "file:///etc/passwd",
        "http://127.0.0.1/admin",
        "http://169.254.169.254/latest/",
        "http://10.0.0.5/internal",
        "http://192.168.1.10/router",
        "http://[::1]/x",
        "",
    ],
)
def test_rejects_unsafe_urls(url):
    with pytest.raises(UnsafeURLError):
        validate_url(url)


def test_accepts_public_https():
    fake = [(2, 1, 6, "", ("93.184.216.34", 0))]
    with mock.patch("app.security.socket.getaddrinfo", return_value=fake):
        result = validate_url("https://www.example.com/watch?v=abc")
    assert result.startswith("https://")
