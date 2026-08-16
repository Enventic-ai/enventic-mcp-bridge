# Enventic MCP 使用指南

从安装到日常使用 · Claude Desktop / Claude Code · 5 分钟接入

---

## 目录

1. [MCP 是什么, 能做什么](#1-mcp-是什么-能做什么)
2. [Enventic MCP 提供的能力](#2-enventic-mcp-提供的能力)
3. [接入前置条件](#3-接入前置条件)
4. [Step 1 — 装 bridge](#4-step-1--装-bridge)
5. [Step 2 — 拿 token](#5-step-2--拿-token)
6. [Step 3 — 配置 Claude](#6-step-3--配置-claude)
7. [Step 4 — 重启验证](#7-step-4--重启验证)
8. [日常使用 (推荐 prompt)](#8-日常使用-推荐-prompt)
9. [常见问题 & 排错](#9-常见问题--排错)
10. [安全 & 隐私](#10-安全--隐私)
11. [Token 管理](#11-token-管理)

---

## 1. MCP 是什么, 能做什么

**MCP** (Model Context Protocol) 是 Anthropic 开放协议, 让 Claude 直接调外部数据 / 工具 / 流程. 不用打开 Enventic 网站, 直接在 Claude Desktop 里问, Claude 自己调 Enventic 的 API 拿数据回来.

**核心价值**:
- **数据缺口驱动** — "CSRD 2024 还差哪些数据?" 一句话拉出 51 项清单
- **数字追溯** — "Scope 2 那 115 tCO₂e 怎么算的?" 秒级返回排放因子 + GWP + 方法论
- **合规日历** — "今年要交哪些报告, 各自准备了多少?" 一次拿全 9 个 obligation
- **叙述起草** — "起草 ESRS E1 章节草稿" Claude 直接用 Enventic 数据生成

---

## 2. Enventic MCP 提供的能力

### 5 Tools (功能)

| 工具名 | 做什么 | 典型问法 |
|---|---|---|
| `list_disclosure_obligations` | 列监管义务 + readiness | "What reports do we owe this year?" |
| `get_disclosure_dataset` | 完整披露包 (框架/期间) | "Give me the full ESRS E1 dataset for 2024" |
| `get_datapoint` | 单点 + 完整 provenance | "Where does dp.esrs.e1.scope2_location come from?" |
| `get_emissions_inventory` | Scope 1/2/3 + 4 种细分 | "Break down 2024 emissions by site" |
| `list_required_inputs` | 缺失数据清单 (最常用) | "What data is still missing for CSRD 2024?" |

### 3 Resources (可读资源)
- `disclosure://CSRD_ESRS/{period}`
- `disclosure://IFRS_S1/{period}`
- `disclosure://IFRS_S2/{period}`

### 1 Prompt (模板)
- `draft_disclosure_narrative` — 起草披露章节文本

---

## 3. 接入前置条件

| 需要 | 怎么装 |
|---|---|
| Claude Desktop *或* Claude Code Desktop | 官网下载, 已装则跳过 |
| Python 3.10+ | `python3 --version` 检查; 没有跑 `brew install python3` |
| Enventic 账号 (真账号, 非 demo) | 已注册 `https://www.enventic.ai` |
| Git | Mac 自带, 或 `brew install git` |

---

## 4. Step 1 — 装 bridge

**克隆 bridge 仓库** (公开 repo, 30 秒完成):

```bash
git clone https://github.com/Enventic-ai/enventic-mcp-bridge.git ~/enventic-mcp-bridge
```

装好后目录:

```
~/enventic-mcp-bridge/
  ├── server.py    # stdio 桥 (176 行, 无 pip 依赖)
  ├── README.md
  ├── GUIDE.md     # 本文
  └── .gitignore
```

> **为什么需要 bridge**: Claude Desktop 走 stdio JSON-RPC, Enventic 后端是 HTTP. 这个 bridge 把两边翻译. Python 标准库, 不用 pip install.

---

## 5. Step 2 — 拿 token

1. **登录 Enventic** — 浏览器打开 `https://www.enventic.ai`, 用真账号登录 (demo 账号不允许).
2. **访问 token 端点** — 保持登录状态, 浏览器直接打开:

   ```
   https://www.enventic.ai/api/mcp/token
   ```

3. **拷 `token` 值**. 页面返回:

   ```json
   {
     "token": "eyJhbGciOi.....很长的一串.....",
     "expires_at": "2026-09-15T04:48:16Z",
     "ttl_days": 30,
     "company_id": 42,
     "company_slug": "acme"
   }
   ```

   拷 `token` 字段的完整值 (整串 `eyJ...`).

> ⚠️ **Token 敏感度**: 这是 30 天 bearer 凭证, 携带你的 `company_id`. 别贴到公共聊天 / GitHub / Slack. 只放本机 config 文件.

---

## 6. Step 3 — 配置 Claude

### Claude Desktop (经典聊天 app)

打开配置文件:

```bash
mkdir -p "$HOME/Library/Application Support/Claude"
open "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
```

如果文件是空的, 完整粘贴 (记得换 `YOUR-USERNAME` 和 token):

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

如果文件已有内容, 只**加**顶层 `mcpServers` 字段, 别删其他.

### Claude Code Desktop / CLI

配置文件位置: `~/.claude.json`

加同样 block 到 root 级 `mcpServers`:

```json
{
  "...其他配置保留不动...": "",
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

## 7. Step 4 — 重启验证

1. **Cmd+Q** 完全退出 Claude (不是关窗口, 一定要 Cmd+Q).
2. 重开 Claude.
3. 验证 3 种方法任选:
   - **直接问**: "Use enventic to list what data is missing for CSRD 2024." → 应返回 51 条列表
   - **输入框 `+` / 附件按钮** → 展开菜单应含 `enventic (5 tools)`
   - **敲 `/mcp`** → 面板显示 `enventic ✓ Connected`

> **没生效常见原因**:
> - Cmd+Q 没执行 (只点关窗) — Cmd+Tab 到 Claude, 再 Cmd+Q
> - 路径写错 — `args` 里必须绝对路径, 不能 `~`
> - Python 找不到 — Terminal 跑 `which python3` 拿绝对路径, 换掉 `"command"` 里的 `"python3"`
> - Token 过期 (>30 天) — 重访 `/api/mcp/token` 拿新的

---

## 8. 日常使用 (推荐 prompt)

### 数据收集场景
> List every CSRD 2024 input I'm still missing, grouped by domain, and rank them by urgency.

→ Claude 调 `list_required_inputs`, 返 35 项缺失 + 按 A-H 域分组 + 优先级建议

### 合规进度场景 (CSO/CFO)
> Which disclosure obligations do we owe this reporting year, and how ready are we on each? Include per-obligation datapoint counts.

→ 调 `list_disclosure_obligations`, 返 9 个 obligation (CSRD/CBAM/IFRS S2/SEC 等) + 每个 ready/missing 计数

### 审计追溯场景
> Where does dp.esrs.e1.scope2_location for 2024 come from? Show me the emission factors, GWP set, and consolidation basis.

→ 调 `get_datapoint`, 返值 + provenance JSON (EF IDs / methodology / audit_trail)

### 排放清单场景
> Break down our 2024 GHG emissions by site. Which 3 sites contribute the most?

→ 调 `get_emissions_inventory` + `breakdown=by_site`, 返各站 S1/S2/S3 + 排序

### 报告起草场景
> Draft the ESRS E1 climate narrative for 2024. Ground every figure in the dataset — no invented numbers. Cite each figure by datapoint_id.

→ Claude 用 `draft_disclosure_narrative` prompt + `get_disclosure_dataset`, 生成 400-800 字草稿

### 双框架场景 (CSRD + IFRS 一次算)
> Show me the same Scope 1 number as both CSRD ESRS E1-6 and IFRS S2 §29(a)(i). Are they identical?

→ 演示"一次算, 两次映"的差异化能力

---

## 9. 常见问题 & 排错

| 问题 | 原因 | 解法 |
|---|---|---|
| `/api/mcp/token` 返 401 | 没登录 / cookie 过期 | 浏览器登录 `www.enventic.ai` 再访问 |
| `/api/mcp/token` 返 403 `demo_forbidden` | 用了 demo 账号 | 换真账号登录 |
| Claude Desktop 里 MCP 灰色 / 显示 failed | bridge 启动失败 | 看 macOS Console 搜 "Claude", 常见: python3 找不到, 路径拼错 |
| 返 `401 token_expired` | Token 过 30 天 | 重访 `/api/mcp/token` |
| 返 `401 token_too_long_lived` | 使用了 admin 模式但 TTL 超 | 切回 user token 模式 (推荐) |
| Tool 调用返 "not found" | 没重启 Claude | Cmd+Q 完全退出重开 |
| 找不到 `python3` | PATH 问题 | 用绝对路径: `/usr/local/bin/python3` 或 `/opt/homebrew/bin/python3` |

---

## 10. 安全 & 隐私

### Token 是什么
- 30 天有效期的 bearer 凭证, HS256 签名
- 嵌入你的 `company_id` — 服务器强制租户隔离, 只能看你公司数据
- 不含密码, 无法反推 Enventic 登录凭证

### 数据传输
- Bridge (本机) ↔ Enventic (EC2) 走 HTTPS (生产) / HTTP (当前 dev)
- Claude Desktop ↔ Bridge 走本地 stdio (不出机器)
- Claude ↔ Anthropic 服务器走 HTTPS (你的 prompt 和 tool 返回都会经 Anthropic)

### 你应该做
- Config 文件设 `chmod 600`:
  ```bash
  chmod 600 "$HOME/Library/Application Support/Claude/claude_desktop_config.json"
  ```
- 别把 config 文件提交到 GitHub
- 换机器时删旧 token

### 不要做
- 把 token 贴到公共 chat / Slack / email
- 用同一 token 装到多台机器 (虽然能用, 但一泄漏所有机器都要重配)
- 联系任何声称是 "Enventic 客服" 索要 token 的人

---

## 11. Token 管理

### 拿新 token
重访 `https://www.enventic.ai/api/mcp/token` → 拿新 JSON → 拷 `token` 换到 config → 重启 Claude.

### Token 有效期
30 天. 到期前 Claude 会返 401. 提前几天换即可.

### Rotate (安全周期)
推荐每 30 天主动重访 `/api/mcp/token` 换新 token, 不必等自然过期. 老 token 到期后自动失效.

### Revoke (紧急吊销)
目前只能 Enventic admin 全量 rotate `SERVICE_JWT_SECRET`, 会踢掉所有 outstanding token (包括自己). 单 token revoke 是 Phase 2 功能.

---

## 参考链接

- Bridge 仓库: https://github.com/Enventic-ai/enventic-mcp-bridge
- Enventic Web: https://www.enventic.ai
- Token endpoint: https://www.enventic.ai/api/mcp/token
- MCP 协议官方: https://modelcontextprotocol.io

---

*Enventic MCP Phase 1 · 生成时间 2026-08-16 · 内部使用*
