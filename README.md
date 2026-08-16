# Enventic MCP stdio bridge

Adapts the Enventic FastAPI HTTP surface (`/mcp/*`) to the MCP stdio
JSON-RPC 2.0 protocol so Claude Desktop, Claude Code, or any stock MCP
client can connect. Stdlib-only Python (≥3.10). No pip install.

Two auth modes:

- **Recommended, any user** — get a long-lived user token from the
  Enventic web app and set `ENVENTIC_MCP_TOKEN`. The bridge just
  forwards this token; no secret handling on the client.
- **Admin fallback** — set `SERVICE_JWT_SECRET` (shared deployment
  secret) and the bridge signs its own short-lived tokens.

---

## 1. Get your MCP token (any Enventic user)

1. Sign into Enventic in your browser.
2. Visit **https://www.enventic.ai/api/mcp/token**.
3. You'll see a JSON blob:
   ```json
   {
     "token": "eyJhbGciOi...long...",
     "expires_at": "2026-09-13T...",
     "ttl_days": 30,
     "company_id": 42,
     "company_slug": "acme"
   }
   ```
4. Copy the `token` value. Guard it like a password — it grants access
   to your company's disclosure data for 30 days.

Rotate by visiting the URL again (each visit mints a new token; old
tokens keep working until they expire).

## 2. Install the bridge

```bash
git clone https://github.com/Enventic-ai/enventic-mcp-bridge.git
cd enventic-mcp-bridge
```

Make sure `python3 --version` prints 3.10 or newer. No pip install
needed — stdlib only.

## 3. Wire into Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
(macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "enventic": {
      "command": "python3",
      "args": ["/absolute/path/to/enventic-mcp-bridge/server.py"],
      "env": {
        "ENVENTIC_MCP_TOKEN": "PASTE-YOUR-TOKEN-HERE",
        "ENVENTIC_URL": "http://46.137.196.146:8000"
      }
    }
  }
}
```

Fully quit Claude Desktop (`Cmd+Q` on macOS) and reopen. The 🔌
indicator by the prompt should show `enventic` with 5 tools, 3
resources, 1 prompt.

## 4. (Alternative) Wire into Claude Code

Edit `~/.claude.json` or your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "enventic": {
      "type": "stdio",
      "command": "python3",
      "args": ["/absolute/path/to/enventic-mcp-bridge/server.py"],
      "env": {
        "ENVENTIC_MCP_TOKEN": "PASTE-YOUR-TOKEN-HERE",
        "ENVENTIC_URL": "http://46.137.196.146:8000"
      }
    }
  }
}
```

Verify with `claude mcp list`.

## 5. Try it

In Claude Desktop, ask any of:

- *"Use the enventic MCP to list every required input still missing for CSRD 2024."*
- *"Get the disclosure dataset for ESRS E1 for 2024. Which sections are ready?"*
- *"What obligations do we owe this year, and how close are we on each?"*
- *"Fetch dp.esrs.e1.scope2_location for 2024. Explain how it was computed."*

Claude picks the right tool automatically.

---

## Env vars

| Var | Default | Notes |
|---|---|---|
| `ENVENTIC_URL`         | `http://46.137.196.146:8000` | Enventic FastAPI base URL |
| `ENVENTIC_MCP_TOKEN`   | *(unset)* | Preferred: pre-minted long-lived user token from `/api/mcp/token` |
| `SERVICE_JWT_SECRET`   | *(unset)* | Admin fallback only. Same value as EC2 `.env`. **Never** share with end users. |
| `SERVICE_JWT_ISSUER`   | `enventic-bff` | Fallback only |
| `SERVICE_JWT_AUDIENCE` | `enventic-fastapi` | Fallback only |
| `ENVENTIC_COMPANY_ID`  | `1` | Fallback only. Tenant to sign as |

If both `ENVENTIC_MCP_TOKEN` and `SERVICE_JWT_SECRET` are set, the
token wins.

## Smoke test (admin fallback mode)

```bash
export SERVICE_JWT_SECRET=<...>
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | python3 server.py
```

## Smoke test (user-token mode)

```bash
export ENVENTIC_MCP_TOKEN=<paste-from-/api/mcp/token>
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' \
  | python3 server.py
```

Expect a JSON-RPC response listing 5 tools.

## Security notes

- The user token is a bearer credential. Storing it in
  `claude_desktop_config.json` is fine on a personal machine; do not
  commit that file. Set the file to `chmod 600` if you share the
  laptop.
- The token embeds *your* `company_id`; the server enforces tenant
  isolation, so the token only sees your company's disclosure data.
- If you need to revoke a token before its 30-day expiry, ask an
  Enventic admin to rotate `SERVICE_JWT_SECRET` (this invalidates all
  outstanding tokens including the short-lived BFF proxy tokens).
  Individual-token revocation is Phase-2 work.
- `SERVICE_JWT_SECRET` is the deployment-shared HMAC key. Anyone with
  it can forge tokens for any `company_id`, i.e. bypass tenant
  isolation. Keep it out of end-user configs.

## Troubleshooting

- **HTTP 401 `token_too_long_lived`** — you're on admin-fallback mode
  and the server tightened `MAX_LIFETIME_SECONDS` below 55s. Lower
  `mint_jwt`'s `exp` accordingly.
- **HTTP 401 with a user token that used to work** — token expired
  (>30d) or `SERVICE_JWT_SECRET` was rotated. Re-visit
  `/api/mcp/token`.
- **Claude Desktop shows the server as failed** — check macOS Console
  filtered by "Claude" for stderr from `server.py`. Most common:
  missing/malformed env in the config.
- **Method not found** — the bridge exposes only the methods in
  `HANDLERS` (initialize / tools/list / tools/call / resources/list /
  resources/read / prompts/list / prompts/get). Non-MCP calls fail
  loudly on purpose.
