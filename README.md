# 本地情报雷达 · Local Intelligence Gazette

> 实时采集你周围发生的大小事，按相关性评分筛选，用 AI 生成报纸风格简报。

![界面预览](https://img.shields.io/badge/界面-复古像素报纸-8b1a1a?style=flat-square) ![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 功能概览

- **多源采集**：OpenWeather 天气 & 空气质量、NewsAPI 本地新闻、OpenStreetMap 施工路况
- **相关性评分**：地理距离 + 影响程度 + 时效性 + 个人兴趣，综合打分 0–100
- **AI 简报**：调用 DeepSeek API，以老派报纸编辑的语气生成中文情报摘要
- **复古报纸界面**：纯 HTML，无需框架，支持历史地址记忆、API Key 本地持久化
- **网络时间校准**：从 worldtimeapi.org 同步真实时间，确保时效评分准确

---

## 快速开始

### 方式一：直接打开网页（推荐）

1. 用本地服务器打开 `index.html`（避免 CORS）：
   ```bash
   # Python
   python -m http.server 8080
   # 然后访问 http://localhost:8080
   ```
   或安装 VS Code 插件 **Live Server** 直接右键打开。

2. 在页面填写：
   - 详细地址（支持历史记录自动补全）
   - DeepSeek API Key（必填）
   - OpenWeather Key、NewsAPI Key（选填，不填则对应来源无数据）

3. 点击 **PRESS TO PRINT** 获取简报。

---

### 方式二：命令行运行

**安装依赖**

```bash
pip install -r requirements.txt
```

**配置 API Key**

编辑 `config.json`，或设置环境变量：

```bash
export DEEPSEEK_API_KEY=sk-xxxx
export OPENWEATHER_API_KEY=xxxx
export NEWSAPI_KEY=xxxx
```

**运行**

```bash
# 基本用法（使用 config.json 中的坐标）
python main.py

# 指定位置和半径
python main.py --lat 31.2304 --lon 121.4737 --radius 3

# 仅输出紧急事项
python main.py --mode alert

# 每日摘要（默认）
python main.py --mode digest

# 本周趋势
python main.py --mode weekly

# 输出原始 JSON
python main.py --json
```

---

## 获取 API Key

| 服务 | 用途 | 获取地址 | 是否必填 |
|------|------|----------|----------|
| DeepSeek | AI 摘要生成 | [platform.deepseek.com](https://platform.deepseek.com) | ★ 必填 |
| OpenWeather | 天气 & 空气质量 | [openweathermap.org/api](https://openweathermap.org/api) | 选填 |
| NewsAPI | 本地新闻 | [newsapi.org](https://newsapi.org) | 选填 |
| OpenStreetMap Overpass | 施工路况 | 免费，无需注册 | 自动 |

---

## 项目结构

```
.
├── index.html          # 复古报纸风格网页界面（独立运行，无需后端）
├── main.py             # 命令行入口，串联完整采集→评分→摘要流程
├── data_collector.py   # 多源数据采集（天气、新闻、路况、房产）
├── relevance_engine.py # 相关性评分引擎（地理×影响×时效×兴趣）
├── config.json         # 用户配置（坐标、半径、兴趣权重、API Key）
├── SKILL.md            # Claude Code skill 触发描述
└── requirements.txt    # Python 依赖
```

---

## 评分模型

每条事件的综合评分由四个维度构成，总分 0–100：

| 维度 | 权重 | 说明 |
|------|------|------|
| 地理距离 | 0–30 | ≤0.5km 满分，线性衰减至关注半径处归零 |
| 影响程度 | 0–30 | 高危关键词（暴雨/封路/火灾）30分，中等关键词18分，基础8分 |
| 时效性 | 0–20 | <1小时20分，<6小时15分，<24小时10分，<72小时5分，更早2分 |
| 兴趣匹配 | 0–20 | 用户偏好权重 × 20（可在界面滑块调整） |

评分阈值：
- **≥ 80** → 高优先级（立即提醒）
- **50–79** → 中优先级（每日摘要）
- **< 50** → 低优先级（过滤不显示）

---

## config.json 配置说明

```jsonc
{
  "location": {
    "lat": 39.9042,       // 纬度
    "lon": 116.4074,      // 经度
    "city": "Beijing",    // 城市（用于新闻搜索）
    "district": "Chaoyang",
    "radius_km": 5        // 关注半径（km）
  },
  "interests": {
    "housing": 0.9,       // 房产关注度 0–1
    "traffic": 0.8,       // 交通关注度
    "safety": 1.0,        // 安全关注度
    "environment": 0.7,   // 环境关注度
    "commerce": 0.5,      // 商业关注度
    "community": 0.6      // 社区关注度
  },
  "thresholds": {
    "immediate_alert": 80,
    "daily_digest": 50
  },
  "api_keys": {
    "openweather": "YOUR_OPENWEATHER_KEY",
    "newsapi": "YOUR_NEWSAPI_KEY",
    "deepseek": "YOUR_DEEPSEEK_KEY"
  }
}
```

---

## 注意事项

- **NewsAPI 免费版**仅支持英文关键词搜索，中文城市名（如 `Beijing`）效果更好
- **Overpass API** 有速率限制，频繁请求可能临时返回 429
- DeepSeek 前端直连可能遇到 **CORS**，建议通过本地服务器访问 `index.html` 而非直接双击打开
- `config.json` 中的 API Key **不要提交到公开仓库**（已在 `.gitignore` 中排除）

---

## License

MIT
