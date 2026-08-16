# Enventic MCP User Guide

From install to daily use · Claude Desktop / Claude Code · 5-minute setup

---

## Contents

1. [What is MCP, and what can it do](#1-what-is-mcp-and-what-can-it-do)
2. [What Enventic MCP provides](#2-what-enventic-mcp-provides)
3. [Prerequisites](#3-prerequisites)
4. [Step 1 — Install the bridge](#4-step-1--install-the-bridge)
5. [Step 2 — Get your token](#5-step-2--get-your-token)
6. [Step 3 — Configure Claude](#6-step-3--configure-claude)
7. [Step 4 — Restart & verify](#7-step-4--restart--verify)
8. [Everyday usage (recommended prompts)](#8-everyday-usage-recommended-prompts)
9. [Troubleshooting](#9-troubleshooting)
10. [Security & privacy](#10-security--privacy)
11. [Token management](#11-token-management)

---

## 1. What is MCP, and what can it do

**MCP** (Model Context Protocol) is an open protocol from Anthropic that lets Claude talk directly to external data, tools, and workflows. You don't need to open the Enventic web app — just ask Claude Desktop, and Claude calls Enventic's API on your behalf.

**Core value**:
- **Data-gap driver** — "What CSRD 2024 inputs am I still missing?" pulls all 51 items in one shot
- **Number traceability** — "Where does that 115 tCO₂e Scope 2 figure come from?" returns emission factors + GWP set + methodology in seconds
- **Compliance calendar** — "Which reports do we owe this year, and how ready are we?" returns all 9 obligations with per-item readiness counts
- **Narrative drafting** — "Draft the ESRS E1 climate section" uses your actual Enventic data

---

## 2. What Enventic MCP provides

### 5 Tools

| Tool | What it does | Sample prompt |
|---|---|---|
| `list_disclosure_obligations` | List regulatory obligations with readiness rollup | "What reports do we owe this year?" |
| `get_disclosure_dataset` | Full disclosure pack for a framework/period | "Give me the full ESRS E1 dataset for 2024" |
| `get_datapoint` | Single datapoint with full provenance | "Where does dp.esrs.e1.scope2_location come from?" |
| `get_emissions_inventory` | Scope 1/2/3 totals plus 4 breakdown modes | "Break down 2024 emissions by site" |
| `list_required_inputs` | Missing-data checklist (most used) | "What data is still missing for CSRD 2024?" |

### 3 Resources (readable URIs)
- `disclosure://CSRD_ESRS/{period}`
- `disclosure://IFRS_S1/{period}`
- `disclosure://IFRS_S2/{period}`

### 1 Prompt template
- `draft_disclosure_narrative` — drafts the narrative text for a disclosure section

---

## 3. Prerequisites

| Requirement | How to install |
|---|---|
| Claude Desktop *or* Claude Code Desktop | Download from claude.ai, skip if already installed |
| Python 3.10+ | Check with `python3 --version`; install with `brew install python3` |
| Enventic account (real, not demo) | Sign up at `https://www.enventic.ai` |
| Git | Ships with macOS, or `brew install git` |

---

## 4. Step 1 — Install the bridge

Clone the bridge repo (public, ~30 seconds):

```bash
git clone https://github.com/Enventic-ai/enventic-mcp-bridge.git ~/enventic-mcp-bridge
```

Installed layout:

```
~/enventic-mcp-bridge/
  ├── server.py    # stdio bridge (176 lines, stdlib only)
  ├── README.md
  ├── GUIDE.md     # this guide
  └── .gitignore
```

> **Why a bridge?** Claude Desktop speaks MCP stdio JSON-RPC; Enventic's backend is HTTP. The bridge translates between them. Pure Python stdlib — no pip install needed.

---

## 5. Step 2 — Get your token

1. **Sign in to Enventic** — open `https://www.enventic.ai` in your browser with a real account (demo accounts cannot mint tokens).
2. **Visit the token endpoint** — while signed in, open:

   ```
   https://www.enventic.ai/api/mcp/token
   ```

3. **Copy the `token` value**. The page returns:

   ```json
   {
     "token": "eyJhbGciOi.....long.....",
     "expires_at": "2026-09-15T04:48:16Z",
     "ttl_days": 30,
     "company_id": 42,
     "company_slug": "acme"
   }
   ```

   Copy the full `token` string (the whole `eyJ...` value).

> ⚠️ **Token sensitivity**: this is a 30-day bearer credential carrying your `company_id`. Never paste it into public chats, GitHub, Slack, or email. Keep it in your local config file only.

---

## 6. Step 3 — Configure Claude

### Claude Desktop (classic chat app)

Open the config file:

```bash
mkdir -p "$HOME/Library/Application Support/Claude"
open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

If empty, paste the block below (replace `YOUR-USERNAME` and paste your token):

```json
{
  "mcpServers": {
    "enventic": {
      "command": "python3",
      "args": ["/Users/YOUR-USERNAME/enventic-mcp-bridge/server.py"],
      "env": {
        "ENVENTIC_MCP_TOKEN": "PASTE-YOUR-TOKEN-HERE",
        "ENVENTIC_URL": "http://46.137.196.146:8000"
      }
    }
  }
}
```

If the file already has other content, only **add** the top-level `mcpServers` field — do not remove existing keys.

### Claude Code Desktop / CLI

Config file: `~/.claude.json`

Add the same block at the root level under `mcpServers`:

```json
{
  "...preserve other config...": "",
  "mcpServers": {
    "enventic": {
      "type": "stdio",
      "command": "python3",
      "args": ["/Users/YOUR-USERNAME/enventic-mcp-bridge/server.py"],
      "env": {
        "ENVENTIC_MCP_TOKEN": "PASTE-YOUR-TOKEN-HERE",
        "ENVENTIC_URL": "http://46.137.196.146:8000"
      }
    }
  }
}
```

---

## 7. Step 4 — Restart & verify

1. **Cmd+Q** to fully quit Claude (not just close the window — Cmd+Q).
2. Reopen Claude.
3. Verify with any of the three methods:
   - **Ask directly**: "Use enventic to list what data is missing for CSRD 2024." — should return a list of 51 items.
   - **Input-box `+` / attachment button** — the menu should show `enventic (5 tools)`.
   - **Type `/mcp`** — the panel should show `enventic ✓ Connected`.

> **Common reasons it didn't take effect**:
> - Didn't actually Cmd+Q (just closed the window) — Cmd+Tab back to Claude, then Cmd+Q
> - Wrong path — `args` must be absolute, not `~`
> - Python not on PATH — run `which python3` in Terminal and replace `"python3"` with the absolute path
> - Token expired (>30 days) — revisit `/api/mcp/token` to get a fresh one

---

## 8. Everyday usage (recommended prompts)

### Data-gathering
> List every CSRD 2024 input I'm still missing, grouped by domain, and rank them by urgency.

→ Claude calls `list_required_inputs` and returns 35 missing items grouped by domain A–H with priority guidance.

### Compliance progress (CSO/CFO)
> Which disclosure obligations do we owe this reporting year, and how ready are we on each? Include per-obligation datapoint counts.

→ Calls `list_disclosure_obligations`, returns 9 obligations (CSRD, CBAM, IFRS S2, SEC Climate, …) with ready/missing counts per item.

### Audit trace
> Where does dp.esrs.e1.scope2_location for 2024 come from? Show me the emission factors, GWP set, and consolidation basis.

→ Calls `get_datapoint`, returns the value plus provenance JSON (EF IDs, methodology, audit trail).

### Emissions inventory
> Break down our 2024 GHG emissions by site. Which 3 sites contribute the most?

→ Calls `get_emissions_inventory` with `breakdown=by_site`, returns per-site S1/S2/S3 sorted by total.

### Narrative drafting
> Draft the ESRS E1 climate narrative for 2024. Ground every figure in the dataset — no invented numbers. Cite each figure by datapoint_id.

→ Claude combines the `draft_disclosure_narrative` prompt with `get_disclosure_dataset` to produce a 400–800 word draft.

### Dual-framework (CSRD + IFRS, computed once)
> Show me the same Scope 1 number as both CSRD ESRS E1-6 and IFRS S2 §29(a)(i). Are they identical?

→ Demonstrates the "compute once, map twice" architecture: the same computed number is exposed under both taxonomy references.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `/api/mcp/token` returns 401 | Not signed in / cookie expired | Sign in to `www.enventic.ai` first, then retry |
| `/api/mcp/token` returns 403 `demo_forbidden` | Used a demo account | Sign in with a real account |
| MCP shows grey / "failed" in Claude Desktop | Bridge failed to start | Open macOS Console, filter by "Claude" — usually `python3` not found or path typo |
| `401 token_expired` | Token past 30 days | Revisit `/api/mcp/token` |
| `401 token_too_long_lived` | Admin fallback mode with excessive TTL | Switch back to user-token mode (recommended) |
| Tool call returns "not found" | Claude wasn't restarted | Cmd+Q fully quit, then reopen |
| `python3` not found | PATH issue | Use absolute path: `/usr/local/bin/python3` or `/opt/homebrew/bin/python3` |

---

## 10. Security & privacy

### What the token is
- 30-day bearer credential, HS256-signed JWT
- Embeds your `company_id` — server enforces tenant isolation; the token can only see your company's data
- Does not contain your password; cannot be reversed into Enventic login credentials

### Data transport
- Bridge (your machine) ↔ Enventic (EC2) — HTTPS (production) / HTTP (current dev)
- Claude Desktop ↔ Bridge — local stdio (never leaves your machine)
- Claude ↔ Anthropic servers — HTTPS (your prompts and tool responses do transit Anthropic)

### Do
- Set the config file to `chmod 600`:
  ```bash
  chmod 600 "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
  ```
- Never commit the config file to GitHub
- Rotate your token when changing machines

### Do not
- Paste the token into public chats, Slack, or email
- Reuse the same token across multiple machines (works, but a single leak forces re-config everywhere)
- Give the token to anyone claiming to be "Enventic support" — support never asks for it

---

## 11. Token management

### Get a new token
Revisit `https://www.enventic.ai/api/mcp/token` → copy the new `token` → replace in your config → restart Claude.

### Lifetime
30 days. Claude will return 401 once it expires. Rotate a few days before expiry to avoid interruption.

### Rotation cadence
Recommended: proactively rotate every 30 days by revisiting `/api/mcp/token`. Old tokens die on their own at expiry.

### Emergency revocation
Currently only an Enventic admin can revoke by rotating `SERVICE_JWT_SECRET`, which invalidates every outstanding token including their own. Per-token revocation is Phase 2 work.

---

## Reference links

- Bridge repo: https://github.com/Enventic-ai/enventic-mcp-bridge
- Enventic Web: https://www.enventic.ai
- Token endpoint: https://www.enventic.ai/api/mcp/token
- MCP protocol: https://modelcontextprotocol.io

---

*Enventic MCP Phase 1 · Generated 2026-08-16 · Internal use*
