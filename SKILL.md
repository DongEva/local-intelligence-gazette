# What's Happening In My Area

A local life intelligence radar that collects nearby events and filters them by relevance to your life — only showing what actually matters to you.

## When to use this skill

Trigger this skill when the user asks:
- "What's happening near me / around me / in my area"
- "Any local news / nearby events / area updates"
- "Is there anything I should know about my neighborhood"
- "周围有什么大事小事" / "附近发生了什么" / "本地动态"
- Questions about nearby construction, traffic, weather warnings, housing prices, local incidents

## What this skill does

Runs the local intelligence pipeline:
1. **Collects** data from configured sources (news APIs, weather, traffic, social)
2. **Scores** each item by relevance (geographic proximity, financial impact, urgency, personal preferences)
3. **Filters** to high/medium relevance items only
4. **Summarizes** each item in a structured, actionable format
5. **Groups** by push mode: immediate alerts (score ≥ 80), daily digest (50–79), weekly trends (< 50)

## How to invoke

Read `main.py` and run the skill with the user's location and preferences from `config.json`.

```python
python main.py
```

Or for a specific location:
```python
python main.py --lat 39.9042 --lon 116.4074 --radius 5
```

## Output format

Each item is structured as:
- **title**: one-sentence summary
- **impact**: why it matters to you
- **level**: 高/中/低
- **suggestion**: recommended action (if any)
- **score**: relevance score 0–100
- **source**: where the data came from

## Configuration

Edit `config.json` to set:
- Your home coordinates (`lat`, `lon`)
- Search radius in km (`radius_km`)
- Interest weights (housing, traffic, safety, environment)
- API keys for data sources
- Notification thresholds

Required API key: `deepseek` — get it from [platform.deepseek.com](https://platform.deepseek.com)

## Architecture

```
data_collector.py   → fetches raw data from multiple sources
relevance_engine.py → scores and filters by user relevance  
summarizer.py       → formats output into structured summaries
main.py             → orchestrates the pipeline, calls Claude API
config.json         → user preferences and API keys
```
