# 项目结构 · 智能体架构（AI 爬虫自动化获客）

> 本文件同时是「文件结构 + 架构说明」，改动目录或工具归属时同步更新。
> 参考分层来自 Quote_Agent，业务内容替换为跨境获客。

## 一、文件结构

```
第二组_AI爬虫自动化获客/
├── server.py                # FastAPI 入口：/api/ask、/api/stats、/api/leads、/api/upload、/api/config、/api/debug/tail、托管 ui/
├── config.py                # 全局配置槽：Key/模型/预算/权限/路径根/网络策略
├── .env.example             # 环境变量样例（不含真实 Key）
├── requirements.txt
├── README.md / 开发文档.md   # 原作业文档，内容不动
├── ui/
│   ├── index.html           # 深色单页：对话/采集/线索/开发信/调试/配置 六个标签
│   ├── app.js               # 原生 fetch；trace 表格、原始 JSON、遥测、.env 读写、本地偏好
│   └── style.css            # 深色主题（#0b0f14 底 + #4d9aff 强调），响应式
├── lead_agent/              # 唯一顶层包
│   ├── Agents/
│   │   ├── supervisor.py    # 主控：规则路由（不发 LLM、不持工具）
│   │   ├── base.py          # ReActAgentBase：LLM 调用 / 记忆 / 工具守卫 / classic 兜底
│   │   ├── flow_agent.py    # 全流程
│   │   ├── collect_agent.py # 采集
│   │   ├── extract_agent.py # 抽取与清洗
│   │   ├── outreach_agent.py# 开发信与发送
│   │   ├── summarizer.py    # 总结
│   │   └── __init__.py      # 门面（PEP 562 懒导出）
│   ├── tools/
│   │   ├── document.py      # parse_document
│   │   ├── collect.py       # gen_urls / crawl_pages / crawl_status
│   │   ├── extract.py       # extract_leads / clean_leads / query_leads
│   │   ├── verify.py        # verify_emails
│   │   ├── outreach.py      # draft_mail / send_mails / mail_stats
│   │   ├── catalog.py       # 线索库 CSV 读写（内部函数，不注册为工具）
│   │   └── __init__.py      # 门面 re-export（导入即注册）
│   ├── memory/
│   │   ├── short_term/__init__.py  # 会话窗口（jsonl 追加）
│   │   ├── long_term/__init__.py   # 长期条目（jsonl 追加 + 关键词检索）
│   │   ├── access.py               # L0/L1/L2 权限门
│   │   ├── manager.py              # remember / recall 总装配
│   │   └── __init__.py
│   └── core/
│       ├── dispatch/
│       │   ├── registry.py   # TOOL_ROLES 文档表 + GLOBAL_REGISTRY.tools_for(role)
│       │   └── orchestrator.py
│       ├── perception/
│       │   ├── input.py      # 输入清洗
│       │   ├── session.py    # 会话识别
│       │   └── context.py    # 上下文组装（字符预算）
│       ├── cognition/react.py
│       ├── constraint/
│       │   ├── layer.py      # 四道检查入口
│       │   ├── validator.py  # 路径不越界
│       │   ├── budget.py     # 单会话工具预算
│       │   └── rules.py      # 死规则 + 工具分类
│       ├── reflection/__init__.py
│       ├── telemetry/live.py # 思考流 jsonl
│       ├── output/__init__.py + formatter.py
│       ├── toolkit/__init__.py + decorator.py（@register(roles=...)）
│       └── __init__.py
├── data/
│   ├── memory/              # short_term.jsonl / long_term.jsonl
│   ├── telemetry/           # live.jsonl
│   ├── uploads/             # 上传的 csv/txt/md
│   ├── leads/               # leads_raw.csv / leads_clean.csv / send_log.csv
│   └── crawl/crawl_log.jsonl
├── raw/                     # 抓回的 HTML
├── dist/                    # 打包输出
├── CHANGELOG.md
└── struct.md
```

## 二、全局分层

1. **入口层**：`server.py`（HTTP/静态资源）、`config.py`（唯一配置槽）。
2. **智能体层**：`lead_agent/Agents/`，Supervisor 只做规则路由，业务智能体继承 `ReActAgentBase`。
3. **工具层**：`lead_agent/tools/`，全部通过 `@register(roles=[...])` 登记，运行时按角色领取。
4. **记忆层**：`lead_agent/memory/`，短期窗口 + 长期条目 + 权限门 + 总装配。
5. **底座层**：`lead_agent/core/`，分派、感知、认知、约束、反思、遥测、输出、工具注册。
6. **数据层**：`data/`（可写）、`raw/`（抓取原文）、`dist/`（打包）。

依赖方向单向：入口 → Agents → tools/memory → core，不允许反向 import Agents。

## 三、智能体清单

| 智能体 | 类 | role | 兜底函数 | 职责 |
|---|---|---|---|---|
| 主控 | Supervisor | 不发 LLM | — | 按正则规则路由 |
| 全流程 | FlowAgent | flow | classic_flow_reply | 采集→抽取→清洗→写信 |
| 采集 | CollectAgent | collect | classic_collect_reply | 生成 URL、批量抓取、查状态 |
| 抽取 | ExtractAgent | extract | classic_extract_reply | 结构化抽取、去重清洗、邮箱验证 |
| 触达 | OutreachAgent | outreach | classic_outreach_reply | 写开发信、限速发送、看回复 |
| 总结 | SummarizerAgent | 无工具 | classic_summarizer_reply | 汇总批次结果 |

## 四、路由优先级

Supervisor._route 按下列顺序匹配，先命中者生效，全不中默认 `collect`：

| 顺序 | 角色 | 正则 |
|---|---|---|
| 1 | flow | `全流程\|一条龙\|端到端\|走一遍\|从采集到` |
| 2 | collect | `采集\|爬\|抓取\|URL\|链接\|名录` |
| 3 | extract | `抽取\|清洗\|去重\|验证\|邮箱\|线索` |
| 4 | outreach | `开发信\|写信\|邮件\|发送\|回复率` |
| 5 | collect（默认） | — |

## 五、工具 ↔ 角色矩阵

`*` = 全部业务角色。真正生效的归属由装饰器写入 `REGISTRY`；
`registry.py` 的 `TOOL_ROLES` 仅作本表镜像，供核对。

| 工具 | flow | collect | extract | outreach |
|---|---|---|---|---|
| document.parse_document | ✓ | ✓ | ✓ | ✓ |
| collect.gen_urls | ✓ | ✓ | | |
| collect.crawl_pages | ✓ | ✓ | | |
| collect.crawl_status | ✓ | ✓ | | |
| extract.extract_leads | ✓ | | ✓ | |
| extract.clean_leads | ✓ | | ✓ | |
| extract.query_leads | ✓ | | ✓ | ✓ |
| verify.verify_emails | ✓ | | ✓ | |
| outreach.draft_mail | ✓ | | | ✓ |
| outreach.send_mails | ✓ | | | ✓ |
| outreach.mail_stats | ✓ | | | ✓ |

## 六、记忆分层

- **短期记忆** L：`data/memory/short_term.jsonl`，按 session_id 过滤，取最近 N 条。
- **长期记忆**：`data/memory/long_term.jsonl`，写文本 + 标签，按关键词（含中文二元组）打分检索。
- **权限门**：`access.check(level, project_id)`；L0 公开读 / L1 项目读 / L2 写与外发。
- **总装配**：`manager.MEMORY.remember / recall`，把摘要交给 `context.build_context`。

## 七、一次问答链路

1. `POST /api/ask` → `Orchestrator.handle` 生成/校验 session_id，写遥测 request。
2. `Supervisor._route` 正则命中角色 → 实例化对应 Agent。
3. Agent.ask：清洗输入 → 取记忆 → 组装四段上下文 → 有 Key 走 `core/cognition/react.py`。
4. ReAct：模型返回 `{"action","args"}` 或 `{"final"}`；最多 4 轮。
5. 每次工具调用 → `constraint.layer.check_tool_call`（四道）→ `budget.consume` → 执行 → 遥测。
6. 模型不可用/异常 → 子类 `classic_*_reply` 兜底（同样过四道检查）。
7. `formatter.build` → `{answer, trace, agent}`；写短期/长期记忆与反思结论；返回前端。

## 八、约束层四道检查

| 顺序 | 文件 | 内容 | 拒绝示例 |
|---|---|---|---|
| 1 权限 | `memory/access.py` | L2 写/外发；readonly 模式仅 L0 | readonly 下调用 send_mails |
| 2 路径 | `constraint/validator.py` | 参数路径不得含 `..`、不得逃出 TOOL_PATH_ROOTS | `D:/其它目录/x.csv` |
| 3 网络 | `constraint/layer.py` | block 全禁；allowlist 校验协议与域名 | 非 http(s)、域名不在白名单 |
| 4 危险写 | `constraint/layer.py` | plan 模式下 crawl_pages / send_mails 需 `confirm=true` | 未带 confirm 的 send_mails |

预算：`constraint/budget.py` 限制单会话 12 次工具调用（`MAX_TOOL_CALLS`）。

## 九、新增东西的改动点

**新增工具**：
1. 在 `lead_agent/tools/` 对应模块写函数并加 `@register(roles=[...], name="模块.函数")`；
2. `tools/__init__.py` re-export；
3. 同步 `core/dispatch/registry.py` 的 `TOOL_ROLES` 与本文第五节矩阵；
4. 若涉及网络/写盘，加入 `constraint/rules.py` 的 `NET_TOOLS` / `WRITE_TOOLS` / `DANGEROUS_WRITE`。

**新增智能体**：
1. `Agents/` 新建 `xxx_agent.py`，继承 `ReActAgentBase`，设置 `role`、`system_prompt`、`classic_xxx_reply`；
2. `Agents/__init__.py` 的 `_EXPORTS` 增加懒导出；
3. `supervisor.py` 的 `ROUTE_RULES` 与 `_agent()` 增加路由（注意顺序即优先级）；
4. 更新本文第三、四节。

**新增接口**：`server.py` 加路由 → 复用 tools 层函数，不在接口里写业务逻辑。

**新增数据文件**：先在 `config.py` 的 `PATHS` 注册路径，再用 `catalog.py` 的读写函数访问。

## 十、界面面板（ui/）

深色单页，六个标签，纯原生 JS，无构建步骤。

| 标签 | 内容 | 用到的接口 |
|---|---|---|
| 对话 | 消息流 + 工具步骤条 + 输入框 | `POST /api/ask` |
| 采集 | 采集计数、URL 生成表单、最近失败 | `/api/stats`、`/api/ask` |
| 线索 | 原始/清洗/已发计数 + 线索表 + 上传 | `/api/stats`、`/api/leads`、`/api/upload` |
| 开发信 | 发送/回复/回复率 + 信件预览 | `/api/stats`、`/api/ask` |
| 调试 | 本次耗时、trace 表格（参数/结果可展开）、原始响应 JSON、遥测尾 30 条 | `/api/ask`、`/api/debug/tail` |
| 配置 | `.env` 白名单读写、界面偏好、会话 ID 重置 | `/api/config` |

- **配置写回**：仅 `ENV_WRITABLE` 八个键可写，其余忽略；`LLM_API_KEY` 只回传「是否已配置」，不经界面读写；保存后需重启服务。
- **界面偏好**（自动刷新间隔、回车发送、默认展开原始 JSON、默认起止页）存 `localStorage`，不影响后端。
- **调试判定**：`trace` 每项含 `round/action/args/ok/result`，失败项标红；`route` 为首条，表示 Supervisor 选中了哪个角色。
