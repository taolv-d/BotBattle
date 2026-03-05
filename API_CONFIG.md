# API 配置指南

## 推荐的 API 提供商

### 1. DeepSeek（当前配置）
- **速度**: ⭐⭐⭐
- **价格**: ¥2/百万 tokens
- **地址**: https://platform.deepseek.com/
- **特点**: 性价比高，适合长文本

### 2. Kimi（月之暗面）- 推荐 ⭐
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

### 3. 通义千问（阿里云）
- **速度**: ⭐⭐⭐⭐
- **价格**: ¥0.008/千 tokens
- **地址**: https://dashscope.aliyun.com/
- **特点**: 国内稳定，速度快

配置示例：
```json
{
  "llm": {
    "provider": "aliyun",
    "api_key": "YOUR_DASHSCOPE_KEY",
    "model": "qwen-turbo",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "temperature": 0.7,
    "timeout": 60
  }
}
```

### 4. Ollama（本地模型）- 免费
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
    "timeout": 120
  }
}
```

## 快速切换 API

编辑 `config/system.json`，修改 `llm` 部分即可。

## 优化建议

### 如果 DeepSeek 速度慢：
1. 增加 `timeout` 到 120 秒
2. 减少 `retry_count` 到 1-2 次
3. 或切换到 Kimi/通义千问

### 如果频繁连接失败：
1. 检查网络连接
2. 确认 API Key 有效
3. 尝试使用代理
4. 切换到国内 API（Kimi/通义千问）

## 测试 API 连接

```bash
python test_api.py
```
