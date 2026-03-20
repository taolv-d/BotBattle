# 阿里云百炼（DashScope）配置指南

**日期**: 2026-03-20
**状态**: ✅ 已支持

---

## 一、快速开始

### 1. 获取 API Key

1. 访问 [阿里云百炼控制台](https://dashscope.console.aliyun.com/)
2. 登录阿里云账号
3. 进入「API-KEY 管理」页面
4. 创建新的 API Key

### 2. 配置 system.json

编辑 `config/system.json` 文件：

```json
{
  "llm": {
    "provider": "dashscope",
    "api_key": "YOUR_DASHSCOPE_KEY",
    "model": "qwen-plus",
    "base_url": "https://dashscope.aliyuncs.com/api/v1",
    "temperature": 0.7,
    "timeout": 120,
    "retry_count": 2,
    "retry_delay": 1
  }
}
```

---

## 二、支持模型

### 通义千问系列

| 模型 | 描述 | 适用场景 |
|------|------|----------|
| `qwen-turbo` | 速度快，成本低 | 简单对话、快速响应 |
| `qwen-plus` | 性能均衡（推荐） | 游戏 AI、复杂对话 |
| `qwen-max` | 最强性能 | 高难度推理、复杂任务 |
| `qwen-long` | 200K 超长上下文 | 长文本分析 |

### 模型选择建议

**狼人杀游戏推荐**: `qwen-plus` 或 `qwen-max`

- **qwen-plus**: 性价比高，适合日常游戏
- **qwen-max**: 逻辑推理更强，适合高质量对局

---

## 三、配置参数说明

### 必填参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `provider` | 固定为 `dashscope` | `"dashscope"` |
| `api_key` | 阿里云 API Key | `"sk-xxxxxxxx"` |
| `model` | 模型名称 | `"qwen-plus"` |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `base_url` | `https://dashscope.aliyuncs.com/api/v1` | API 端点 |
| `temperature` | `0.7` | 创造性（0-1，越高越随机） |
| `timeout` | `120` | 请求超时时间（秒） |
| `retry_count` | `2` | 重试次数 |
| `retry_delay` | `1` | 重试间隔（秒） |

---

## 四、价格参考

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

---

## 五、使用示例

### 5.1 运行游戏

```bash
cd /home/admin/project/BotBattle
venv/bin/python werewolf_main.py
```

### 5.2 验证配置

运行后会看到：

```
正在加载配置...
[OK] LLM 已配置：dashscope
[OK] 模型：qwen-plus
```

---

## 六、常见问题

### Q1: API Key 无效

**错误信息**: `DashScope API Key 无效`

**解决方法**:
1. 检查 API Key 是否正确复制（包含 `sk-` 前缀）
2. 确认 API Key 未过期
3. 检查阿里云账号余额

### Q2: 请求超时

**错误信息**: `DashScope 请求超时`

**解决方法**:
1. 检查网络连接
2. 增加 `timeout` 参数值
3. 如持续超时，考虑切换到 `qwen-turbo`

### Q3: 模型不可用

**错误信息**: `Model not found`

**解决方法**:
1. 确认模型名称正确
2. 检查该模型是否已开通服务
3. 查看 [模型列表](https://help.aliyun.com/zh/dashscope/models)

---

## 七、与其他提供商对比

| 特性 | DeepSeek | DashScope（通义） | OpenAI |
|------|----------|-------------------|--------|
| 价格 | 低 | 中 | 高 |
| 速度 | 中 | 快 | 中 |
| 中文能力 | 强 | 强 | 中 |
| 推理能力 | 强 | 强 | 强 |
| 国内访问 | ✅ | ✅ | ❌ |

**推荐场景**:
- **DeepSeek**: 性价比高，适合日常使用
- **DashScope**: 国内访问稳定，模型选择多
- **OpenAI**: 海外用户，需要 GPT-4 能力

---

## 八、代码实现

### 核心类

```python
class DashScopeLLM(BaseLLMProvider):
    """阿里云百炼 LLM 实现"""
    
    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "qwen-plus")
        self.base_url = config.get("base_url", "https://dashscope.aliyuncs.com/api/v1")
        # ... 其他参数
```

### API 调用

```python
# 请求格式
payload = {
    "model": self.model,
    "input": {
        "messages": [{"role": "user", "content": prompt}]
    },
    "parameters": {
        "temperature": self.temperature,
        "max_tokens": 2000,
    }
}

# API 端点
url = f"{self.base_url}/services/aigc/text-generation/generation"
```

---

## 九、相关资源

- [阿里云百炼官网](https://www.aliyun.com/product/dashscope)
- [API 文档](https://help.aliyun.com/zh/dashscope/)
- [模型列表](https://help.aliyun.com/zh/dashscope/models)
- [定价说明](https://help.aliyun.com/zh/dashscope/pricing)

---

**更新时间**: 2026-03-20
