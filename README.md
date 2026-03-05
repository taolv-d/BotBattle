# BotBattle - AI 狼人杀

🤖 AI 驱动的狼人杀游戏引擎，支持完整的游戏流程和智能 AI 发言。

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd BotBattle
```

### 2. 配置 API Key

复制示例配置文件：
```bash
cp config/system.example.json config/system.json
```

然后编辑 `config/system.json`，填入你的 API Key：
```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "YOUR_API_KEY",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1"
  }
}
```

**获取 API Key：**
- DeepSeek: https://platform.deepseek.com/
- Kimi: https://platform.moonshot.cn/
- 通义千问：https://dashscope.aliyun.com/

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 测试 API 连接

```bash
python test_api.py
```

### 5. 运行游戏

```bash
python main.py
```

详细部署说明请查看 [DEPLOY.md](DEPLOY.md)

## 已完成功能 ✅

### 游戏流程
- ✅ 完整狼人杀规则（9 人标准局）
- ✅ 警长竞选环节
- ✅ 多轮发言（每轮 2 轮）
- ✅ 投票前辩论（显示怀疑/信任列表）
- ✅ 遗言环节
- ✅ 夜晚行动（狼人刀人、预言家查验、女巫用药）
- ✅ 猎人技能（死后可以带人）
- ✅ 女巫技能（解药 + 毒药）

### AI 功能
- ✅ 大模型驱动发言
- ✅ 7 种人格（真诚、爱撒谎、笑面虎、高冷、啰嗦、激进、佛系）
- ✅ 隐藏任务系统
- ✅ 记忆系统（记住之前的发言）
- ✅ 信任/怀疑列表（根据发言自动更新）
- ✅ 内心独白（写入日志）
- ✅ 发言长度控制（根据人格）

### 技术特性
- ✅ 网络重试机制（5 次重试，3 秒间隔）
- ✅ 超时保护（180 秒超时）
- ✅ 日志记录（JSON 格式）
- ✅ UI 接口抽象（方便扩展 Web）
- ✅ 配置化设计（易扩展其他游戏）

## 游戏配置

### 标准 9 人局（默认）
- 狼人 ×3
- 村民 ×3
- 预言家 ×1
- 女巫 ×1
- 猎人 ×1

### 人格系统

| 人格 | 特点 | 发言长度 |
|------|------|----------|
| 真诚 | 诚实正直 | 30-80 字 |
| 爱撒谎 | 擅长欺骗 | 40-120 字 |
| 笑面虎 | 表面友好 | 35-100 字 |
| 高冷 | 话少简洁 | 10-40 字 |
| 啰嗦 | 话多分析 | 60-200 字 |
| 激进 | 强势带节奏 | 30-100 字 |
| 佛系 | 低调跟随 | 15-50 字 |

## 游戏日志

每局游戏自动生成日志文件，保存在 `logs/` 目录：
- 游戏全程记录
- AI 内心独白
- JSON 格式，方便回放分析

## 扩展其他游戏

本架构支持扩展其他轮流对话型游戏：
- 剧本杀
- 三国杀
- 阿瓦隆
- 血染钟楼

只需在 `games/` 目录下创建新游戏模块即可。

## 架构设计

```
BotBattle/
├── main.py              # 主入口
├── config_loader.py     # 配置加载
├── test_auto.py         # 自动测试
├── test_analyze.py      # 分析功能测试
├── config/
│   ├── system.json      # 系统配置
│   ├── werewolf_default.json  # 游戏配置
│   └── personalities.json # 人格库
├── core/
│   ├── state.py         # 游戏状态
│   └── game_engine.py   # 游戏引擎
├── ai/
│   ├── llm_client.py    # LLM 客户端
│   ├── personality.py   # 人格系统
│   └── agent.py         # AI 代理
├── ui/
│   ├── base.py          # UI 基类
│   └── cli.py           # 命令行实现
├── games/werewolf/      # 狼人杀模块
└── logs/                # 游戏日志
```

## 注意事项

1. **API 选择**：推荐使用 DeepSeek（性价比高）或 Kimi（速度快）
2. **网络连接**：如果频繁连接失败，检查网络或切换 API
3. **发言质量**：AI 发言质量取决于 LLM 模型，可调整 temperature 参数
4. **游戏平衡**：当前版本狼人胜率略高，后续会优化

## 故障排除

### API 连接失败
```bash
# 运行测试脚本
python test_api.py
```

### 检查配置
```json
{
  "api_key": "确保填写有效的 Key",
  "timeout": 180,
  "retry_count": 5
}
```

### 查看日志
```bash
# 最新的日志文件
ls -lt logs/ | head -1
```
