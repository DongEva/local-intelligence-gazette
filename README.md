# Local Intelligence Gazette · 本地情报雷达

**Your personal AI-powered local news agency — built around the places you actually care about.**

Pin your home, your office, or anywhere else. Set the radius. Get a curated intelligence briefing — daily digest, weekly roundup, or instant alerts — tailored entirely to your patch of the world.

> *The most important news in the world? What's happening right outside your door.*

**你专属的 AI 本地新闻社 —— 以你关心的地方为中心运转。**

定位你家、公司、或任何你在意的地点，控制关注的区域范围，让 AI 为你输出专属的本地情报 —— 日报、周报、即时预警，只关于你的那一片地方。

> *世界上最重要的新闻？就是你家门口正在发生的事。*

![UI](https://img.shields.io/badge/UI-Retro%20Pixel%20Newspaper-8b1a1a?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## The Idea

We scroll through global headlines every day — wars, elections, markets — yet somehow miss the road closure that's about to add 20 minutes to our morning commute, or the new policy that affects our rent, or the air quality warning we should have seen before heading out for a run.

**People care most about what's closest to them.** That's just human nature.

This project started from a simple question: *what if there was a tool that treated your neighborhood as the center of the news universe?* Not the world, not the country — just the 5-kilometer radius around where you actually live, filtered by what actually matters to you.

So that's what this is. A local intelligence radar. It watches your area, scores events by how much they affect your daily life, and delivers them as a crisp AI-generated briefing — styled like an old newspaper, because good local reporting deserves that kind of dignity.

---

## What It Does

- **Multi-source collection** — real-time data from OpenWeather (weather & air quality), NewsAPI (local headlines), and OpenStreetMap Overpass (road construction & closures)
- **Relevance scoring** — every event is scored 0–100 across four dimensions: geographic distance, impact severity, recency, and your personal interest weights
- **AI briefing** — DeepSeek API generates a concise summary in the voice of an old-school newspaper editor
- **Retro newspaper UI** — a self-contained HTML page, no frameworks, with address history memory and local API key persistence
- **Network time sync** — pulls real time from worldtimeapi.org so recency scores are always accurate

---

## Quick Start

### Option 1: Open the webpage (recommended)

Serve it locally to avoid CORS issues:

```bash
python -m http.server 8080
# then open http://localhost:8080
```

Or use the VS Code **Live Server** extension — right-click `index.html` → Open with Live Server.

Fill in:
- Your address (supports autocomplete from history)
- DeepSeek API Key *(required)*
- OpenWeather Key, NewsAPI Key *(optional — sources without a key simply won't appear)*

Hit **PRESS TO PRINT**.

---

### Option 2: Command line

```bash
pip install -r requirements.txt
```

Set your keys via environment variables or edit `config.json`:

```bash
export DEEPSEEK_API_KEY=sk-xxxx
export OPENWEATHER_API_KEY=xxxx
export NEWSAPI_KEY=xxxx
```

```bash
python main.py                                        # daily digest at your configured location
python main.py --lat 31.2304 --lon 121.4737 --radius 3
python main.py --mode alert                           # urgent items only
python main.py --mode weekly                          # weekly trend analysis
python main.py --json                                 # raw JSON output
```

---

## API Keys

| Service | Purpose | Get it at | Required |
|---------|---------|-----------|----------|
| DeepSeek | AI summary generation | [platform.deepseek.com](https://platform.deepseek.com) | ★ Yes |
| OpenWeather | Weather & air quality | [openweathermap.org/api](https://openweathermap.org/api) | Optional |
| NewsAPI | Local news headlines | [newsapi.org](https://newsapi.org) | Optional |
| OpenStreetMap Overpass | Road construction | Free, no signup | Auto |

---

## Project Structure

```
.
├── index.html           # Retro newspaper UI (standalone, no backend needed)
├── main.py              # CLI entry point — collect → score → summarize
├── data_collector.py    # Multi-source data fetching
├── relevance_engine.py  # Relevance scoring engine
├── config.json          # Your location, interests, and API keys (gitignored)
├── config.example.json  # Safe template to copy from
├── SKILL.md             # Claude Code skill trigger descriptor
└── requirements.txt     # Python dependencies
```

---

## Scoring Model

Each event is scored across four dimensions (total 0–100):

| Dimension | Weight | Logic |
|-----------|--------|-------|
| Geographic distance | 0–30 | Full score within 0.5 km, linear decay to zero at your set radius |
| Impact severity | 0–30 | High-risk keywords (storm / road closure / fire) = 30, medium = 18, baseline = 8 |
| Recency | 0–20 | <1h = 20, <6h = 15, <24h = 10, <72h = 5, older = 2 |
| Interest match | 0–20 | Your preference weight × 20 (adjustable via sliders) |

Thresholds:
- **≥ 80** → High priority (immediate alert)
- **50–79** → Medium priority (daily digest)
- **< 50** → Filtered out

---

## Notes

- **NewsAPI free tier** works better with English city names (e.g. `Beijing` not `北京`)
- **Overpass API** has rate limits — too many requests may return 429 temporarily
- **DeepSeek direct calls** from the browser may hit CORS; use a local server instead of opening `index.html` directly as a file
- `config.json` is gitignored — your API keys stay local

---

## Work in Progress

This project is under active development. A lot is still missing or rough around the edges.

Planned improvements include:

- **Richer search** — web search integration so the AI can actively look up events rather than relying only on pre-fetched API data
- **More data sources** — social platforms, government announcements, local forums, real estate feeds
- **Housing data** — real price and listing data (currently placeholder only)
- **Better geocoding** — smarter address parsing for non-Chinese cities
- **Notification support** — push alerts when a high-priority event appears
- **Scheduled runs** — automatic daily/weekly digest without manual trigger

Contributions and ideas are welcome.

---

## 这个项目的起点

我们每天刷全球新闻——战争、选举、股市——但往往不知道明天早上那条路要封，不知道刚出台的政策会不会影响自己的租房，也没有看到出门跑步前那条空气质量预警。

**人最关心的，其实还是自己身边的事。** 这是人之常情。

这个项目从一个简单的问题出发：*如果有一个工具，把你家附近的5公里当作新闻的中心，会怎样？* 不是全世界，不是全国，就是你真实生活的那个半径，按照和你的关联程度筛选过滤。

于是就有了这个东西。一个本地情报雷达。它盯着你的周边，给每条事件打一个"和你生活有多相关"的分，然后用 AI 整理成一份简报——做成老式报纸的样子，因为好的本地信息值得被认真对待。

## 功能概览

- **多源采集**：OpenWeather 天气 & 空气质量、NewsAPI 本地新闻、OpenStreetMap 施工路况
- **相关性评分**：地理距离 + 影响程度 + 时效性 + 个人兴趣，综合打分 0–100
- **AI 简报**：调用 DeepSeek API，以老派报纸编辑的语气生成情报摘要
- **复古报纸界面**：纯 HTML，无需框架，支持历史地址记忆、API Key 本地持久化
- **网络时间校准**：从 worldtimeapi.org 同步真实时间，确保时效评分准确

## 快速开始

### 方式一：打开网页（推荐）

用本地服务器打开 `index.html`（避免 CORS）：

```bash
python -m http.server 8080
# 然后访问 http://localhost:8080
```

或安装 VS Code 插件 **Live Server** 直接右键打开。

填写地址、DeepSeek Key，点击 **PRESS TO PRINT**。

### 方式二：命令行

```bash
pip install -r requirements.txt

export DEEPSEEK_API_KEY=sk-xxxx
export OPENWEATHER_API_KEY=xxxx
export NEWSAPI_KEY=xxxx

python main.py
python main.py --lat 31.2304 --lon 121.4737 --radius 3
python main.py --mode alert    # 仅紧急事项
python main.py --mode weekly   # 本周趋势
```

## 评分模型

| 维度 | 权重 | 说明 |
|------|------|------|
| 地理距离 | 0–30 | ≤0.5km 满分，线性衰减至关注半径处归零 |
| 影响程度 | 0–30 | 高危关键词 30分，中等 18分，基础 8分 |
| 时效性 | 0–20 | <1小时 20分，依次递减，3天以上 2分 |
| 兴趣匹配 | 0–20 | 用户偏好权重 × 20（界面滑块调整） |

评分 ≥80 立即提醒，50–79 每日摘要，<50 过滤不显示。

## 注意事项

- NewsAPI 免费版建议用英文城市名（如 `Beijing`）
- Overpass API 有速率限制，频繁请求可能临时 429
- DeepSeek 前端直连可能遇到 CORS，建议本地服务器访问
- `config.json` 已在 `.gitignore` 中排除，API Key 不会上传

## 仍在完善中

这个项目还在持续迭代，很多能力还没有做到位。

计划补充的内容包括：

- **搜索能力** — 接入网络搜索，让 AI 能主动查找事件，而不只依赖预设 API 的数据
- **更多数据源** — 社交平台、政府公告、本地论坛、房产平台实时数据
- **房产数据** — 目前仅为占位符，后续接入真实挂牌和成交数据
- **更智能的地址解析** — 对非中文城市的支持
- **推送提醒** — 出现高优先级事件时主动通知
- **定时运行** — 不用手动触发，自动生成每日/每周简报

欢迎提 Issue 或 PR，也欢迎分享你的想法。

## License

MIT
