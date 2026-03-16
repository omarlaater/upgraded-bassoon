"""Helpers for normalizing timestamp values returned by Bitbucket APIs."""

from datetime import datetime, timezone


def to_utc_iso(timestamp_value) -> str:
    """Convert a Bitbucket timestamp to ISO-8601 UTC when possible."""
    if timestamp_value in (None, "", 0, "0"):
        return ""

    try:
        numeric_value = int(timestamp_value)
    except (TypeError, ValueError):
        return ""

    # Bitbucket examples commonly use milliseconds, but some examples and
    # installations may surface second-based values. Normalize both.
    if abs(numeric_value) >= 1_000_000_000_000:
        numeric_value = numeric_value / 1000.0

    try:
        return (
            datetime.fromtimestamp(numeric_value, tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
    except (OverflowError, OSError, ValueError):
        return ""
