<div align="center">

# Anti-Spam 反垃圾/反刷屏

**AstrBot 插件** · 检测并拦截重复消息和刷屏行为，保护机器人不被滥用

[![License](https://img.shields.io/github/license/Je1ghtxyuN/astrbot_plugin_anti_spam?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/version-v1.0.0-blue?style=flat-square)](https://github.com/Je1ghtxyuN/astrbot_plugin_anti_spam/releases)
[![AstrBot](https://img.shields.io/badge/AstrBot-%3E%3D4.0.0-orange?style=flat-square)](https://github.com/Soulter/AstrBot)
[![Python](https://img.shields.io/badge/python-%3E%3D3.10-blue?style=flat-square)](https://www.python.org/)

</div>

---

## 功能特性

| 功能 | 说明 |
|------|------|
| 重复消息检测 | 在时间窗口内检测用户发送的相同文本消息，超过阈值触发冷却 |
| 刷屏检测 | 在时间窗口内检测用户发送的消息频率，超过阈值触发冷却 |
| 静默丢弃 | 冷却期间用户消息被完全丢弃，**不消耗任何 token** |
| 可配置警告 | 触发时可选择发送警告消息，或完全静默 |
| 自动清理 | 内存中的追踪数据定期自动清理，不会造成内存泄漏 |
| WebUI 配置 | 所有参数均可通过 AstrBot WebUI 界面调整 |

## 工作原理

```
用户消息
  │
  ▼
┌─────────────────────┐
│   冷却检查          │ ← 已在冷却中？静默丢弃，0 token 消耗
│   event.stop_event()│
└─────────┬───────────┘
          │ 未在冷却
          ▼
┌─────────────────────┐
│   刷屏检测          │ ← 窗口内消息数 ≥ 阈值？→ 触发冷却
│   (所有消息类型)     │
└─────────┬───────────┘
          │ 未触发
          ▼
┌─────────────────────┐
│   重复消息检测      │ ← 窗口内相同文本 ≥ 阈值？→ 触发冷却
│   (仅文本消息)       │
└─────────┬───────────┘
          │ 未触发
          ▼
      正常处理
    (传递给下一个 handler / LLM)
```

> [!IMPORTANT]
> **Token 保护机制**
>
> 本插件通过 `event.stop_event()` 阻断 AstrBot 事件管线，被拦截的消息**不会进入 LLM 上下文**，因此不会产生任何 token 消耗。
>
> 关于群聊中的非 @bot 消息：AstrBot 的 `WakingCheckStage` 会自动过滤掉未 @bot 的群聊消息，这些消息**天然不会触发 LLM 调用**。本插件在此基础上提供额外保护——即使用户通过 @bot 或唤醒词触发了 bot，如果检测到刷屏行为，消息仍会被阻断在 LLM 调用之前。

## 安装

### 方式一：通过 AstrBot WebUI 安装（推荐）

1. 打开 AstrBot WebUI → 插件管理
2. 搜索 `astrbot_plugin_anti_spam`
3. 点击安装

### 方式二：手动安装

```bash
# 进入 AstrBot 插件目录
cd /AstrBot/data/plugins

# 克隆仓库
git clone https://github.com/Je1ghtxyuN/astrbot_plugin_anti_spam.git

# 重启 AstrBot
docker restart astrbot
```

## 配置

所有参数均可通过 AstrBot WebUI 的插件配置页面调整，也可直接编辑 `data/config/astrbot_plugin_anti_spam_config.json`。

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `enabled` | bool | `true` | 是否启用反垃圾功能 |
| `duplicate_threshold` | int | `3` | 重复消息触发阈值（次） |
| `duplicate_window_seconds` | int | `10` | 重复消息检测窗口（秒） |
| `flood_threshold` | int | `5` | 刷屏触发阈值（条） |
| `flood_window_seconds` | int | `10` | 刷屏检测窗口（秒） |
| `cooldown_seconds` | int | `30` | 冷却时间（秒） |
| `warning_message` | string | `检测到刷屏行为，你的消息将被暂时忽略。` | 警告消息，留空则不发送 |

### 配置示例

**严格模式**（群聊防骚扰）：
```json
{
  "duplicate_threshold": 2,
  "duplicate_window_seconds": 5,
  "flood_threshold": 3,
  "flood_window_seconds": 5,
  "cooldown_seconds": 60
}
```

**宽松模式**（防止误伤）：
```json
{
  "duplicate_threshold": 5,
  "duplicate_window_seconds": 15,
  "flood_threshold": 8,
  "flood_window_seconds": 15,
  "cooldown_seconds": 15
}
```

## 支持平台

本插件通过 AstrBot 的统一事件系统工作，支持所有平台适配器：

| 平台 | 支持 |
|------|------|
| QQ (aiocqhttp) | Yes |
| Telegram | Yes |
| Discord | Yes |
| 企业微信 (WeCom) | Yes |
| 飞书 (Lark) | Yes |
| 钉钉 (DingTalk) | Yes |
| Slack | Yes |
| KOOK | Yes |

## FAQ

<details>
<summary>Q: 插件会影响正常消息处理吗？</summary>

不会。只有在检测到刷屏/重复消息时才会拦截。正常频率的消息不受任何影响。
</details>

<details>
<summary>Q: 冷却期间发送的消息会怎样？</summary>

完全静默丢弃。不会发送给 LLM，不会消耗 token，也不会发送任何回复（除非配置了 `warning_message`，此时仅在首次触发时发送一次警告）。
</details>

<details>
<summary>Q: 重启 AstrBot 后追踪数据会丢失吗？</summary>

是的。追踪数据存储在内存中，重启后会重置。这是设计如此——防止重启后立即触发旧的冷却状态。
</details>

<details>
<summary>Q: 图片、表情包等非文本消息会触发重复检测吗？</summary>

不会。重复检测仅针对文本消息。非文本消息（图片、表情包、语音等）只受刷屏频率检测的影响。
</details>

## 开发

```bash
# 克隆仓库
git clone https://github.com/Je1ghtxyuN/astrbot_plugin_anti_spam.git
cd astrbot_plugin_anti_spam

# 项目结构
.
├── main.py              # 插件主逻辑
├── metadata.yaml        # 插件元数据
├── _conf_schema.json    # 配置 Schema（WebUI 生成配置表单）
├── __init__.py          # Python 包标识（空文件）
└── README.md
```

## 许可证

[MIT License](LICENSE)

---

<div align="center">

如果这个插件帮到了你，给个 Star 吧

</div>
