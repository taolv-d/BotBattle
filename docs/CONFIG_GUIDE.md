# BotBattle 配置指南

## 一、快速开始

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
    "provider": "dashscope",
    "api_key": "sk-your-actual-api-key",
    "model": "qwen-plus",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature": 0.7,
    "timeout": 180,
    "retry_count": 5,
    "retry_delay": 3
  }
}
```

## 二、API 提供商配置

### 2.1 DeepSeek（性价比高）
- **速度**: ⭐⭐⭐
- **价格**: ¥2/百万 tokens
- **地址**: https://platform.deepseek.com/
- **特点**: 性价比高，适合长文本

配置示例：
```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "YOUR_DEEPSEEK_KEY",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",
    "temperature": 0.7,
    "timeout": 180,
    "retry_count": 5,
    "retry_delay": 3
  }
}
```

### 2.2 Kimi（月之暗面）- 推荐 ⭐
- **速度**: ⭐⭐⭐⭐⭐
- **价格**: ¥0.008/千 tokens
- **地址**: https://platform.moonshot.cn/
- **特点**: 速度非常快，适合短文本对话

配置示例：
```json
{
  "llm": {
    "provider": "kimi",
    "api_key": "YOUR_KIMI_KEY",
    "model": "moonshot-v1-8k",
    "base_url": "https://api.moonshot.cn/v1",
    "temperature": 0.7,
    "timeout": 60,
    "retry_count": 2,
    "retry_delay": 1
  }
}
```

### 2.3 通义千问（阿里云百炼）- 推荐 ⭐
- **速度**: ⭐⭐⭐⭐
- **价格**: ¥0.008/千 tokens
- **地址**: https://dashscope.aliyun.com/
- **特点**: 国内稳定，速度快

#### 2.3.1 获取 API Key

1. 访问 [阿里云百炼控制台](https://dashscope.console.aliyun.com/)
2. 登录阿里云账号
3. 进入「API-KEY 管理」页面
4. 创建新的 API Key

#### 2.3.2 配置示例

```json
{
  "llm": {
    "provider": "dashscope",
    "api_key": "YOUR_DASHSCOPE_KEY",
    "model": "qwen-plus",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature": 0.7,
    "timeout": 120,
    "retry_count": 2,
    "retry_delay": 1
  }
}
```

#### 2.3.3 支持模型

| 模型 | 描述 | 适用场景 |
|------|------|----------|
| `qwen-turbo` | 速度快，成本低 | 简单对话、快速响应 |
| `qwen-plus` | 性能均衡（推荐） | 游戏 AI、复杂对话 |
| `qwen-max` | 最强性能 | 高难度推理、复杂任务 |
| `qwen-long` | 200K 超长上下文 | 长文本分析 |

**模型选择建议**:
- **狼人杀游戏推荐**: `qwen-plus` 或 `qwen-max`
  - **qwen-plus**: 性价比高，适合日常游戏
  - **qwen-max**: 逻辑推理更强，适合高质量对局

#### 2.3.4 价格参考

> 以下价格为参考，实际价格以阿里云官网为准

| 模型 | 输入价格 | 输出价格 |
|------|----------|----------|
| qwen-turbo | ¥0.002 / K tokens | ¥0.006 / K tokens |
| qwen-plus | ¥0.004 / K tokens | ¥0.012 / K tokens |
| qwen-max | ¥0.02 / K tokens | ¥0.06 / K tokens |

**一局狼人杀（9 人）成本估算**:
- qwen-turbo: ¥0.1 - ¥0.3
- qwen-plus: ¥0.2 - ¥0.6
- qwen-max: ¥1.0 - ¥3.0

### 2.4 Ollama（本地模型）- 免费
- **速度**: ⭐⭐⭐（取决于硬件）
- **价格**: 免费
- **地址**: https://ollama.ai/
- **特点**: 本地运行，无需 API Key

配置示例：
```json
{
  "llm": {
    "provider": "ollama",
    "api_key": "ollama",
    "model": "qwen2.5:7b",
    "base_url": "http://localhost:11434/v1",
    "temperature": 0.7,
    "timeout": 120,
    "retry_count": 2,
    "retry_delay": 1
  }
}
```

## 三、配置参数说明

### 3.1 必填参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `provider` | LLM 提供商 | `"dashscope"` |
| `api_key` | API Key | `"sk-xxxxxxxx"` |
| `model` | 模型名称 | `"qwen-plus"` |

### 3.2 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `base_url` | 取决于提供商 | API 端点 |
| `temperature` | `0.7` | 创造性（0-1，越高越随机） |
| `timeout` | `180` | 请求超时时间（秒） |
| `retry_count` | `5` | 重试次数 |
| `retry_delay` | `3` | 重试间隔（秒） |

## 四、快速切换 API

编辑 `config/system.json`，修改 `llm` 部分即可。

## 五、优化建议

### 5.1 如果 DeepSeek 速度慢：
1. 增加 `timeout` 到 120 秒
2. 减少 `retry_count` 到 1-2 次
3. 或切换到 Kimi/通义千问

### 5.2 如果频繁连接失败：
1. 检查网络连接
2. 确认 API Key 有效
3. 尝试使用代理
4. 切换到国内 API（Kimi/通义千问）

## 六、常见问题

### 6.1 API 连接失败

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

### 6.2 配置文件不存在

确保 `config/system.json` 存在：
```bash
ls config/
```

如果不存在，复制示例文件：
```bash
cp config/system.example.json config/system.json
```

### 6.3 API Key 无效

**错误信息**: `DashScope API Key 无效` 或类似错误

**解决方法**:
1. 检查 API Key 是否正确复制（包含相应前缀）
2. 确认 API Key 未过期
3. 检查阿里云账号余额

### 6.4 请求超时

**错误信息**: `请求超时` 或类似错误

**解决方法**:
1. 检查网络连接
2. 增加 `timeout` 参数值
3. 如持续超时，考虑切换到更快的模型

### 6.5 模型不可用

**错误信息**: `Model not found`

**解决方法**:
1. 确认模型名称正确
2. 检查该模型是否已开通服务
3. 查看 [模型列表](https://help.aliyun.com/zh/dashscope/models)

### 6.6 依赖安装失败

**升级 pip：**
```bash
python -m pip install --upgrade pip
```

**使用国内镜像：**
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 七、提供商对比

| 特性 | DeepSeek | DashScope（通义） | Kimi | OpenAI | Ollama |
|------|----------|-------------------|------|--------|--------|
| 价格 | 低 | 中 | 低 | 高 | 免费 |
| 速度 | 中 | 快 | 很快 | 中 | 取决于硬件 |
| 中文能力 | 强 | 强 | 强 | 中 | 取决于模型 |
| 推理能力 | 强 | 强 | 强 | 强 | 取决于模型 |
| 国内访问 | ✅ | ✅ | ✅ | ❌ | ✅ |
| 本地运行 | ❌ | ❌ | ❌ | ❌ | ✅ |

**推荐场景**:
- **DeepSeek**: 性价比高，适合日常使用
- **DashScope**: 国内访问稳定，模型选择多
- **Kimi**: 速度快，适合短文本对话
- **OpenAI**: 海外用户，需要 GPT-4 能力
- **Ollama**: 本地运行，隐私要求高

## 八、测试 API 连接

```bash
python test_api.py
```

或运行游戏验证配置：
```bash
python werewolf_main.py
```

运行后会看到：
```
正在加载配置...
[OK] LLM 已配置：dashscope
[OK] 模型：qwen-plus
```

## 九、目录结构

```
BotBattle/
├── config/
│   ├── system.json          # 系统配置（需自行填写 API Key）
│   ├── system.example.json  # 配置示例
│   ├── werewolf_default.json # 游戏配置
│   └── personalities.json   # 人格库
├── logs/                    # 游戏日志（自动创建）
├── main.py                  # 主程序
├── werewolf_main.py         # 狼人杀主程序
├── test_api.py              # API 测试
└── requirements.txt         # 依赖
```

## 十、安全提示

⚠️ **重要：**
- `config/system.json` 包含 API Key，请勿提交到 Git
- 项目已配置 `.gitignore` 自动忽略敏感文件
- 如需分享配置，请使用 `system.example.json`