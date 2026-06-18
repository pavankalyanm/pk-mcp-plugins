from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"

PROVIDER_MAP: dict[str, dict[str, str | int]] = {
    "gmail.com":       {"imap_host": "imap.gmail.com",       "imap_port": 993, "smtp_host": "smtp.gmail.com",       "smtp_port": 587, "provider": "gmail"},
    "googlemail.com":  {"imap_host": "imap.gmail.com",       "imap_port": 993, "smtp_host": "smtp.gmail.com",       "smtp_port": 587, "provider": "gmail"},
    "outlook.com":     {"imap_host": "outlook.office365.com","imap_port": 993, "smtp_host": "smtp.office365.com",  "smtp_port": 587, "provider": "outlook"},
    "hotmail.com":     {"imap_host": "outlook.office365.com","imap_port": 993, "smtp_host": "smtp.office365.com",  "smtp_port": 587, "provider": "outlook"},
    "live.com":        {"imap_host": "outlook.office365.com","imap_port": 993, "smtp_host": "smtp.office365.com",  "smtp_port": 587, "provider": "outlook"},
    "msn.com":         {"imap_host": "outlook.office365.com","imap_port": 993, "smtp_host": "smtp.office365.com",  "smtp_port": 587, "provider": "outlook"},
    "yahoo.com":       {"imap_host": "imap.mail.yahoo.com",  "imap_port": 993, "smtp_host": "smtp.mail.yahoo.com", "smtp_port": 587, "provider": "yahoo"},
    "ymail.com":       {"imap_host": "imap.mail.yahoo.com",  "imap_port": 993, "smtp_host": "smtp.mail.yahoo.com", "smtp_port": 587, "provider": "yahoo"},
    "icloud.com":      {"imap_host": "imap.mail.me.com",     "imap_port": 993, "smtp_host": "smtp.mail.me.com",    "smtp_port": 587, "provider": "icloud"},
    "me.com":          {"imap_host": "imap.mail.me.com",     "imap_port": 993, "smtp_host": "smtp.mail.me.com",    "smtp_port": 587, "provider": "icloud"},
    "mac.com":         {"imap_host": "imap.mail.me.com",     "imap_port": 993, "smtp_host": "smtp.mail.me.com",    "smtp_port": 587, "provider": "icloud"},
    "aol.com":         {"imap_host": "imap.aol.com",         "imap_port": 993, "smtp_host": "smtp.aol.com",        "smtp_port": 587, "provider": "aol"},
    "zoho.com":        {"imap_host": "imap.zoho.com",        "imap_port": 993, "smtp_host": "smtp.zoho.com",       "smtp_port": 587, "provider": "zoho"},
    "fastmail.com":    {"imap_host": "imap.fastmail.com",    "imap_port": 993, "smtp_host": "smtp.fastmail.com",   "smtp_port": 587, "provider": "fastmail"},
    "protonmail.com":  {"imap_host": "127.0.0.1",            "imap_port": 1143,"smtp_host": "127.0.0.1",           "smtp_port": 1025,"provider": "protonmail"},
    "proton.me":       {"imap_host": "127.0.0.1",            "imap_port": 1143,"smtp_host": "127.0.0.1",           "smtp_port": 1025,"provider": "protonmail"},
}

GMAIL_DEFAULTS = {"imap_host": "imap.gmail.com", "imap_port": 993, "smtp_host": "smtp.gmail.com", "smtp_port": 587, "provider": "gmail"}


def detect_provider(email_address: str) -> dict[str, str | int]:
    domain = email_address.rsplit("@", 1)[-1].lower()
    if domain in PROVIDER_MAP:
        return dict(PROVIDER_MAP[domain])
    return {"imap_host": f"imap.{domain}", "imap_port": 993, "smtp_host": f"smtp.{domain}", "smtp_port": 587, "provider": domain}


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def _load_accounts_map() -> dict[str, dict]:
    if not ACCOUNTS_FILE.exists():
        return {}
    return json.loads(ACCOUNTS_FILE.read_text())


def _save_accounts_map(accounts: dict[str, dict]) -> None:
    _ensure_data_dir()
    ACCOUNTS_FILE.write_text(json.dumps(accounts, indent=2))


def add_account(
    alias: str,
    email: str,
    app_password: str,
    imap_host: str | None = None,
    imap_port: int | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
) -> str:
    _ensure_data_dir()
    accounts = _load_accounts_map()

    detected = detect_provider(email)
    entry = {
        "email": email,
        "app_password": app_password,
        "imap_host": imap_host or detected["imap_host"],
        "imap_port": imap_port or detected["imap_port"],
        "smtp_host": smtp_host or detected["smtp_host"],
        "smtp_port": smtp_port or detected["smtp_port"],
        "provider": detected["provider"],
    }
    accounts[alias] = entry
    _save_accounts_map(accounts)
    return f"Account '{alias}' added ({email}) via {entry['provider']}."


def remove_account(alias: str) -> str:
    accounts = _load_accounts_map()
    if alias not in accounts:
        return f"Account '{alias}' not found."
    del accounts[alias]
    _save_accounts_map(accounts)
    return f"Account '{alias}' removed."


def list_accounts() -> dict[str, dict[str, str]]:
    accounts = _load_accounts_map()
    return {
        alias: {"email": info.get("email", "unknown"), "provider": info.get("provider", "gmail")}
        for alias, info in accounts.items()
    }


def get_account(alias: str) -> dict:
    accounts = _load_accounts_map()
    if alias not in accounts:
        available = ", ".join(accounts.keys()) or "(none)"
        raise ValueError(f"Account '{alias}' not found. Available accounts: {available}")
    acct = accounts[alias]
    if "imap_host" not in acct:
        acct.update(GMAIL_DEFAULTS)
    return acct


def resolve_account(alias: str | None) -> str:
    accounts = _load_accounts_map()
    if not accounts:
        raise ValueError("No accounts configured. Use the email_add_account tool first.")
    if alias:
        if alias not in accounts:
            available = ", ".join(accounts.keys())
            raise ValueError(f"Account '{alias}' not found. Available: {available}")
        return alias
    if len(accounts) == 1:
        return next(iter(accounts))
    available = ", ".join(accounts.keys())
    raise ValueError(f"Multiple accounts configured. Specify one: {available}")
