"""
data_collector.py — Multi-source local data collection

Fetches raw events from:
- OpenWeather API (weather alerts, air quality)
- NewsAPI (local news headlines)
- OpenStreetMap Overpass (nearby construction, road changes)
- Mock social/housing data (extend with real APIs as needed)
"""

import json
import math
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawEvent:
    source: str          # "weather" | "news" | "traffic" | "housing" | "social"
    title: str
    description: str
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    url: Optional[str] = None
    extra: dict = field(default_factory=dict)


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance in km between two points."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _get_json(url: str, timeout: int = 8) -> Optional[dict]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        print(f"  [fetch error] {url[:60]}... → {e}")
        return None


# ─── Weather ──────────────────────────────────────────────────────────────────

def fetch_weather(lat: float, lon: float, api_key: str) -> list[RawEvent]:
    if not api_key or api_key.startswith("YOUR_"):
        return _mock_weather(lat, lon)

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=zh_cn"
    )
    data = _get_json(url)
    if not data:
        return []

    events = []
    weather_desc = data.get("weather", [{}])[0].get("description", "")
    temp = data.get("main", {}).get("temp", "?")
    wind_speed = data.get("wind", {}).get("speed", 0)
    events.append(RawEvent(
        source="weather",
        title=f"当前天气：{weather_desc}，{temp}°C",
        description=f"风速 {wind_speed} m/s",
        lat=lat, lon=lon,
        extra={"temp": temp, "wind_speed": wind_speed, "desc": weather_desc}
    ))

    # Severe weather check
    if wind_speed > 10 or any(w in weather_desc for w in ["暴", "雷", "冰雹", "大雨", "大雪"]):
        events.append(RawEvent(
            source="weather",
            title=f"天气预警：{weather_desc}",
            description=f"风速 {wind_speed} m/s，注意出行安全",
            lat=lat, lon=lon,
            extra={"alert": True}
        ))

    # Air quality
    aq_url = (
        f"https://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}&lon={lon}&appid={api_key}"
    )
    aq = _get_json(aq_url)
    if aq:
        aqi = aq.get("list", [{}])[0].get("main", {}).get("aqi", 0)
        aqi_labels = {1: "优", 2: "良", 3: "中等", 4: "较差", 5: "很差"}
        label = aqi_labels.get(aqi, "未知")
        events.append(RawEvent(
            source="weather",
            title=f"空气质量：{label}（AQI={aqi}）",
            description="出行前请参考空气质量",
            lat=lat, lon=lon,
            extra={"aqi": aqi}
        ))

    return events


def _mock_weather(lat, lon) -> list[RawEvent]:
    return [
        RawEvent(source="weather", title="今日晴，气温18°C", description="适宜出行", lat=lat, lon=lon),
        RawEvent(source="weather", title="空气质量：良（AQI=2）", description="户外活动适宜", lat=lat, lon=lon),
    ]


# ─── News ─────────────────────────────────────────────────────────────────────

def fetch_news(city: str, api_key: str, max_items: int = 10) -> list[RawEvent]:
    if not api_key or api_key.startswith("YOUR_"):
        return _mock_news()

    q = urllib.parse.quote(city)
    url = (
        f"https://newsapi.org/v2/everything"
        f"?q={q}&sortBy=publishedAt&pageSize={max_items}&apiKey={api_key}"
    )
    data = _get_json(url)
    if not data:
        return []

    events = []
    for article in data.get("articles", []):
        events.append(RawEvent(
            source="news",
            title=article.get("title", ""),
            description=article.get("description", "") or "",
            timestamp=article.get("publishedAt", datetime.now().isoformat()),
            url=article.get("url"),
        ))
    return events


def _mock_news() -> list[RawEvent]:
    return [
        RawEvent(source="news", title="朝阳区地铁14号线延伸段将于下月开通", description="新增三个站点，预计缓解东部通勤压力"),
        RawEvent(source="news", title="本市出台新政策调整部分区域限购规则", description="符合条件家庭可申请豁免"),
        RawEvent(source="news", title="附近商业综合体计划改建，施工预计持续6个月", description="周边交通将受影响"),
    ]


# ─── Traffic / Construction via Overpass ──────────────────────────────────────

def fetch_traffic(lat: float, lon: float, radius_km: float) -> list[RawEvent]:
    radius_m = int(radius_km * 1000)
    # Query road construction tags within radius
    query = f"""
    [out:json][timeout:10];
    (
      way["construction"](around:{radius_m},{lat},{lon});
      way["highway"="construction"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    url = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    data = _get_json(url, timeout=12)

    events = []
    if data:
        for elem in data.get("elements", [])[:5]:  # cap at 5
            center = elem.get("center", {})
            tags = elem.get("tags", {})
            name = tags.get("name") or tags.get("highway") or "道路"
            c_lat = center.get("lat", lat)
            c_lon = center.get("lon", lon)
            dist = _haversine_km(lat, lon, c_lat, c_lon)
            events.append(RawEvent(
                source="traffic",
                title=f"施工区域：{name}（距你约 {dist:.1f} km）",
                description="道路施工，请注意绕行",
                lat=c_lat, lon=c_lon,
                extra={"distance_km": round(dist, 2), "tags": tags}
            ))

    if not events:
        events = _mock_traffic(lat, lon)
    return events


def _mock_traffic(lat, lon) -> list[RawEvent]:
    return [
        RawEvent(source="traffic", title="主干道施工：XX路（距你约0.8km）", description="预计封路至下月底，建议改走辅路", lat=lat, lon=lon, extra={"distance_km": 0.8}),
    ]


# ─── Housing (mock — extend with real estate API) ─────────────────────────────

def fetch_housing(city: str, district: str) -> list[RawEvent]:
    # Placeholder: replace with Lianjia/Beike API or scrapers
    return [
        RawEvent(
            source="housing",
            title=f"{district}区二手房均价本月环比上涨1.2%",
            description="挂牌量增加，成交周期缩短",
            extra={"change_pct": 1.2, "trend": "up"}
        ),
    ]


# ─── Main collector ───────────────────────────────────────────────────────────

def collect_all(config: dict) -> list[RawEvent]:
    loc = config["location"]
    keys = config.get("api_keys", {})

    print("📡 采集数据中...")
    events: list[RawEvent] = []

    print("  🌤 天气 & 空气质量")
    events += fetch_weather(loc["lat"], loc["lon"], keys.get("openweather", ""))

    print("  📰 本地新闻")
    events += fetch_news(loc.get("city", ""), keys.get("newsapi", ""))

    print("  🚧 交通 & 施工")
    events += fetch_traffic(loc["lat"], loc["lon"], loc.get("radius_km", 5))

    print("  🏠 房产动态")
    events += fetch_housing(loc.get("city", ""), loc.get("district", ""))

    print(f"  ✅ 共采集 {len(events)} 条原始数据")
    return events
