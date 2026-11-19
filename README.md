# 第二组 · AI 爬虫自动化获客

跨境独立站课题的实践方向：从**公开信息源**采集目标客户线索，清洗验证后由 AI 生成个性化开发信，小批量触达并记录回复，形成可复盘的获客闭环。

本项目是一套可本地运行的多智能体骨架（FastAPI + 原生前端），不是一次性脚本集合。所有动作经由「主控路由 → 业务智能体 → 工具」执行，并统一经过约束层、预算与遥测记录。

## 核心链路

```
展会名录 / 企业官网 / 公开目录
        ↓ 采集（gen_urls → crawl_pages）
线索表（公司 · 国家 · 官网 · 公开商务邮箱）
        ↓ 清洗 · 去重 · 邮箱验证（extract_leads → clean_leads → verify_emails）
有效线索
        ↓ AI 写信（draft_mail，按对方业务定制开头）
开发信
        ↓ 小批量发送（send_mails · 限速 · 带退订 · 默认空跑）
回复记录 → 跟进 → 复盘
```

## 技术架构

| 层 | 位置 | 职责 |
|---|---|---|
| 入口层 | `server.py`、`config.py` | HTTP 接口与静态托管；全项目唯一配置槽 |
| 智能体层 | `lead_agent/Agents/` | Supervisor 规则路由；Flow / Collect / Extract / Outreach 业务智能体 |
| 工具层 | `lead_agent/tools/` | `@register(roles=[...])` 注册，运行时按角色领取，不写死在类里 |
| 记忆层 | `lead_agent/memory/` | 短期会话窗口 + 长期条目 + L0/L1/L2 权限门 |
| 底座层 | `lead_agent/core/` | 分派、感知、认知（ReAct）、约束、反思、遥测、输出、注册表 |

依赖方向单向：入口 → Agents → tools / memory → core，不允许反向 import。

**路由规则**：Supervisor 用正则规则路由（不发 LLM、不持工具），命中全流程 → 采集 → 抽取 → 开发信，默认落到采集。模型调用只在业务智能体内发生。

**工具调用四道闸**：权限（`plan` / `auto` / `readonly`）→ 路径（不得越出 `TOOL_PATH_ROOTS`）→ 网络（`deny` / 白名单 / 放行）→ 危险写确认；再叠加单会话工具预算 `MAX_TOOL_CALLS`。

**降级策略**：未配置 `LLM_API_KEY` 时不报错，自动走各智能体的 `classic_*_reply` 规则兜底，界面与调试链路照常可用。

## 目录结构

完整说明见 [struct.md](struct.md)。

```
第二组_AI爬虫自动化获客/
├── server.py            # FastAPI 入口 + 托管 ui/
├── config.py            # 配置槽（路径 / 模型 / 权限 / 预算）
├── .env.example         # 环境变量样例（不含真实 Key）
├── requirements.txt
├── README.md / 开发文档.md / struct.md / CHANGELOG.md
├── ui/                  # 深色单页：对话 / 采集 / 线索 / 开发信 / 调试 / 配置
│   ├── index.html
│   ├── app.js
│   └── style.css
├── lead_agent/
│   ├── Agents/          # supervisor + 四个业务智能体 + 基类 + 总结
│   ├── tools/           # document / collect / extract / verify / outreach / catalog
│   ├── memory/          # 短期、长期、权限门、总装配
│   └── core/            # dispatch / perception / cognition / constraint / reflection / telemetry / output / toolkit
├── data/                # 记忆、遥测、上传、线索 CSV、抓取日志（运行时生成）
├── raw/                 # 抓回的原始 HTML
└── dist/                # 打包输出
```

## 快速开始

要求 Python 3.11+。

```bash
pip install -r requirements.txt
copy .env.example .env      # Windows；macOS/Linux 用 cp
uvicorn server:app --reload --port 8000
```

打开 http://127.0.0.1:8000 即可使用界面。

`.env` 至少填这两项才会真正调用模型，其余可留空：

```ini
LLM_API_KEY=sk-xxxx
LLM_MODEL=deepseek-chat
```

`LLM_BASE_URL` 支持任意 OpenAI 兼容接口（DeepSeek / 通义 / 自建代理）。留空 `LLM_API_KEY` 则全部走 classic 兜底，不联网。

## 界面说明

| 标签 | 作用 |
|---|---|
| 对话 | 与主控对话，显示路由结果、智能体、工具调用步骤与耗时 |
| 采集 | 填写站点基址与分页规则，生成待抓 URL；上传 csv/txt/md 线索表 |
| 线索 | 查看 raw / clean 线索与邮箱验证状态 |
| 开发信 | 生成与预览开发信正文 |
| 调试 | 最近一次调用的时间、耗时、智能体、模型、工具次数、会话 ID；逐步 trace 表（工具 / 状态 / 耗时 / 参数与结果）；遥测尾部日志与原始 JSON |
| 配置 | 模型接入（模型 ID / API Key / 自定义接口地址）、约束与预算、界面偏好；写回 `.env` |

API Key 只写不读：界面显示「已配置」，输入框留空表示不修改，保存时不会清空已有 Key。

## 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/ask` | `{text, session_id}` → 回答 + trace + 时间 / 耗时 / 模型 / 工具数 |
| GET | `/api/stats` | 线索数、抓取状态分布、发信统计 |
| GET | `/api/leads` | 线索列表（`limit`） |
| POST | `/api/upload` | 上传线索表（csv / txt / md） |
| GET / POST | `/api/config` | 读取配置 / 写回 `.env` 白名单键 |
| GET | `/api/debug/tail` | 遥测尾部日志（`n`） |

## 配置项

| 变量 | 默认 | 说明 |
|---|---|---|
| `LLM_API_KEY` | 空 | 空则走 classic 兜底 |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI 兼容地址 |
| `LLM_MODEL` | `deepseek-chat` | 模型 ID |
| `LLM_TIMEOUT` | `60` | 单次请求超时（秒） |
| `AGENT_PERMISSION_MODE` | `plan` | 写类工具需 `confirm=true`；`auto` 免确认；`readonly` 只读 |
| `TOOL_NET_POLICY` | `allowlist` | `allowlist` 按域名白名单；`block` 禁网 |
| `TOOL_NET_ALLOWLIST` | 空 | 逗号分隔域名，留空时只校验协议 |
| `TOOL_PATH_ROOTS` | 项目根 | 工具可写路径根，多个用系统分隔符 |
| `MAX_TOOL_CALLS` | `12` | 单会话工具调用预算 |
| `REACT_MAX_ROUNDS` | `4` | 单次问答最多工具轮数 |
| `CONTEXT_CHAR_BUDGET` | `6000` | 上下文组装字符预算 |
| `DAILY_MAIL_LIMIT` | `50` | 每日发信上限 |
| `DRY_RUN_MAIL` | `true` | `true` 时只写发送日志，不真正外发 |

## 数据源原则

- 只用**公开可查**的第三方来源：展会参展商名录、企业自有官网、公开 B2B 目录、Google Places API、行业协会名录。
- 不抓取 LinkedIn / 阿里国际站 / 亚马逊等平台数据，不登录、不绕验证码。
- 只采集公司层面的商务联系方式（info@ / sales@ / contact@），不采集个人隐私信息。
- 每条线索保留**来源 URL + 抓取时间**，便于溯源与答辩举证。
- 遵守目标站点 robots.txt 与条款，限速 ≤ 1 次/秒，并发 ≤ 2。

## 阶段目标

1. **采集**：选定 1–2 个公开名录，抓取 100–300 条初始线索。
2. **清洗**：去重 + 邮箱验证，保留 60–100 条有效线索。
3. **写信**：AI 生成中英双版开发信，人工抽检。
4. **触达**：每日 ≤ 50 封，带退订链接，记录打开与回复。
5. **复盘**：统计回复率，沉淀有效话术。

## 底线

- 不做全自动无人值守群发。
- 不发未经邮箱验证的地址。
- 不使用未配置 SPF/DKIM/DMARC 的域名发信。

## 现状与限制

- 采集链路已具备「生成 URL → 抓取 → 入库」的工具，但目标源站尚未固定，尚未跑真实批量采集。
- 发信默认 `DRY_RUN_MAIL=true`，只落日志；真实外发需自备发信服务与域名配置。
- `plan` 模式下写类工具需要显式 `confirm=true`，避免模型误触。

## 修改记录

见 [CHANGELOG.md](CHANGELOG.md)。
