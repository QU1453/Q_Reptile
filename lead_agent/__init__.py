# -*- coding: utf-8 -*-
"""AI 爬虫自动化获客 · 唯一顶层包。

子包：
- Agents/  智能体（Supervisor 与四类业务智能体 + 总结）
- tools/   可被智能体调用的工具（采集 / 抽取 / 校验 / 触达 / 文档 / 线索库）
- memory/  短期与长期记忆
- core/    调度、感知、认知、约束、反思、遥测、输出、工具注册
"""

__all__ = ["Agents", "tools", "memory", "core"]
