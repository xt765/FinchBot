---
name: weather
description: 查询当前天气和天气预报（无需 API 密钥）。
homepage: https://open-meteo.com/
metadata: {"finchbot":{"emoji":"🌤️","requires":{"bins":["curl"]}}}
---

# 天气查询

使用 Open-Meteo 免费服务查询天气，无需 API 密钥。

## 当前天气
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia/Shanghai"
```

## 未来3天预报
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&daily=temperature_2m_max,temperature_2m_min,precipitation_probability&timezone=Asia/Shanghai&forecast_days=3"
```

## 小时级预报
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&hourly=temperature_2m,precipitation_probability&timezone=Asia/Shanghai&forecast_days=2"
```

## 可用参数
- `temperature_2m` - 温度（°C）
- `relative_humidity_2m` - 相对湿度（%）
- `wind_speed_10m` - 风速（km/h）
- `wind_direction_10m` - 风向（°）
- `precipitation_probability` - 降水概率（%）
- `weather_code` - WMO 天气代码
- `surface_pressure` - 气压（hPa）

## 常用城市坐标

| 城市 | 纬度 | 经度 |
|------|------|------|
| 北京 | 39.9 | 116.4 |
| 上海 | 31.2 | 121.5 |
| 广州 | 23.1 | 113.3 |
| 深圳 | 22.5 | 114.1 |
| 香港 | 22.3 | 114.2 |
| 台北 | 25.0 | 121.5 |
| 东京 | 35.7 | 139.7 |
| 纽约 | 40.7 | -74.0 |
| 伦敦 | 51.5 | -0.1 |

## WMO 天气代码

| 代码 | 天气 |
|------|------|
| 0 | 晴天 |
| 1-2 | 少云/部分多云 |
| 3 | 阴天 |
| 45-48 | 雾 |
| 51-57 | 毛毛雨 |
| 61-67 | 雨 |
| 71-77 | 雪 |
| 80-82 | 阵雨 |
| 95-99 | 雷暴 |

文档：https://open-meteo.com/en/docs
