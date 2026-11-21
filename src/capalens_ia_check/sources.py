"""Read a document from a file or a URL (GET, through the careful client). Nothing is executed."""

from __future__ import annotations

from pathlib import Path

from .net import BudgetExceeded, HttpClient

MAX_FILE_BYTES = 10 * 1024 * 1024


def is_url(location: str) -> bool:
    return location.lower().startswith(("http://", "https://"))


def read(location: str, http: HttpClient | None) -> tuple[bytes | None, str | None]:
    """(bytes, problem). Exactly one of them is None."""
    if is_url(location):
        client = http or HttpClient()
        try:
            resp = client.request("GET", location, headers={"Accept": "application/json, application/yaml, */*"})
        except BudgetExceeded as exc:
            return None, str(exc)
        if resp.status is None:
            return None, resp.error or "no answer"
        if resp.status != 200:
            return None, f"HTTP {resp.status}" + (f" ({resp.error})" if resp.error else "")
        if resp.error:
            return None, resp.error
        return resp.body, None
    path = Path(location)
    if not path.is_file():
        return None, f"not a readable file: {location}"
    if path.stat().st_size > MAX_FILE_BYTES:
        return None, f"file larger than {MAX_FILE_BYTES} bytes"
    return path.read_bytes(), None
