import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from beauty_creator_agent.core.errors import ExternalServiceError


def validate_public_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL must use http or https and include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port)}
    except socket.gaierror as exc:
        raise ValueError("URL hostname cannot be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("URL must not resolve to a private or reserved address")
    return url


async def fetch_public_text(url: str, *, max_bytes: int = 1_000_000) -> str:
    safe_url = validate_public_url(url)
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
            async with client.stream("GET", safe_url) as response:
                response.raise_for_status()
                if response.is_redirect:
                    raise ExternalServiceError("redirects are disabled for URL safety")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ExternalServiceError("response exceeds maximum allowed size")
                    chunks.append(chunk)
        return b"".join(chunks).decode("utf-8", errors="replace")
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"safe URL fetch failed: {exc}") from exc
