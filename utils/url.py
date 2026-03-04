from urllib.parse import urlparse, urlunparse


def normalize_server_url(base_url: str) -> str:
    """Normalize user URL input into stable `scheme://host[/path]` format."""

    raw = (base_url or "").strip()

    if not raw:
        raise ValueError("Server URL is empty.")

    if "://" not in raw:
        raw = f"https://{raw}"

    parsed = urlparse(raw)

    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid server URL: {base_url!r}")

    path = parsed.path.rstrip("/")

    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))
