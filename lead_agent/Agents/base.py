# -*- coding: utf-8 -*-
"""智能体公共基类：LLM 调用 / 记忆 / 工具守卫 / classic 兜底。

工具不写死在类里：按 self.role 向 GLOBAL_REGISTRY 领取。
每次工具调用前必须过约束层 check_tool_call，并消耗会话预算。
"""

from config import LLM_API_KEY
from lead_agent.core.cognition import run_react
from lead_agent.core.constraint.layer import check_budget, check_tool_call
from lead_agent.core.dispatch.registry import GLOBAL_REGISTRY
from lead_agent.core.output.formatter import build, error
from lead_agent.core.perception.context import build_context
from lead_agent.core.perception.input import clean_input
from lead_agent.core.perception.session import ensure_session
from lead_agent.core.reflection import reflect
from lead_agent.core.telemetry import live
from lead_agent.memory import MEMORY


class ReActAgentBase:
    """所有业务智能体的基类。"""

    role: str = ""
    system_prompt: str = "你是跨境获客项目的智能体，只处理公开商务信息相关任务。"

    def __init__(self, role: str | None = None):
        if role:
            self.role = role

    # ------------------------- 对外入口 -------------------------

    def ask(self, user_text: str, session_id: str | None = None) -> dict:
        """处理一次用户输入，返回 {answer, trace, agent}。"""
        text = clean_input(user_text)
        sid = ensure_session(session_id)
        if not text:
            return build("请输入要处理的内容。", [], self.role)

        trace: list[dict] = []
        answer = ""

        if LLM_API_KEY:
            try:
                memory_text = MEMORY.recall(sid, text)
                context_text = build_context(
                    self.system_prompt,
                    self._rules(),
                    memory_text,
                    text,
                )
                result = run_react(
                    role=self.role,
                    user_text=text,
                    tools=self.tools(),
                    execute=lambda name, args: self._execute_tool(name, args, sid),
                    context_text=context_text,
                    system_extra=self._tool_contract(),
                )
                answer = result.get("answer", "")
                trace = result.get("trace", [])
            except Exception as exc:  # noqa: BLE001  模型不可用 → classic 兜底
                live.log("llm_error", agent=self.role, error=str(exc)[:300])
                answer = ""

        if not answer:
            try:
                answer, trace = self._classic(text, sid)
            except Exception as exc:  # noqa: BLE001
                live.log("classic_error", agent=self.role, error=str(exc)[:300])
                return error(str(exc), self.role)

        MEMORY.remember(sid, text, answer, agent=self.role)
        check = reflect(answer, trace)
        live.think(check["note"], agent=self.role, session=sid)
        return build(answer, trace, self.role)

    # ------------------------- 工具 -------------------------

    def tools(self) -> dict[str, dict]:
        return GLOBAL_REGISTRY.tools_for(self.role)

    def use(self, name: str, args: dict | None, sid: str, trace: list[dict]):
        """执行一个工具并把结果记入 trace。"""
        ok, payload = self._execute_tool(name, args or {}, sid)
        trace.append(
            {
                "round": len(trace) + 1,
                "action": name,
                "args": args or {},
                "ok": ok,
                "result": str(payload)[:1200],
            }
        )
        return ok, payload

    def _execute_tool(self, name: str, args: dict, session_id: str) -> tuple[bool, dict]:
        tool = GLOBAL_REGISTRY.get(name)
        if tool is None:
            payload = {"error": f"未知工具：{name}"}
            live.tool(name, args, False, payload, session=session_id)
            return False, payload

        ok, reason = check_tool_call(name, args)
        if not ok:
            payload = {"error": reason}
            live.tool(name, args, False, payload, session=session_id, stage="constraint")
            return False, payload

        ok, reason = check_budget(session_id)
        if not ok:
            payload = {"error": reason}
            live.tool(name, args, False, payload, session=session_id, stage="budget")
            return False, payload

        try:
            result = tool["func"](**args)
        except TypeError as exc:
            payload = {"error": f"参数不匹配：{exc}"}
            live.tool(name, args, False, payload, session=session_id)
            return False, payload
        except Exception as exc:  # noqa: BLE001  工具异常回填给模型/兜底
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            live.tool(name, args, False, payload, session=session_id)
            return False, payload

        live.tool(name, args, True, result, session=session_id)
        return True, result

    # ------------------------- 兜底 -------------------------

    def _classic(self, text: str, sid: str) -> tuple[str, list[dict]]:
        fn = getattr(self, f"classic_{self.role}_reply", None)
        if fn is None:
            return "当前智能体没有配置兜底逻辑。", []
        return fn(text, sid)

    def _rules(self) -> str:
        from lead_agent.core.constraint.rules import DEAD_RULES

        return DEAD_RULES

    def _tool_contract(self) -> str:
        """把工具清单再以纯文本形式给模型一份。"""
        items = self.tools()
        if not items:
            return "当前角色没有可用工具，请直接用 final 回答。"
        lines = [f"- {name}：{info['description']}" for name, info in items.items()]
        return "可用工具：\n" + "\n".join(lines)


__all__ = ["ReActAgentBase"]
