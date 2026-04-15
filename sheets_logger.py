"""
Google Sheets dual-write logger for Streamlit Cloud persistence.
Falls back silently if credentials not configured (local dev).

Sheet structure:
  Tab "gatefix_log"  — one row per submission
  Tab "feedback_log" — one row per feedback
"""

import json

_SHEETS_AVAILABLE = None   # None = unchecked, True/False after first call

def _client():
    """Return (gspread client, sheet_id) or (None, None) if not configured."""
    global _SHEETS_AVAILABLE
    try:
        import gspread
        import streamlit as st
        from google.oauth2.service_account import Credentials

        info = st.secrets.get("gcp_service_account")
        sheet_id = st.secrets.get("GSHEET_ID")
        if not info or not sheet_id:
            _SHEETS_AVAILABLE = False
            return None, None

        creds = Credentials.from_service_account_info(
            dict(info),
            scopes=[
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        client = gspread.authorize(creds)
        _SHEETS_AVAILABLE = True
        return client, sheet_id
    except Exception:
        _SHEETS_AVAILABLE = False
        return None, None


def _get_or_create_tab(spreadsheet, tab_name: str, headers: list):
    """Return worksheet, creating it with header row if missing."""
    try:
        ws = spreadsheet.worksheet(tab_name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
        ws.append_row(headers, value_input_option="RAW")
    # If sheet exists but is empty, add headers
    if ws.row_count == 0 or not ws.row_values(1):
        ws.append_row(headers, value_input_option="RAW")
    return ws


def append_record(tab_name: str, record: dict):
    """Append one record to the given sheet tab. Silent no-op on any error."""
    try:
        client, sheet_id = _client()
        if client is None:
            return
        ss = client.open_by_key(sheet_id)
        headers = list(record.keys())
        ws = _get_or_create_tab(ss, tab_name, headers)
        # Align values to existing headers (in case schema evolved)
        existing_headers = ws.row_values(1)
        if not existing_headers:
            ws.append_row(headers, value_input_option="RAW")
            existing_headers = headers
        row = [str(record.get(h, "")) for h in existing_headers]
        ws.append_row(row, value_input_option="RAW")
    except Exception:
        pass  # never crash the app


def read_records(tab_name: str) -> list[dict]:
    """Read all records from the given sheet tab. Returns [] on any error."""
    try:
        client, sheet_id = _client()
        if client is None:
            return []
        ss = client.open_by_key(sheet_id)
        ws = ss.worksheet(tab_name)
        rows = ws.get_all_records()
        # Coerce types: "True"/"False" → bool, numeric strings → appropriate type
        result = []
        for row in rows:
            clean = {}
            for k, v in row.items():
                if v == "True":   clean[k] = True
                elif v == "False": clean[k] = False
                elif v == "None" or v == "": clean[k] = None
                else:
                    try:
                        clean[k] = int(v)
                    except (ValueError, TypeError):
                        try:
                            clean[k] = float(v)
                        except (ValueError, TypeError):
                            clean[k] = v
            result.append(clean)
        return result
    except Exception:
        return []


def sheets_configured() -> bool:
    """Return True if Google Sheets credentials are present in secrets."""
    _, sheet_id = _client()
    return sheet_id is not None
