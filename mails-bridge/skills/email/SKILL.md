---
description: "Manage multiple email accounts (Gmail, Outlook, Yahoo, iCloud, and more) — search, read, send, draft, and organize emails. Use when the user says 'check my email', 'search emails', 'send an email', 'draft a reply', 'read my inbox', 'check unread', 'star this message', 'move to trash', or any email-related request."
---

# Mails Bridge

Manage multiple email accounts through IMAP/SMTP with App Passwords. Supports Gmail, Outlook, Yahoo, iCloud, AOL, Zoho, Fastmail, ProtonMail, and any custom IMAP/SMTP provider. Every tool accepts an `account` parameter to select which mailbox to act on.

## First-time setup

When no accounts are configured (or the user asks how to set up / add an account), walk them through these steps:

1. **Check existing accounts first** — call `email_list_accounts()`. If accounts already exist, skip setup.
2. **Ask which provider** — "Which email provider? (Gmail, Outlook, Yahoo, iCloud, or other?)"
3. **Guide them to create an App Password** based on their provider:

   **Gmail:**
   - Enable 2-Step Verification: https://myaccount.google.com/signinoptions/two-step-verification
   - Create App Password: https://myaccount.google.com/apppasswords
   - Enter name "Claude", click Create, copy the 16-character password

   **Outlook / Hotmail / Live:**
   - Go to https://account.live.com/proofs/AppPassword
   - Create a new app password and copy it

   **Yahoo:**
   - Go to https://login.yahoo.com/account/security/app-passwords
   - Generate a new app password for "Other App"

   **iCloud:**
   - Go to https://appleid.apple.com → Sign-In and Security → App-Specific Passwords
   - Generate a password

   **Other providers:**
   - Ask: "What's your IMAP server and port? (e.g. imap.example.com:993)"
   - Ask: "What's your SMTP server and port? (e.g. smtp.example.com:587)"
   - The server will try `imap.{domain}` / `smtp.{domain}` if not specified

4. **Ask for details** — "What alias do you want for this account? (e.g. 'personal', 'work', 'school')" and "What's the email address?"
5. **Add the account** — call `email_add_account(alias, email_address, app_password)` (add `imap_host`/`smtp_host` for custom providers)
6. **Verify it works** — call `email_get_profile(alias)` and show them their inbox stats.
7. **Offer to add more** — "Want to add another email account?"

If the login fails, common issues are:
- App Passwords require 2FA to be enabled first
- The password has spaces — that's fine, the server strips them
- For Gmail: "Less secure app access" is NOT needed — App Passwords bypass that
- For custom providers: double-check the IMAP host and port

## Account resolution

- If the user specifies an account alias, use it.
- If only one account is configured, it's selected automatically.
- If multiple accounts exist and the user doesn't specify, ask which one.
- To act on ALL accounts, loop through each alias from `email_list_accounts`.

## Available tools

### Account management
- `email_add_account(alias, email_address, app_password, imap_host?, imap_port?, smtp_host?, smtp_port?)` — Add an email account. Auto-detects IMAP/SMTP for known providers. Pass custom servers for unlisted providers.
- `email_remove_account(alias)` — Remove an account.
- `email_list_accounts()` — Show all configured accounts and their providers.
- `email_supported_providers()` — List all auto-detected providers and their servers.

### Reading email
- `email_search(query, account, max_results, folder)` — Search emails using IMAP syntax. Common queries: `"ALL"`, `"UNSEEN"`, `"FROM \"sender@example.com\""`, `"SUBJECT \"meeting\""`, `"SINCE 01-Jun-2025"`, `"UNSEEN FROM \"boss@co.com\""`. Default folder is `"INBOX"`.
- `email_read_message(uid, account, folder)` — Read a full message by UID from search results.
- `email_read_thread(subject, account, max_messages)` — Read all messages matching a subject line. Searches All Mail (Gmail) or INBOX (other providers).

### Composing
- `email_create_draft(to, subject, body, account, cc, bcc, html_body)` — Save a draft.
- `email_send(to, subject, body, account, cc, bcc, html_body)` — Send immediately. Always confirm with the user before sending.

### Organization
- `email_list_drafts(account, max_results)` — List drafts.
- `email_list_folders(account)` — List all IMAP folders/labels.
- `email_move_message(uid, destination, account, source)` — Move a message between folders.
- `email_mark_read(uid, account, folder)` — Mark as read.
- `email_mark_unread(uid, account, folder)` — Mark as unread.
- `email_star_message(uid, account, folder)` — Star/flag a message.

### Profile
- `email_get_profile(account)` — Get inbox stats (total messages, unread count, provider).

## IMAP search syntax reference

See `references/imap-search.md` for the full IMAP search syntax guide.

## Important rules

1. **Never send an email without explicit user confirmation.** Always show the draft (to, subject, body) and ask "Should I send this?"
2. When searching across multiple accounts, run searches in parallel for speed.
3. Present email summaries in a clean table format: subject, from, date, snippet.
4. Truncate long email bodies — show the first ~500 chars and offer to show more.
5. When the user says "unread" use the IMAP query `"UNSEEN"`.
