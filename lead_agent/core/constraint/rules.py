# -*- coding: utf-8 -*-
"""死规则文本与工具分类常量（约束层与提示词共用）。"""

# 四道检查与提示词都会引用这段规则
DEAD_RULES = """1. 只处理公开可查的商务信息，不采集个人隐私，不登录、不绕验证码。
2. 不抓取 LinkedIn / 阿里国际站 / 亚马逊等平台数据。
3. 发信前必须做过邮箱验证，invalid 地址一律不发；每封信必须含退订说明。
4. 每日发信不超过上限，不做无人值守群发。
5. 所有回答注明使用了哪些工具与结果，不编造抓取到的字段。
6. 路径只能落在项目根内，禁止读写项目外目录。"""

# 需要联网的工具
NET_TOOLS = {"collect.crawl_pages"}

# 会写数据的工具（权限等级按 L2 处理）
WRITE_TOOLS = {
    "collect.gen_urls",
    "collect.crawl_pages",
    "extract.extract_leads",
    "extract.clean_leads",
    "outreach.send_mails",
}

# 「危险写操作」：plan 模式下必须显式 confirm=true
DANGEROUS_WRITE = {"collect.crawl_pages", "outreach.send_mails"}


__all__ = ["DEAD_RULES", "NET_TOOLS", "WRITE_TOOLS", "DANGEROUS_WRITE"]
