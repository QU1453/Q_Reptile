# 修改记录（倒序）

## 2026-11-19 · 深色交互界面（调试 + 配置）

- 重写 `ui/`：深色主题，六个标签（对话/采集/线索/开发信/调试/配置）。
- 调试页：耗时、trace 表格（参数与结果可展开）、原始响应 JSON、遥测尾 30 条。
- 配置页：`.env` 八键白名单读写、界面偏好（自动刷新/回车发送/默认页）、会话重置。
- `server.py` 新增 `GET/POST /api/config`、`GET /api/debug/tail`；API Key 只报是否已配置。

## 2026-11-19 · 按 Quote_Agent 架构重构

- 新增 `lead_agent/` 顶层包：Agents（Supervisor + 5 个智能体）、tools（10 个工具）、memory（短期/长期/权限）、core（dispatch/perception/cognition/constraint/reflection/telemetry/output/toolkit）。
- 新增 `server.py`（/api/ask、/api/stats、/api/leads、/api/upload、托管 ui/）与 `ui/` 单页看板。
- 新增 `config.py` 统一配置槽；`.env.example` 追加 LLM / 权限 / 网络 / 预算变量。
- 移植 `src/gen_urls.py` → `tools/collect.py`，`src/crawler.py` → `tools/collect.py`，`src/app.py` 的职责拆入 `server.py` 与 `lead_agent/`。
- 删除旧 `src/`、`config/settings.yaml`、`output/` 与各目录 `.gitkeep`（改为 `__init__.py`）。
- 新增 `struct.md`（结构 + 智能体架构）、本 `CHANGELOG.md`。
