---
name: weather
description: 查询当前天气和天气预报（无需 API 密钥）。
homepage: https://open-meteo.com/
metadata: {"finchbot":{"emoji":"🌤️","requires":{"bins":["curl"]}}}
---

# 天气查询

使用免费服务查询天气，无需 API 密钥。

## 推荐服务：Open-Meteo

稳定可靠，响应快，数据详细，支持 JSON 格式。

### 当前天气
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=Asia/Shanghai"
```

### 未来3天预报
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&daily=temperature_2m_max,temperature_2m_min,precipitation_probability&timezone=Asia/Shanghai&forecast_days=3"
```

### 小时级预报
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&hourly=temperature_2m,precipitation_probability&timezone=Asia/Shanghai&forecast_days=2"
```

### 可用参数
- `temperature_2m` - 温度（°C）
- `relative_humidity_2m` - 相对湿度（%）
- `wind_speed_10m` - 风速（km/h）
- `wind_direction_10m` - 风向（°）
- `precipitation_probability` - 降水概率（%）
- `weather_code` - WMO 天气代码
- `surface_pressure` - 气压（hPa）

### 常用城市坐标

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

### WMO 天气代码

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

## 备选服务：wttr.in

适合快速查看天气，支持图片和月相。

> **注意**：
> - 使用英文城市名（Beijing 而非 北京），中文支持不稳定
> - 服务器响应较慢，需添加 `--connect-timeout 30` 参数
> - PNG 图片功能可能因网络问题失败

### 快速查询
```bash
curl -s --connect-timeout 30 "http://wttr.in/Beijing?format=3"
# 输出: Beijing: ⛅️ +1°C
```

### 详细格式
```bash
curl -s --connect-timeout 30 "http://wttr.in/Beijing?format=%l:+%c+%t+%h+%w"
# 输出: Beijing: ⛅️ +1°C 51% ↓6km/h
```

### 今日预报
```bash
curl -s --connect-timeout 30 "http://wttr.in/Beijing?1"
```

### 月相查询
```bash
curl -s --connect-timeout 30 "http://wttr.in/Beijing?format=%m"
# 输出: 🌒
```

### 机场代码
```bash
curl -s --connect-timeout 30 "http://wttr.in/JFK?format=3"
# 输出: JFK: 🌦 +4°C
```

### PNG 图片输出
```bash
curl -s --connect-timeout 30 "http://wttr.in/Beijing.png" -o "$WORKSPACE/weather/beijing.png"
```

> **重要**：图片文件保存到工作区的 `weather/` 子目录，路径格式：`$WORKSPACE/weather/{城市名}.png`

### 格式代码
- `%c` 天气状况（图标）
- `%t` 温度
- `%h` 湿度
- `%w` 风速
- `%l` 位置
- `%m` 月相

## 使用建议

1. **优先使用 Open-Meteo**：稳定可靠，响应快
2. **快速查询用 wttr.in**：输出直观，但需英文城市名
3. **程序调用用 Open-Meteo**：JSON 格式便于解析
