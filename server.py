#!/usr/bin/env python3
"""Enventic MCP stdio bridge.

Speaks MCP JSON-RPC 2.0 on stdin/stdout, forwards each call to the
Enventic FastAPI HTTP surface.

Two auth modes:

  * **Preferred** — set ``ENVENTIC_MCP_TOKEN`` to a pre-minted long-
    lived user token (get one from Enventic → Settings → MCP Access,
    or GET /api/mcp/token in your browser while logged in). The bridge
    just forwards this token as a Bearer credential. This is the mode
    that lets any Enventic user set the bridge up on their own laptop
    without ever handling the shared ``SERVICE_JWT_SECRET``.

  * **Fallback** — set ``SERVICE_JWT_SECRET`` (+ optional
    ``SERVICE_JWT_ISSUER`` / ``AUDIENCE`` / ``ENVENTIC_COMPANY_ID``)
    and the bridge mints its own 55s tokens on every request. Only
    admins with access to the deployment secret should use this mode.

Config via env vars:
  ENVENTIC_URL           default http://46.137.196.146:8000
  ENVENTIC_MCP_TOKEN     preferred — long-lived user token
  SERVICE_JWT_SECRET     fallback — server-shared HMAC secret
  SERVICE_JWT_ISSUER     default enventic-bff  (fallback only)
  SERVICE_JWT_AUDIENCE   default enventic-fastapi  (fallback only)
  ENVENTIC_COMPANY_ID    default 1 (demo)  (fallback only)

Wire into Claude Desktop / Claude Code via a `mcpServers` entry that
points `command` at `python3` and `args` at this file.

Stdlib only — no pip install.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL      = os.environ.get("ENVENTIC_URL", "http://46.137.196.146:8000").rstrip("/")
STATIC_TOKEN  = os.environ.get("ENVENTIC_MCP_TOKEN", "").strip()
JWT_SECRET    = os.environ.get("SERVICE_JWT_SECRET", "")
JWT_ISSUER    = os.environ.get("SERVICE_JWT_ISSUER", "enventic-bff")
JWT_AUDIENCE  = os.environ.get("SERVICE_JWT_AUDIENCE", "enventic-fastapi")
COMPANY_ID    = int(os.environ.get("ENVENTIC_COMPANY_ID", "1"))
PROTOCOL_VER  = "2025-06-18"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def mint_jwt() -> str:
    """HS256 JWT with 55s TTL — under the server's 60s max."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": "enventic-mcp-bridge",
        "company_id": COMPANY_ID,
        "role": "writer",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + 55,
    }
    h = _b64url(json.dumps(header,  separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig_input = f"{h}.{p}".encode()
    sig = _b64url(hmac.new(JWT_SECRET.encode(), sig_input, hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"


def bearer_token() -> str:
    """Prefer a pre-minted user token; fall back to signing our own."""
    if STATIC_TOKEN:
        return STATIC_TOKEN
    if not JWT_SECRET:
        raise RuntimeError(
            "Set ENVENTIC_MCP_TOKEN (preferred) or SERVICE_JWT_SECRET (admin fallback)."
        )
    return mint_jwt()


def _http(method: str, path: str, *, body: dict | None = None,
          params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={
            "Authorization": f"Bearer {bearer_token()}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            detail = json.loads(raw).get("detail", raw)
        except Exception:
            detail = raw
        raise RuntimeError(f"HTTP {e.code}: {detail}")


# ─── MCP method handlers ─────────────────────────────────────────────

def h_initialize(_: dict) -> dict:
    return {
        "protocolVersion": PROTOCOL_VER,
        "capabilities": {
            "tools":     {"listChanged": False},
            "resources": {"listChanged": False, "subscribe": False},
            "prompts":   {"listChanged": False},
        },
        "serverInfo": {"name": "enventic-mcp", "version": "0.1.0"},
    }


def h_tools_list(_: dict) -> dict:
    r = _http("GET", "/mcp/tools")
    return {"tools": r.get("tools", [])}


def h_tools_call(params: dict) -> dict:
    name = params.get("name")
    args = params.get("arguments", {})
    r = _http("POST", "/mcp/tools/call", body={"name": name, "arguments": args})
    result = r.get("result", r)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


def h_resources_list(_: dict) -> dict:
    r = _http("GET", "/mcp/resources")
    resources = r if isinstance(r, list) else r.get("resources", [])
    return {"resources": resources}


def h_resources_read(params: dict) -> dict:
    uri = params.get("uri", "")
    r = _http("GET", "/mcp/resources/read", params={"uri": uri})
    payload = r.get("payload", r)
    return {"contents": [{
        "uri": uri, "mimeType": "application/json",
        "text": json.dumps(payload, indent=2),
    }]}


def h_prompts_list(_: dict) -> dict:
    r = _http("GET", "/mcp/prompts")
    prompts = r if isinstance(r, list) else r.get("prompts", [])
    return {"prompts": prompts}


def h_prompts_get(params: dict) -> dict:
    r = _http("POST", "/mcp/prompts/get",
              body={"name": params.get("name"),
                    "arguments": params.get("arguments", {})})
    return {
        "description": r.get("description"),
        "messages": [
            {"role": m["role"],
             "content": {"type": "text", "text": m.get("content", "")}}
            for m in r.get("messages", [])
        ],
    }


HANDLERS = {
    "initialize":       h_initialize,
    "tools/list":       h_tools_list,
    "tools/call":       h_tools_call,
    "resources/list":   h_resources_list,
    "resources/read":   h_resources_read,
    "prompts/list":     h_prompts_list,
    "prompts/get":      h_prompts_get,
}


def send(msg: dict) -> None:
    sys.stdout.write(json.dumps(msg, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            send({"jsonrpc": "2.0", "id": None,
                  "error": {"code": -32700, "message": f"parse error: {e}"}})
            continue

        rid    = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {}) or {}

        # Notifications (no id) — no response.
        if rid is None and method.startswith("notifications/"):
            continue

        handler = HANDLERS.get(method)
        if handler is None:
            send({"jsonrpc": "2.0", "id": rid,
                  "error": {"code": -32601, "message": f"method not found: {method}"}})
            continue
        try:
            result = handler(params)
            send({"jsonrpc": "2.0", "id": rid, "result": result})
        except Exception as e:
            send({"jsonrpc": "2.0", "id": rid,
                  "error": {"code": -32000, "message": str(e)}})


if __name__ == "__main__":
    main()
