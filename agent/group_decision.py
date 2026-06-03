"""Group decision skeleton for broad multi-person scenarios."""
from __future__ import annotations

import re
from typing import Any


GROUP_RE = r"朋友|同学|同事|女朋友|男朋友|家人|孩子|几个人|我们|聚会|四个人|4个人|三个人|3个人"


def build_group_decision(raw_text: str, intent_frame: dict[str, Any] | None = None) -> dict[str, Any]:
    raw_text = raw_text or ""
    frame = intent_frame or {}
    is_group = bool(re.search(GROUP_RE, raw_text))
    participants: list[str] = []
    for label in ["朋友", "同学", "同事", "女朋友", "男朋友", "家人", "孩子"]:
        if label in raw_text:
            participants.append(label)

    choice_cards: list[dict[str, Any]] = []
    if frame.get("next_action") == "show_category_choices":
        choice_cards = [
            {"category": "剧本杀", "why": "适合 4-6 人，互动强，需要确认本型和人数。"},
            {"category": "KTV", "why": "适合晚上，注意是否自驾、是否喝酒。"},
            {"category": "台球", "why": "轻松、预算低、时间灵活。"},
            {"category": "密室", "why": "刺激，但要确认是否有人怕恐怖。"},
            {"category": "电影", "why": "决策简单，但互动较弱。"},
            {"category": "桌游", "why": "轻松社交，适合预算较低。"},
        ]

    decision_mode = "ask_host"
    if choice_cards:
        decision_mode = "collect_votes" if is_group else "ask_host"
    if "位置不一样" in raw_text or "折中" in raw_text:
        decision_mode = "compromise_area"

    return {
        "is_group": is_group,
        "participants": participants,
        "known_preferences": _known_preferences(raw_text),
        "unknown_preferences": ["活动方向"] if choice_cards else [],
        "decision_mode": decision_mode,
        "choice_cards": choice_cards,
    }


def _known_preferences(text: str) -> list[str]:
    out: list[str] = []
    if "唱歌" in text:
        out.append("有人想唱歌")
    if "台球" in text:
        out.append("有人想打台球")
    if "不吃辣" in text:
        out.append("有人不吃辣")
    if "怕恐怖" in text:
        out.append("有人怕恐怖")
    return out
