from __future__ import annotations

import email
import email.utils
import imaplib
import json
import logging
import smtplib
import sys
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mcp.server.fastmcp import FastMCP

from accounts import (
    add_account,
    remove_account,
    list_accounts,
    get_account,
    resolve_account,
    detect_provider,
    PROVIDER_MAP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

mcp = FastMCP("mails-bridge")


# ── IMAP/SMTP helpers ───────────────────────────────────────────────

def _imap_connect(alias: str) -> imaplib.IMAP4_SSL:
    acct = get_account(alias)
    conn = imaplib.IMAP4_SSL(acct["imap_host"], acct["imap_port"])
    conn.login(acct["email"], acct["app_password"])
    return conn


def _smtp_send(alias: str, msg: MIMEMultipart | MIMEText, recipients: list[str]) -> None:
    acct = get_account(alias)
    with smtplib.SMTP(acct["smtp_host"], acct["smtp_port"]) as server:
        server.starttls()
        server.login(acct["email"], acct["app_password"])
        server.sendmail(acct["email"], recipients, msg.as_string())


def _drafts_folder(alias: str) -> str:
    acct = get_account(alias)
    if acct.get("provider") == "gmail":
        return '"[Gmail]/Drafts"'
    return "Drafts"


def _all_mail_folder(alias: str) -> str:
    acct = get_account(alias)
    if acct.get("provider") == "gmail":
        return '"[Gmail]/All Mail"'
    return "INBOX"


def _decode_header_value(raw: str | None) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for data, charset in parts:
        if isinstance(data, bytes):
            decoded.append(data.decode(charset or "utf-8", errors="replace"))
        else:
            decoded.append(data)
    return "".join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/html" and "attachment" not in disp:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def _parse_message(msg: email.message.Message, uid: str) -> dict:
    return {
        "uid": uid,
        "from": _decode_header_value(msg.get("From")),
        "to": _decode_header_value(msg.get("To")),
        "cc": _decode_header_value(msg.get("Cc", "")),
        "date": _decode_header_value(msg.get("Date")),
        "subject": _decode_header_value(msg.get("Subject")),
    }


def _parse_message_full(msg: email.message.Message, uid: str) -> dict:
    result = _parse_message(msg, uid)
    body = _extract_body(msg)
    result["body"] = body[:5000]
    return result


# ── Account management ──────────────────────────────────────────────

@mcp.tool()
def email_add_account(
    alias: str,
    email_address: str,
    app_password: str,
    imap_host: str | None = None,
    imap_port: int | None = None,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
) -> str:
    """Add an email account using an app password or IMAP/SMTP password.

    Automatically detects IMAP/SMTP servers for Gmail, Outlook, Yahoo, iCloud, AOL,
    Zoho, Fastmail, and ProtonMail. For other providers, pass custom imap_host/smtp_host
    or let it try imap.{domain}/smtp.{domain}.

    Args:
        alias: A short name for this account (e.g. "personal", "work").
        email_address: The full email address (e.g. "user@gmail.com", "user@outlook.com").
        app_password: The app password or account password for IMAP/SMTP access.
        imap_host: Custom IMAP server hostname (auto-detected if omitted).
        imap_port: Custom IMAP port (default 993).
        smtp_host: Custom SMTP server hostname (auto-detected if omitted).
        smtp_port: Custom SMTP port (default 587).
    """
    clean_pw = app_password.replace(" ", "")

    detected = detect_provider(email_address)
    final_imap_host = imap_host or detected["imap_host"]
    final_imap_port = imap_port or detected["imap_port"]

    try:
        conn = imaplib.IMAP4_SSL(final_imap_host, final_imap_port)
        conn.login(email_address, clean_pw)
        conn.logout()
    except imaplib.IMAP4.error as e:
        return f"Login failed for {final_imap_host}:{final_imap_port}: {e}. Check the email and password."
    except Exception as e:
        return f"Connection failed to {final_imap_host}:{final_imap_port}: {e}. Check the server address."

    result = add_account(alias, email_address, clean_pw, imap_host, imap_port, smtp_host, smtp_port)
    return result


@mcp.tool()
def email_remove_account(alias: str) -> str:
    """Remove a previously added email account.

    Args:
        alias: The account alias to remove.
    """
    return remove_account(alias)


@mcp.tool()
def email_list_accounts() -> str:
    """List all configured email accounts, their addresses, and providers."""
    accounts = list_accounts()
    if not accounts:
        return "No accounts configured. Use email_add_account to add one."
    lines = [f"  {alias}: {info['email']} ({info['provider']})" for alias, info in accounts.items()]
    return "Configured accounts:\n" + "\n".join(lines)


@mcp.tool()
def email_supported_providers() -> str:
    """List all auto-detected email providers and their IMAP/SMTP servers."""
    seen = {}
    for domain, info in PROVIDER_MAP.items():
        p = info["provider"]
        if p not in seen:
            seen[p] = {"domains": [], "imap": f"{info['imap_host']}:{info['imap_port']}", "smtp": f"{info['smtp_host']}:{info['smtp_port']}"}
        seen[p]["domains"].append(domain)

    lines = []
    for provider, info in seen.items():
        domains = ", ".join(info["domains"])
        lines.append(f"  {provider}: {domains}\n    IMAP: {info['imap']}  SMTP: {info['smtp']}")
    lines.append("\n  For unlisted providers, pass custom imap_host/smtp_host or let auto-detect try imap.{domain}.")
    return "Supported providers:\n" + "\n".join(lines)


# ── Email reading ────────────────────────────────────────────────────

@mcp.tool()
def email_search(
    query: str,
    account: str | None = None,
    max_results: int = 10,
    folder: str = "INBOX",
) -> str:
    """Search emails using IMAP search.

    Args:
        query: IMAP search query. Examples:
            - "ALL" (all messages)
            - "UNSEEN" (unread)
            - "FROM \\"sender@example.com\\""
            - "SUBJECT \\"meeting\\""
            - "SINCE 01-Jun-2025"
            - "UNSEEN FROM \\"boss@co.com\\""
            - "OR FROM \\"alice@co.com\\" FROM \\"bob@co.com\\""
            - "TEXT \\"project update\\""
        account: Account alias. Optional if only one account is configured.
        max_results: Max messages to return (default 10).
        folder: IMAP folder to search (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(folder, readonly=True)
        _, data = conn.search(None, query)
        uids = data[0].split()
        if not uids:
            return json.dumps({"account": alias, "count": 0, "messages": []}, indent=2)

        uids = uids[-max_results:]
        uids.reverse()

        messages = []
        for uid in uids:
            _, msg_data = conn.fetch(uid, "(RFC822.HEADER)")
            if msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            parsed = _parse_message(msg, uid.decode())
            _, body_data = conn.fetch(uid, "(BODY.PEEK[TEXT]<0.300>)")
            if body_data[0] is not None:
                snippet_raw = body_data[0][1]
                snippet = snippet_raw.decode("utf-8", errors="replace")[:200]
                parsed["snippet"] = snippet.strip()
            messages.append(parsed)

        return json.dumps({"account": alias, "folder": folder, "count": len(messages), "messages": messages}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_read_message(uid: str, account: str | None = None, folder: str = "INBOX") -> str:
    """Read a single email message by UID.

    Args:
        uid: The message UID (from email_search results).
        account: Account alias. Optional if only one account is configured.
        folder: IMAP folder (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(folder, readonly=True)
        _, msg_data = conn.fetch(uid.encode(), "(RFC822)")
        if msg_data[0] is None:
            return json.dumps({"error": f"Message UID {uid} not found in {folder}"})

        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        parsed = _parse_message_full(msg, uid)
        parsed["account"] = alias
        parsed["folder"] = folder
        return json.dumps(parsed, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_read_thread(subject: str, account: str | None = None, max_messages: int = 10) -> str:
    """Read all messages in a thread by subject line.

    Searches All Mail (Gmail) or INBOX (other providers) for messages with the given subject.

    Args:
        subject: The subject line to search for (exact or partial match).
        account: Account alias. Optional if only one account is configured.
        max_messages: Max messages to return (default 10).
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)
    folder = _all_mail_folder(alias)

    try:
        conn.select(folder, readonly=True)
        _, data = conn.search(None, f'SUBJECT "{subject}"')
        uids = data[0].split()
        if not uids:
            return json.dumps({"account": alias, "subject": subject, "count": 0, "messages": []}, indent=2)

        uids = uids[-max_messages:]
        messages = []
        for uid in uids:
            _, msg_data = conn.fetch(uid, "(RFC822)")
            if msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            parsed = _parse_message_full(msg, uid.decode())
            messages.append(parsed)

        return json.dumps({"account": alias, "subject": subject, "count": len(messages), "messages": messages}, indent=2)
    finally:
        conn.logout()


# ── Composing / sending ──────────────────────────────────────────────

@mcp.tool()
def email_create_draft(
    to: str,
    subject: str,
    body: str,
    account: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    html_body: str | None = None,
) -> str:
    """Create a draft email (saved to Drafts folder via IMAP).

    Args:
        to: Recipient email address(es), comma-separated.
        subject: Email subject line.
        body: Plain-text body.
        account: Account alias. Optional if only one account is configured.
        cc: CC recipients, comma-separated.
        bcc: BCC recipients, comma-separated.
        html_body: Optional HTML body (plain text body becomes fallback).
    """
    alias = resolve_account(account)
    acct = get_account(alias)
    conn = _imap_connect(alias)
    drafts = _drafts_folder(alias)

    try:
        msg = _build_message(acct["email"], to, subject, body, cc, bcc, html_body)
        conn.select(drafts)
        conn.append(drafts, "\\Draft", None, msg.as_bytes())
        return json.dumps({"account": alias, "status": "draft created", "to": to, "subject": subject}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_send(
    to: str,
    subject: str,
    body: str,
    account: str | None = None,
    cc: str | None = None,
    bcc: str | None = None,
    html_body: str | None = None,
) -> str:
    """Send an email immediately via SMTP.

    Args:
        to: Recipient email address(es), comma-separated.
        subject: Email subject line.
        body: Plain-text body.
        account: Account alias. Optional if only one account is configured.
        cc: CC recipients, comma-separated.
        bcc: BCC recipients, comma-separated.
        html_body: Optional HTML body (plain text body becomes fallback).
    """
    alias = resolve_account(account)
    acct = get_account(alias)

    msg = _build_message(acct["email"], to, subject, body, cc, bcc, html_body)

    all_recipients = [addr.strip() for addr in to.split(",")]
    if cc:
        all_recipients.extend(addr.strip() for addr in cc.split(","))
    if bcc:
        all_recipients.extend(addr.strip() for addr in bcc.split(","))

    _smtp_send(alias, msg, all_recipients)

    return json.dumps({"account": alias, "status": "sent", "to": to, "subject": subject}, indent=2)


@mcp.tool()
def email_list_drafts(account: str | None = None, max_results: int = 10) -> str:
    """List draft emails.

    Args:
        account: Account alias. Optional if only one account is configured.
        max_results: Max drafts to return (default 10).
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)
    drafts = _drafts_folder(alias)

    try:
        conn.select(drafts, readonly=True)
        _, data = conn.search(None, "ALL")
        uids = data[0].split()
        if not uids:
            return json.dumps({"account": alias, "drafts": []}, indent=2)

        uids = uids[-max_results:]
        uids.reverse()

        draft_list = []
        for uid in uids:
            _, msg_data = conn.fetch(uid, "(RFC822.HEADER)")
            if msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            draft_list.append(_parse_message(msg, uid.decode()))

        return json.dumps({"account": alias, "drafts": draft_list}, indent=2)
    finally:
        conn.logout()


# ── Folders ──────────────────────────────────────────────────────────

@mcp.tool()
def email_list_folders(account: str | None = None) -> str:
    """List all IMAP folders (labels) in the account.

    Args:
        account: Account alias. Optional if only one account is configured.
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        _, folders = conn.list()
        folder_names = []
        for f in folders:
            decoded = f.decode("utf-8", errors="replace")
            parts = decoded.split(' "/" ')
            if len(parts) == 2:
                folder_names.append(parts[1].strip('"'))
            else:
                folder_names.append(decoded)

        return json.dumps({"account": alias, "folders": folder_names}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_move_message(
    uid: str,
    destination: str,
    account: str | None = None,
    source: str = "INBOX",
) -> str:
    """Move a message to a different folder/label.

    Args:
        uid: The message UID.
        destination: Target folder (e.g. "Trash", "Spam", or a label/folder name).
        account: Account alias. Optional if only one account is configured.
        source: Source folder (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(source)
        conn.copy(uid.encode(), destination)
        conn.store(uid.encode(), "+FLAGS", "\\Deleted")
        conn.expunge()
        return json.dumps({"account": alias, "uid": uid, "moved_to": destination}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_mark_read(uid: str, account: str | None = None, folder: str = "INBOX") -> str:
    """Mark a message as read.

    Args:
        uid: The message UID.
        account: Account alias. Optional if only one account is configured.
        folder: IMAP folder (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(folder)
        conn.store(uid.encode(), "+FLAGS", "\\Seen")
        return json.dumps({"account": alias, "uid": uid, "status": "marked read"}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_mark_unread(uid: str, account: str | None = None, folder: str = "INBOX") -> str:
    """Mark a message as unread.

    Args:
        uid: The message UID.
        account: Account alias. Optional if only one account is configured.
        folder: IMAP folder (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(folder)
        conn.store(uid.encode(), "-FLAGS", "\\Seen")
        return json.dumps({"account": alias, "uid": uid, "status": "marked unread"}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_star_message(uid: str, account: str | None = None, folder: str = "INBOX") -> str:
    """Star/flag a message.

    Args:
        uid: The message UID.
        account: Account alias. Optional if only one account is configured.
        folder: IMAP folder (default "INBOX").
    """
    alias = resolve_account(account)
    conn = _imap_connect(alias)

    try:
        conn.select(folder)
        conn.store(uid.encode(), "+FLAGS", "\\Flagged")
        return json.dumps({"account": alias, "uid": uid, "status": "starred"}, indent=2)
    finally:
        conn.logout()


@mcp.tool()
def email_get_profile(account: str | None = None) -> str:
    """Get the profile info and mailbox stats for an account.

    Args:
        account: Account alias. Optional if only one account is configured.
    """
    alias = resolve_account(account)
    acct = get_account(alias)
    conn = _imap_connect(alias)

    try:
        conn.select("INBOX", readonly=True)
        _, all_data = conn.search(None, "ALL")
        total = len(all_data[0].split()) if all_data[0] else 0
        _, unseen_data = conn.search(None, "UNSEEN")
        unread = len(unseen_data[0].split()) if unseen_data[0] else 0

        return json.dumps({
            "account": alias,
            "email": acct["email"],
            "provider": acct.get("provider", "gmail"),
            "imap_server": acct["imap_host"],
            "inbox_total": total,
            "inbox_unread": unread,
        }, indent=2)
    finally:
        conn.logout()


# ── Helpers ──────────────────────────────────────────────────────────

def _build_message(
    from_addr: str, to: str, subject: str, body: str,
    cc: str | None, bcc: str | None, html_body: str | None,
) -> MIMEMultipart | MIMEText:
    if html_body:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html_body, "html"))
    else:
        msg = MIMEText(body, "plain")

    msg["From"] = from_addr
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc
    return msg
