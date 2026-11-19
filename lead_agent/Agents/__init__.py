# -*- coding: utf-8 -*-
"""Agents 门面：PEP 562 懒导出，避免 import 时拉起整套依赖。"""

import importlib

_EXPORTS = {
    "ReActAgentBase": "base",
    "Supervisor": "supervisor",
    "FlowAgent": "flow_agent",
    "CollectAgent": "collect_agent",
    "ExtractAgent": "extract_agent",
    "OutreachAgent": "outreach_agent",
    "SummarizerAgent": "summarizer",
}

__all__ = list(_EXPORTS)


def __getattr__(name: str):
    module_name = _EXPORTS.get(name)
    if not module_name:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value  # 缓存，后续访问不再走 __getattr__
    return value


def __dir__():
    return sorted(list(globals()) + __all__)
