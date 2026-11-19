# -*- coding: utf-8 -*-
"""orchestrator：一次请求的编排薄层。

职责只有两件：把输入交给 Supervisor，并把请求/响应写入思考流。
业务细节不放在这里，避免和 Agents 层重复。
"""

from lead_agent.core.perception.session import ensure_session
from lead_agent.core.telemetry import live


class Orchestrator:
    def __init__(self, supervisor):
        self.supervisor = supervisor

    def handle(self, text: str, session_id: str | None = None) -> dict:
        sid = ensure_session(session_id)
        live.log("request", session=sid, text=str(text)[:300])
        result = self.supervisor.ask(text, sid)
        live.log(
            "response",
            session=sid,
            agent=result.get("agent", ""),
            chars=len(result.get("answer", "")),
            tools=len(result.get("trace", [])),
        )
        return result


__all__ = ["Orchestrator"]
