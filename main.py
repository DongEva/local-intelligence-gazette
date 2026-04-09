"""
main.py — "What's Happening In My Area" skill entry point

Orchestrates: data collection → relevance scoring → DeepSeek API summarization
Usage:
  python main.py
  python main.py --lat 39.9042 --lon 116.4074 --radius 5
  python main.py --mode digest   # force daily-digest output
  python main.py --mode alert    # only high-priority alerts
"""

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from data_collector import collect_all
from relevance_engine import ScoredEvent, score_events, filter_by_level


# ─── Config ───────────────────────────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config(overrides: dict = None) -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        cfg = json.load(f)

    # Allow API key from environment
    if os.environ.get("DEEPSEEK_API_KEY"):
        cfg["api_keys"]["deepseek"] = os.environ["DEEPSEEK_API_KEY"]
    if os.environ.get("OPENWEATHER_API_KEY"):
        cfg["api_keys"]["openweather"] = os.environ["OPENWEATHER_API_KEY"]
    if os.environ.get("NEWSAPI_KEY"):
        cfg["api_keys"]["newsapi"] = os.environ["NEWSAPI_KEY"]

    if overrides:
        if "lat" in overrides:
            cfg["location"]["lat"] = overrides["lat"]
        if "lon" in overrides:
            cfg["location"]["lon"] = overrides["lon"]
        if "radius" in overrides:
            cfg["location"]["radius_km"] = overrides["radius"]

    return cfg


# ─── Formatting ───────────────────────────────────────────────────────────────

def format_events_for_claude(events: list[ScoredEvent]) -> str:
    lines = []
    for i, e in enumerate(events, 1):
        lines.append(
            f"[{i}] {e.level}优先级 (score={e.score})\n"
            f"    标题: {e.raw.title}\n"
            f"    来源: {e.raw.source} | 时间: {e.raw.timestamp[:16]}\n"
            f"    描述: {e.raw.description or '(无)'}\n"
            f"    影响: {e.impact}\n"
            f"    建议: {e.suggestion}"
        )
    return "\n\n".join(lines)


def format_plain_output(events: list[ScoredEvent], lang: str = "zh") -> str:
    """Fallback output when Anthropic API key is not set."""
    high = [e for e in events if e.level == "高"]
    mid  = [e for e in events if e.level == "中"]

    parts = []
    if high:
        parts.append("🔴 高优先级（需立即关注）")
        for e in high:
            parts.append(f"\n  📌 {e.raw.title}")
            parts.append(f"     {e.impact}")
            parts.append(f"     建议：{e.suggestion}")

    if mid:
        parts.append("\n🟡 中优先级（今日关注）")
        for e in mid:
            parts.append(f"\n  📍 {e.raw.title}")
            parts.append(f"     {e.impact}")

    if not parts:
        parts.append("✅ 暂无需要特别关注的本地动态")

    return "\n".join(parts)


# ─── DeepSeek summarization ───────────────────────────────────────────────────

def summarize_with_deepseek(events: list[ScoredEvent], config: dict, mode: str) -> str:
    api_key = config["api_keys"].get("deepseek", "")
    if not api_key or api_key.startswith("YOUR_"):
        print("  ⚠️  未配置 DeepSeek API Key，使用基础格式输出")
        return format_plain_output(events, config.get("language", "zh"))

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    loc = config["location"]
    city = loc.get("city", "")
    district = loc.get("district", "")
    radius = loc.get("radius_km", 5)

    mode_instruction = {
        "alert":  "只输出需要立即处理的紧急事项，每条控制在2-3句话。",
        "digest": "输出完整的每日摘要，包含所有高/中优先级事项，适合早上阅读。",
        "weekly": "提炼本周趋势性信息，重点分析房价、治安、城市建设的变化方向。",
    }.get(mode, "输出结构清晰的情报摘要，让用户一目了然。")

    events_text = format_events_for_claude(events)

    prompt = f"""你是用户的本地生活情报助手。用户位于{city}{district}，关注半径{radius}km以内的动态。

以下是经过相关性过滤后的本地事件（共{len(events)}条）：

{events_text}

请按以下格式输出情报摘要：
{mode_instruction}

输出格式：
- 每条事件用一行简洁的标题（带emoji表情符号）
- 下方一句话说明"为什么和你有关"
- 如有需要行动的事项，附上"→ 建议：xxx"
- 最后加一行"今日总评"：用1-2句话概括整体情况

语言：中文，简洁自然，避免冗长。"""

    print("  🤖 调用 DeepSeek 生成情报摘要...")
    result_parts = []
    with client.chat.completions.create(
        model="deepseek-reasoner",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
        stream=True,
    ) as stream:
        for chunk in stream:
            delta = chunk.choices[0].delta
            # deepseek-reasoner streams reasoning_content then content
            text = getattr(delta, "content", None) or ""
            if text:
                result_parts.append(text)
                print(text, end="", flush=True)
    print()  # newline after streaming
    return "".join(result_parts)


# ─── Pipeline ─────────────────────────────────────────────────────────────────

def run(config: dict, mode: str = "digest") -> dict:
    # 1. Collect
    raw_events = collect_all(config)

    # 2. Score & filter
    print("\n🧠 计算相关性评分...")
    scored = score_events(raw_events, config)
    filtered = filter_by_level(scored, min_level="中")

    print(f"\n📊 评分结果：")
    print(f"   高优先级: {sum(1 for e in scored if e.level == '高')}")
    print(f"   中优先级: {sum(1 for e in scored if e.level == '中')}")
    print(f"   低优先级: {sum(1 for e in scored if e.level == '低')}")
    print(f"   → 推送 {len(filtered)} 条（高+中）\n")

    # 3. Summarize
    summary = summarize_with_deepseek(filtered, config, mode)

    # 4. Return structured output
    return {
        "mode": mode,
        "location": config["location"],
        "total_collected": len(raw_events),
        "shown": len(filtered),
        "summary": summary,
        "events": [
            {
                "title": e.raw.title,
                "source": e.raw.source,
                "score": e.score,
                "level": e.level,
                "impact": e.impact,
                "suggestion": e.suggestion,
                "timestamp": e.raw.timestamp,
            }
            for e in filtered
        ],
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="What's Happening In My Area")
    parser.add_argument("--lat", type=float, help="Latitude override")
    parser.add_argument("--lon", type=float, help="Longitude override")
    parser.add_argument("--radius", type=float, help="Search radius in km")
    parser.add_argument("--mode", choices=["alert", "digest", "weekly"], default="digest",
                        help="Output mode: alert (urgent only), digest (daily), weekly (trends)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON")
    args = parser.parse_args()

    overrides = {}
    if args.lat: overrides["lat"] = args.lat
    if args.lon: overrides["lon"] = args.lon
    if args.radius: overrides["radius"] = args.radius

    config = load_config(overrides)
    loc = config["location"]

    print(f"\n{'='*50}")
    print(f"📡 本地情报雷达")
    print(f"   位置: {loc.get('city', '')} {loc.get('district', '')} ({loc['lat']}, {loc['lon']})")
    print(f"   半径: {loc['radius_km']} km | 模式: {args.mode}")
    print(f"{'='*50}\n")

    result = run(config, mode=args.mode)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"\n{'='*50}")
        print("📋 情报摘要")
        print(f"{'='*50}")
        print(result["summary"])
        print(f"\n[共采集 {result['total_collected']} 条，推送 {result['shown']} 条]")


if __name__ == "__main__":
    main()
