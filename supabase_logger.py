"""
Supabase dual-write logger for Streamlit Cloud persistence.
Falls back silently if credentials not configured (local dev).

Tables:
  gatefix_log  — one row per submission
  feedback_log — one row per feedback
"""

import json
import requests

_BASE_URL: str | None = None
_KEY: str | None = None


def _config() -> tuple[str, str]:
    global _BASE_URL, _KEY
    if _BASE_URL is not None:
        return _BASE_URL, _KEY  # type: ignore[return-value]
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL", "")
        key = st.secrets.get("SUPABASE_KEY", "")
        _BASE_URL = str(url).rstrip("/") if url else ""
        _KEY = str(key) if key else ""
        return _BASE_URL, _KEY
    except Exception:
        _BASE_URL = ""
        _KEY = ""
        return "", ""


def _headers(return_repr: str = "minimal") -> dict:
    _, key = _config()
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": f"return={return_repr}",
    }


def append_record(tab_name: str, record: dict) -> None:
    """Insert one record into the given Supabase table. Silent no-op on error."""
    try:
        url, key = _config()
        if not url or not key:
            return
        row: dict = {}
        for k, v in record.items():
            if isinstance(v, (list, dict)):
                row[k] = json.dumps(v, ensure_ascii=False)
            else:
                row[k] = v
        requests.post(
            f"{url}/rest/v1/{tab_name}",
            headers=_headers("minimal"),
            json=row,
            timeout=5,
        )
    except Exception:
        pass


def read_records(tab_name: str) -> list[dict]:
    """Read all records from the given table. Returns [] on error."""
    try:
        url, key = _config()
        if not url or not key:
            return []
        h = _headers("representation")
        h["Prefer"] = ""
        resp = requests.get(
            f"{url}/rest/v1/{tab_name}?select=*&order=timestamp.asc&limit=10000",
            headers=h,
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        rows = resp.json()
        result = []
        for row in rows:
            clean: dict = {}
            for k, v in row.items():
                if v is None or v == "None":
                    clean[k] = None
                elif v == "True":
                    clean[k] = True
                elif v == "False":
                    clean[k] = False
                elif v == "":
                    clean[k] = None
                elif isinstance(v, str):
                    # Try JSON arrays/objects stored as text
                    if v.startswith("[") or v.startswith("{"):
                        try:
                            clean[k] = json.loads(v)
                            continue
                        except Exception:
                            pass
                    try:
                        clean[k] = int(v)
                    except (ValueError, TypeError):
                        try:
                            clean[k] = float(v)
                        except (ValueError, TypeError):
                            clean[k] = v
                else:
                    clean[k] = v
            result.append(clean)
        return result
    except Exception:
        return []


def supabase_configured() -> bool:
    """Return True if Supabase credentials are present in secrets."""
    url, key = _config()
    return bool(url and key)


# Alias for backwards-compat with any code that called sheets_configured()
sheets_configured = supabase_configured
