"""
relevance_engine.py — Relevance scoring and filtering

Scores each raw event 0–100 based on:
  - Geographic proximity  (30 pts)
  - Impact severity       (30 pts)
  - Urgency / recency     (20 pts)
  - User interest match   (20 pts)

Thresholds (configurable in config.json):
  ≥ 80  → 高优先级 (immediate alert)
  50–79 → 中优先级 (daily digest)
  < 50  → 低优先级 (archived / ignored)
"""

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from data_collector import RawEvent


@dataclass
class ScoredEvent:
    raw: RawEvent
    score: int               # 0–100
    level: str               # 高 / 中 / 低
    impact: str              # why it matters to you
    suggestion: str          # recommended action


# ─── Keyword signal tables ────────────────────────────────────────────────────

_HIGH_IMPACT_KEYWORDS = [
    "暴雨", "暴雪", "台风", "龙卷", "地震", "洪水", "预警", "紧急",
    "封路", "断路", "停电", "爆炸", "火灾", "事故", "伤亡",
    "限购", "降价", "崩盘", "暴涨",
]

_MEDIUM_IMPACT_KEYWORDS = [
    "施工", "整修", "改建", "拆迁", "新政", "调整", "规划",
    "限行", "绕行", "延误", "雾霾", "污染",
    "上涨", "下跌", "均价", "成交",
]

_SOURCE_BASE_SCORES = {
    "weather": 15,
    "traffic": 15,
    "news":    10,
    "housing": 10,
    "social":   8,
}

_INTEREST_SOURCE_MAP = {
    "housing":     ["housing"],
    "traffic":     ["traffic"],
    "safety":      ["news", "social"],
    "environment": ["weather"],
    "commerce":    ["news", "housing"],
    "community":   ["social", "news"],
}


# ─── Scoring components ───────────────────────────────────────────────────────

def _geo_score(event: RawEvent, user_lat: float, user_lon: float, radius_km: float) -> int:
    """0–30 pts. Max score if distance ≤ 0.5 km, scales down to 0 at radius."""
    if event.lat is None or event.lon is None:
        return 12  # no location → assume city-level relevance

    dist = _haversine(user_lat, user_lon, event.lat, event.lon)
    if dist <= 0.5:
        return 30
    if dist >= radius_km:
        return 0
    # Linear decay between 0.5 km and radius
    return int(30 * (1 - (dist - 0.5) / (radius_km - 0.5)))


def _impact_score(event: RawEvent) -> int:
    """0–30 pts based on keyword signals in title + description."""
    text = (event.title + " " + event.description).lower()
    for kw in _HIGH_IMPACT_KEYWORDS:
        if kw in text:
            return 30
    for kw in _MEDIUM_IMPACT_KEYWORDS:
        if kw in text:
            return 18
    return 8  # baseline


def _urgency_score(event: RawEvent) -> int:
    """0–20 pts. More recent = higher score."""
    try:
        ts = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    except Exception:
        return 10

    if age_hours < 1:
        return 20
    if age_hours < 6:
        return 15
    if age_hours < 24:
        return 10
    if age_hours < 72:
        return 5
    return 2


def _interest_score(event: RawEvent, interests: dict) -> int:
    """0–20 pts based on user's declared interest weights."""
    best = 0.0
    for interest, weight in interests.items():
        sources = _INTEREST_SOURCE_MAP.get(interest, [])
        if event.source in sources:
            best = max(best, weight)
    return int(best * 20)


def _haversine(lat1, lon1, lat2, lon2) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ─── Impact & suggestion text generation ─────────────────────────────────────

def _build_impact(event: RawEvent, score: int, dist_label: str) -> str:
    source_impacts = {
        "weather": "影响出行、健康及户外活动",
        "traffic": f"影响通勤路线{dist_label}",
        "news":    "可能影响政策、生活成本或公共安全",
        "housing": "直接影响资产价值或租房成本",
        "social":  "邻里社区动态，影响日常生活",
    }
    base = source_impacts.get(event.source, "与你的日常生活相关")
    if score >= 80:
        return f"⚠️ 高度相关：{base}"
    if score >= 50:
        return f"📌 值得关注：{base}"
    return f"ℹ️ 一般参考：{base}"


def _build_suggestion(event: RawEvent, score: int) -> str:
    title = event.title
    if "施工" in title or "封路" in title or "限行" in title:
        return "建议提前规划替代路线，预留额外通勤时间"
    if any(w in title for w in ["暴雨", "暴雪", "台风", "预警"]):
        return "减少外出，备好雨具，关注官方预警更新"
    if "空气" in title and "差" in title:
        return "建议佩戴口罩，减少户外剧烈运动"
    if "房价" in title or "均价" in title:
        return "可结合近期趋势评估买卖/续租时机"
    if "新政" in title or "政策" in title:
        return "建议阅读全文，评估对自身的具体影响"
    if score >= 80:
        return "建议立即关注，必要时采取行动"
    if score >= 50:
        return "纳入近期关注事项"
    return "可选择性了解"


# ─── Main scoring pipeline ────────────────────────────────────────────────────

def score_events(events: list[RawEvent], config: dict) -> list[ScoredEvent]:
    loc = config["location"]
    interests = config.get("interests", {})
    thresholds = config.get("thresholds", {"immediate_alert": 80, "daily_digest": 50})
    radius_km = loc.get("radius_km", 5)

    scored = []
    for event in events:
        geo  = _geo_score(event, loc["lat"], loc["lon"], radius_km)
        imp  = _impact_score(event)
        urg  = _urgency_score(event)
        inte = _interest_score(event, interests)
        raw_score = geo + imp + urg + inte
        score = min(100, raw_score)

        if score >= thresholds["immediate_alert"]:
            level = "高"
        elif score >= thresholds["daily_digest"]:
            level = "中"
        else:
            level = "低"

        # Distance label for impact text
        if event.lat and event.lon:
            d = _haversine(loc["lat"], loc["lon"], event.lat, event.lon)
            dist_label = f"（约 {d:.1f} km）"
        else:
            dist_label = ""

        scored.append(ScoredEvent(
            raw=event,
            score=score,
            level=level,
            impact=_build_impact(event, score, dist_label),
            suggestion=_build_suggestion(event, score),
        ))

    # Sort by score descending
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored


def filter_by_level(scored: list[ScoredEvent], min_level: str = "中") -> list[ScoredEvent]:
    """Return only 高 and (optionally) 中 priority events."""
    include = {"高", "中"} if min_level == "中" else {"高"}
    return [e for e in scored if e.level in include]
