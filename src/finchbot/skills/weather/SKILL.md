---
name: weather
description: 查询当前天气和天气预报（无需 API 密钥）。
homepage: https://wttr.in/:help
metadata: {"finchbot":{"emoji":"🌤️","requires":{"bins":["curl"]}}}
---

# 天气查询

使用两个免费服务查询天气，无需 API 密钥。

## wttr.in（主要服务）

### 快速查询
```bash
curl -s "wttr.in/北京?format=3"
# 输出: 北京: ⛅️ +8°C
```

### 紧凑格式
```bash
curl -s "wttr.in/北京?format=%l:+%c+%t+%h+%w"
# 输出: 北京: ⛅️ +8°C 71% ↙5km/h
```

### 完整预报
```bash
curl -s "wttr.in/北京?T"
```

### 格式代码
- `%c` 天气状况
- `%t` 温度
- `%h` 湿度
- `%w` 风速
- `%l` 位置
- `%m` 月相

### 使用提示
- 空格需要 URL 编码：`wttr.in/New+York`
- 机场代码：`wttr.in/JFK`
- 单位：`?m`（公制）`?u`（英制）
- 仅今天：`?1` · 仅当前：`?0`
- PNG 图片：`curl -s "wttr.in/上海.png" -o /tmp/weather.png`

## Open-Meteo（备用服务，JSON 格式）

免费服务，无需密钥，适合程序调用：
```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=39.9&longitude=116.4&current_weather=true"
```

先找到城市的经纬度，然后查询。返回包含温度、风速、天气代码的 JSON。

文档：https://open-meteo.com/en/docs
