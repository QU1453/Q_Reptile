# -*- coding: utf-8 -*-
"""认知层：简易 ReAct 循环。

模型每轮返回 JSON：
- {"action": "工具名", "args": {...}}  → 执行工具，把观察结果回填
- {"final": "最终回答"}               → 结束
最多 REACT_MAX_ROUNDS 轮，超出返回已有观察。
"""

import json
import re

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, REACT_MAX_ROUNDS

_JSON_RE = re.compile(r"\{.*\}", re.S)

_SYSTEM_TMPL = """你是「AI 爬虫自动化获客」项目的智能体，角色：{role}。
只能做公开商务信息相关的线索采集、清洗与触达辅助，不能编造抓取结果。

可用工具（名称：说明）：
{tools}

输出格式要求（严格遵守，只输出一个 JSON，不要 Markdown 代码块）：
- 需要调用工具时：{{"action": "工具名", "args": {{参数对象}}}}
- 可以结束回答时：{{"final": "给用户的中文回答"}}
一次只调用一个工具；拿到观察结果后再决定下一步。最多 {rounds} 轮。
"""


def _parse_json(text: str) -> dict | None:
    """从模型输出里抠出第一个 JSON 对象。"""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json", "", 1).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = _JSON_RE.search(text)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


def run(
    role: str,
    user_text: str,
    tools: dict[str, dict],
    execute,
    context_text: str = "",
    system_extra: str = "",
) -> dict:
    """执行 ReAct 循环；execute(name, args) 返回 (ok, payload)。"""
    from openai import OpenAI  # 延迟导入，未装 openai 时只影响此路径

    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL, timeout=LLM_TIMEOUT)
    tool_doc = "\n".join(f"- {name}：{item['description']}" for name, item in tools.items())
    if not tool_doc:
        tool_doc = "（当前角色没有可用工具）"

    system = _SYSTEM_TMPL.format(role=role, tools=tool_doc, rounds=REACT_MAX_ROUNDS)
    if system_extra:
        system += "\n" + system_extra
    if context_text:
        system += "\n\n【上下文】\n" + context_text

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_text},
    ]
    trace: list[dict] = []
    observations: list[str] = []

    for round_no in range(1, max(1, REACT_MAX_ROUNDS) + 1):
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=0.2,
        )
        content = (resp.choices[0].message.content or "").strip()
        data = _parse_json(content)

        if not data:
            return {"answer": content or "模型没有返回可解析内容", "trace": trace}

        if "final" in data:
            return {"answer": str(data.get("final") or ""), "trace": trace}

        action = str(data.get("action") or "").strip()
        args = data.get("args") or {}
        if not isinstance(args, dict):
            args = {}

        ok, payload = execute(action, args)
        try:
            payload_text = json.dumps(payload, ensure_ascii=False, default=str)
        except TypeError:
            payload_text = str(payload)
        trace.append(
            {
                "round": round_no,
                "action": action,
                "args": args,
                "ok": ok,
                "result": payload_text[:1200],
            }
        )
        observation = f"工具 {action} 返回：{payload_text[:1500]}"
        observations.append(observation)

        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": f"观察结果：{observation}\n请继续。"})

    answer = "已达到最大工具调用轮数，以下为已获得的观察结果：\n" + "\n".join(observations)
    return {"answer": answer, "trace": trace}


__all__ = ["run"]
