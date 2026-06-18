# IMAP Search Syntax

## Basic queries
- `ALL` — all messages
- `UNSEEN` — unread messages
- `SEEN` — read messages
- `FLAGGED` — starred messages
- `UNFLAGGED` — unstarred messages
- `DELETED` — deleted messages
- `NEW` — new (recent + unseen)

## Sender / recipient
- `FROM "sender@example.com"` — from specific sender
- `TO "recipient@example.com"` — to specific recipient
- `CC "user@example.com"` — in CC

## Content
- `SUBJECT "meeting"` — subject contains word
- `BODY "project update"` — body contains phrase
- `TEXT "keyword"` — subject or body contains word

## Date filters
- `SINCE 01-Jun-2025` — on or after date
- `BEFORE 01-Jun-2025` — before date
- `ON 01-Jun-2025` — on exact date
- Date format: `DD-Mon-YYYY` (e.g. `01-Jan-2026`, `15-Mar-2025`)

## Size
- `LARGER 1000000` — larger than N bytes
- `SMALLER 5000` — smaller than N bytes

## Combining queries
- `UNSEEN FROM "boss@co.com"` — AND (space-separated)
- `OR FROM "alice@co.com" FROM "bob@co.com"` — OR
- `NOT SEEN` — NOT

## Gmail-specific folders
- `INBOX` — inbox
- `"[Gmail]/All Mail"` — all mail
- `"[Gmail]/Sent Mail"` — sent
- `"[Gmail]/Drafts"` — drafts
- `"[Gmail]/Trash"` — trash
- `"[Gmail]/Spam"` — spam
- `"[Gmail]/Starred"` — starred

## Examples
```
UNSEEN                                    # all unread
FROM "recruiter@company.com"              # from specific sender
UNSEEN SINCE 01-Jun-2025                  # unread since date
SUBJECT "interview" SINCE 01-May-2025     # subject + date
OR FROM "alice@co.com" FROM "bob@co.com"  # from either person
TEXT "invoice" BEFORE 01-Jan-2026         # keyword before date
```
