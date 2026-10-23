# pi-mcp-servers

Small Model Context Protocol (MCP) servers for Google Contacts, Google Tasks, Gmail label filters, and Telegram media, built for a Raspberry Pi home server.

Each server is a single self-contained file. The Python servers use the MCP Python SDK (FastMCP) and plain `urllib` against the Google/Telegram APIs; the Google Tasks server is Node, using `@modelcontextprotocol/sdk` and `googleapis`.

## Servers

| Folder | File | Tools |
| --- | --- | --- |
| `google-contacts/` | `contacts_mcp.py` | `search_contacts`, `list_contacts`, `create_contact`, `update_contact`, `delete_contact` (Google People API) |
| `google-tasks/` | `index.js` | `tasks_list`, `tasks_add`, `tasks_complete`, `tasks_delete` (Google Tasks API) |
| `gmail-filters/` | `gmail_filters_mcp.py` | `list_filters`, `create_filter`, `delete_filter` (Gmail API filter settings) |
| `telegram-media/` | `telegram_media_mcp.py` | `send_message`, `send_photo_file`, `send_video_file`, `send_photo_base64` (Telegram Bot API) |

## Credentials

No credentials live in this repo. The servers read them from local files at runtime:

- Google servers: an OAuth refresh token at `~/.config/google-docs-mcp/token.json`, plus a client ID/secret pair in `~/services/secrets/google.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`). The token needs scopes covering People, Tasks, and Gmail settings, depending on which servers you run.
- Telegram server: an env file at `~/services/secrets/telegram-trouble.env` with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

Adjust the paths in the loader at the top of each file if your layout differs.

## Running

Python servers:

```sh
pip install mcp
python3 contacts_mcp.py   # stdio transport, ready for an MCP client config
```

Google Tasks server:

```sh
cd google-tasks
npm install
node index.js
```

## License

MIT — see [LICENSE](LICENSE).
