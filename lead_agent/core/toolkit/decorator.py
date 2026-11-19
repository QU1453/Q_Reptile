# -*- coding: utf-8 -*-
"""@register 装饰器：把工具函数登记到全局 REGISTRY。

这是工具归谁使用的**唯一事实来源**：智能体运行时只读这里，
`core/dispatch/registry.py` 里的 TOOL_ROLES 仅用于文档与人工核对。
"""

from typing import Callable, Iterable

# name -> {"name": str, "func": callable, "roles": list[str], "description": str}
REGISTRY: dict[str, dict] = {}


def describe(fn: Callable) -> str:
    """取 docstring 首行作为工具描述，供 LLM 选择工具时使用。"""
    doc = (fn.__doc__ or "").strip().splitlines()
    return doc[0].strip() if doc else fn.__name__


def register(roles: Iterable[str] | None = None, name: str | None = None):
    """登记一个工具函数。

    用法：
        @register(roles=["collect", "flow"], name="collect.gen_urls")
        def gen_urls(...): ...

    roles 中的 "*" 表示所有角色可用；name 缺省时用「模块名.函数名」。
    """

    role_list = list(roles or ["*"])

    def deco(fn: Callable) -> Callable:
        key = name or f"{fn.__module__.split('.')[-1]}.{fn.__name__}"
        old = REGISTRY.get(key)
        if old is not None and old["func"] is not fn:
            raise RuntimeError(f"工具名重复注册：{key}")
        REGISTRY[key] = {
            "name": key,
            "func": fn,
            "roles": role_list,
            "description": describe(fn),
        }
        return fn

    return deco
