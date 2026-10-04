# Open WebUI Tools

A small collection of tools for [Open WebUI](https://github.com/open-webui/open-webui):
Gmail, Google Calendar and an OpenRouter ZDR filter.

Everything is plain Python. No MCP server, no relay service, no Docker —
the tools talk straight to the Google APIs with `httpx` and OAuth2 refresh
tokens. Drop the files in `tools/`, restart Open WebUI, fill in the Valves.

## Tools

| Tool | File | What it does |
| --- | --- | --- |
| Gmail | [`tools/gmail.py`](tools/gmail.py) | List, search, read, draft, send, reply, archive, label and delete emails |
| Google Calendar | [`tools/google-calendar.py`](tools/google-calendar.py) | Read, search, create, update and delete events, across several calendars |
| OpenRouter ZDR | [`tools/openrouter_zdr.py`](tools/openrouter_zdr.py) | Forces `provider.zdr = true` on every OpenRouter request |

Both Google tools share the same shape: OAuth2 client ID + secret + a long
lived refresh token, stored in the tool Valves (`Workspace → Tools → <tool>`).

## Installation

```bash
cd /path/to/open-webui/backend/open_webui/tools
cp /path/to/this/repo/tools/*.py .
```

Restart Open WebUI. The tools appear under **Workspace → Tools**, and their
Valves under **Tools → <name>**.

Each tool declares its own dependencies in the docstring header, read by
Open WebUI on load:

- `gmail.py` → `httpx>=0.27`
- `google-calendar.py` → `httpx>=0.27`
- `openrouter_zdr.py` → nothing (pydantic only)

## OAuth2 setup (Gmail & Calendar)

Both use the same credentials; the scopes differ. Getting a refresh token
takes about five minutes, once.

### 1. Create the OAuth client

In the [Google Cloud Console](https://console.cloud.google.com):

- **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
- Application type: **Web application**
- Authorized redirect URI: `https://developers.google.com/oauthplayground`

### 2. Enable the APIs you need

- **APIs & Services → Library → "Gmail API" → Enable**
- **APIs & Services → Library → "Google Calendar API" → Enable**

### 3. Get a refresh token

On the [OAuth 2.0 Playground](https://developers.google.com/oauthplayground):

1. Gear icon (top right) → *Use your own OAuth credentials* → paste your
   Client ID and Client Secret.
2. **Step 1** — enter the scope:
   - `https://mail.google.com/` for Gmail
   - `https://www.googleapis.com/auth/calendar` for Calendar
   - or both, space-separated, if you want one refresh token for both tools
3. **Authorize APIs** and sign in with the Google account you want to expose.
4. **Step 2** — *Exchange authorization code for tokens*.
5. Copy the **Refresh token**.

### 4. Fill in the Valves

| Valve | Notes |
| --- | --- |
| `CLIENT_ID` | OAuth2 client ID |
| `CLIENT_SECRET` | OAuth2 client secret |
| `REFRESH_TOKEN` | From step 3.5 |
| `DEFAULT_MAX_RESULTS` / `MAX_RESULTS` | Page size for list/search calls |
| `REQUEST_TIMEOUT` | HTTP timeout in seconds (default `15.0`) |
| `DEFAULT_TIMEZONE` | Calendar only — IANA timezone for created events |
| `DEFAULT_CALENDAR_ID` | Calendar only — `primary` for the main calendar |
| `CALENDARS_TO_WATCH` | Calendar only — extra calendar IDs, comma-separated |

The refresh token is as sensitive as a password: anyone holding it can act on
the account until it is revoked. Revoke it from
[Google Account → Security → Third-party access](https://myaccount.google.com/connections).

## Using the tools

### Gmail

| Method | Description |
| --- | --- |
| `check_auth_status()` | Confirms the connection and returns the mailbox address |
| `get_unread_count()` | Unread count in the inbox, without reading any content |
| `list_recent_emails(max_results, label)` | Recent messages from `INBOX`, `SENT`, `DRAFTS`, `SPAM`, `STARRED`, `UNREAD`, `TRASH` |
| `search_emails(query, max_results)` | Gmail search syntax (`from:`, `subject:`, `has:attachment`, `after:` …) |
| `get_email_content(message_id)` | Full body of one message |
| `send_email(to, subject, body, cc, bcc)` | Sends a message |
| `reply_to_email(message_id, body, reply_all)` | Replies inside the original thread |
| `create_draft(to, subject, body)` | Saves a draft without sending it |
| `archive_email(message_id)` | Removes `INBOX` |
| `delete_email(message_id)` | Moves to trash |
| `mark_as_read` / `mark_as_unread` | Toggles the `UNREAD` label |
| `add_label(message_id, label)` | Adds a label |

### Google Calendar

| Method | Description |
| --- | --- |
| `check_auth_status()` | Verifies the token and lists accessible calendars |
| `list_calendars()` | IDs of every calendar the account can see |
| `list_upcoming_events(max_results, calendar_id)` | Next events |
| `search_events(query, time_min, time_max, max_results, calendar_id)` | Free-text search in a window |
| `get_event_details(event_id, calendar_id)` | One event in full |
| `create_event(summary, start_datetime, end_datetime, …)` | Creates an event, with description, location and attendees |
| `quick_add_event(text)` | Natural language, e.g. *"Dentist tuesday 15:00"* |
| `update_event(event_id, …)` | Partial update — only the fields you pass are touched |
| `delete_event(event_id)` | Removes an event |

Dates are ISO 8601 (`2026-10-04T15:00:00+02:00`); `create_event` also accepts
`all_day=True` with `YYYY-MM-DD` boundaries.

### OpenRouter ZDR

A filter with a single Valve, `ZDR_ENABLED` (default `true`). When active it
adds `provider: { zdr: true }` to every request body, so OpenRouter only routes
to providers with zero data retention. If your OpenRouter plan does not
support ZDR, requests will fail — turn the Valve off.

## Prompting

The Gmail docstrings tell the model to ask before reading a mailbox, but a
model can still be talked into it. If you care about that boundary, state it
in a system prompt:

> Before any Gmail or Calendar tool call, ask me for confirmation and wait for
> an explicit yes. Never send, delete or modify anything on the first request.

Anything the model does goes through your own Google account. Revoking access
at any time is the fastest way to stop it.

## Licence

**Non-Commercial + Attribution.** See [LICENSE](LICENSE).

Personal, research and evaluation use is fine. Commercial use, resale, or
use in a product you charge for requires written permission from the author,
with credit. Contributions are welcome but you keep your copyright and are
credited as a contributor.

## Contributing

Issues and pull requests are welcome. Keep the existing style: French docstrings,
English identifiers, `httpx` only, no new runtime dependencies.

By contributing you agree that your work is licensed under the same terms, and
that you are credited as a contributor.

## Author

Anas — [GitHub](https://github.com/anas)