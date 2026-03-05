# BotBattle 部署指南

## 快速部署

### 1. 克隆项目

```bash
git clone <repository-url>
cd BotBattle
```

### 2. 配置 API Key

**方法一：复制示例文件**
```bash
cp config/system.example.json config/system.json
```

**方法二：手动创建**
编辑 `config/system.json`，填入你的 API Key：

```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "sk-your-actual-api-key",
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

## 配置说明

### system.json 配置项

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `provider` | LLM 提供商 | deepseek |
| `api_key` | API 密钥（必填） | - |
| `model` | 模型名称 | deepseek-chat |
| `base_url` | API 地址 | https://api.deepseek.com/v1 |
| `temperature` | 温度（0-1） | 0.7 |
| `timeout` | 超时时间（秒） | 180 |
| `retry_count` | 重试次数 | 5 |
| `retry_delay` | 重试间隔（秒） | 3 |

### 推荐配置

**DeepSeek（性价比高）**
```json
{
  "provider": "deepseek",
  "model": "deepseek-chat",
  "temperature": 0.7,
  "timeout": 180
}
```

**Kimi（速度快）**
```json
{
  "provider": "kimi",
  "model": "moonshot-v1-8k",
  "temperature": 0.7,
  "timeout": 60
}
```

**通义千问（国内稳定）**
```json
{
  "provider": "aliyun",
  "model": "qwen-turbo",
  "temperature": 0.7,
  "timeout": 60
}
```

## 常见问题

### 1. API 连接失败

**检查网络：**
```bash
ping api.deepseek.com
```

**检查 API Key：**
```bash
python test_api.py
```

**使用国内 API：**
切换到 Kimi 或通义千问（见上方推荐配置）

### 2. 配置文件不存在

确保 `config/system.json` 存在：
```bash
ls config/
```

如果不存在，复制示例文件：
```bash
cp config/system.example.json config/system.json
```

### 3. 依赖安装失败

**升级 pip：**
```bash
python -m pip install --upgrade pip
```

**使用国内镜像：**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 目录结构

```
BotBattle/
├── config/
│   ├── system.json          # 系统配置（需自行填写 API Key）
│   ├── system.example.json  # 配置示例
│   ├── werewolf_default.json # 游戏配置
│   └── personalities.json   # 人格库
├── logs/                    # 游戏日志（自动创建）
├── main.py                  # 主程序
├── test_api.py              # API 测试
└── requirements.txt         # 依赖
```

## 安全提示

⚠️ **重要：**
- `config/system.json` 包含 API Key，请勿提交到 Git
- 项目已配置 `.gitignore` 自动忽略敏感文件
- 如需分享配置，请使用 `system.example.json`

## 更新日志

### v1.0.0
- 完整狼人杀流程
- 7 种 AI 人格
- 警长竞选、多轮发言、遗言环节
- 信任/怀疑列表系统
- 网络重试机制
