# -*- coding: utf-8 -*-
"""
集中管理 InfoSynapse 中用到的主要 Prompt 模板。
"""

from typing import List


def build_tab_helper_prompt(
    tab_key: str,
    role_hint: str,
    title: str,
    stage: str,
    interests: str,
    context: str,
    user_input: str,
) -> str:
    return f"""{role_hint}

当前页面：{title}
当前阶段：{stage or '未设置'}
用户兴趣标签：{interests or '未设置'}

本页上下文信息（系统整理）： 
{context or '（页面中有课程、导师、实践、社区等信息，用户正在浏览/思考中）'}

用户在本页补充的问题或情况：
{user_input or '（未补充）'}

请结合这些信息，给出与本页主题相关的一些建议和下一步行动方向。
要求：
1. 结构清晰，用 Markdown 标题/列表组织
2. 针对本页主题，给出 3-6 条具体行动建议（比如『优先选哪些课』『怎么联系导师』『先做哪个项目』）
3. 如果信息不足，也要说明「还需要补充什么信息」"""


def build_career_plan_prompt(
    careers_brief: str,
    interests: str,
    location: str,
    stage: str,
    extra: str,
) -> str:
    return f"""下面是系统根据你的兴趣和地区推荐的一些职业方向：
{careers_brief or '（目前还没有职业推荐）'}

你的兴趣标签：{interests or '未设置'}
目标地区：{location or '未设置'}
当前阶段：{stage or '未设置'}
你补充的信息：{extra or '（未补充）'}

请作为一名资深职业导师，给出一份清晰可执行的规划，要求：
1. 明确优先推荐的 1-2 个职业方向，并说明为什么（结合兴趣、地区、转岗难度、当前阶段）
2. 针对未来 3 个月，给出按时间分段的行动计划（第 1 个月 / 第 2 个月 / 第 3 个月）
3. 列出 3-5 条简历与项目积累的关键建议（越具体越好，例如『做一个 XXX 项目，练 YYY 能力』）
4. 提供一个「最小可行版本」计划，只保留 3-4 件必须做的事

请用 Markdown 标题和列表组织内容。
"""


def build_mixed_plan_prompt(
    brief_recs: str,
    interests: str,
    stage: str,
    extra: str,
) -> str:
    return f"""下面是根据你的兴趣标签『{interests or '未设置'}』生成的一些综合推荐（课程/实践/项目/导师等，最多 15 条）：
{brief_recs or '（目前还没有推荐项）'}

你当前阶段：{stage or '未设置'}
你补充的个人情况 / 目标：
{extra or '（未补充）'}

请基于这些推荐，给出一份「8~12 周」的行动计划，要求：
1. 分阶段：比如「第 1-4 周」「第 5-8 周」「第 9-12 周」，每个阶段列出要做的事情（可以引用上面的推荐项）
2. 每个阶段给一个可量化的目标
3. 提供一个「最小可行版本」计划，只保留 3-5 件最关键的事情
4. 注意三类平衡：课程学习、项目实践、求职/深造准备
5. 根据当前阶段调整节奏（例如大一偏基础，大三/大四偏求职）

请用 Markdown 结构化输出（使用标题 + 列表），不要空话，多给例子。
"""


def build_career_chat_prompt(
    careers_brief: str,
    interests: str,
    location: str,
    stage: str,
    history_text: str,
) -> str:
    return f"""你是一名资深职业规划顾问，需要用中文帮助一名学生做长期职业规划与短期行动安排。

学生基本情况：
- 兴趣标签：{interests or '未设置'}
- 目标地区：{location or '未设置'}
- 当前阶段：{stage or '未设置'}

系统根据学生情况推荐的职业方向示例：
{careers_brief or '（暂无职业推荐）'}

下面是你和学生之前的对话记录（按时间顺序）：
{history_text or '（暂无历史对话）'}

请你只针对「学生最后一条提问」进行回复，要求：
1. 不要重复之前已经说过的大段内容，可以在此基础上补充和细化
2. 回答尽量具体、可执行，避免空话套话
3. 适当提醒学生接下来 1-2 周可以做的事情
4. 如信息不足，可以说明你还需要哪些补充信息

请用 Markdown 列表或小标题组织你的回答。
"""