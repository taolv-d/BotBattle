# BotBattle 测试指南

## 当前目录结构

```text
tests/
├── __init__.py
├── README.md
├── common/
│   ├── __init__.py
│   └── test_api.py                  # LLM API 连接测试
├── werewolf/
│   ├── __init__.py
│   └── test_seer_revealed.py        # 预言家信息暴露相关测试
├── threekingdoms/
│   └── __init__.py
└── test_game_review.py              # 复盘服务测试
```

仓库根目录下还有若干历史测试/验证脚本，例如：

- `test_connection.py`
- `test_threekingdoms_fixes.py`

## 运行测试

### API 连接测试

```bash
python tests/common/test_api.py
```

前提条件：

- 已配置 `config/system.json`
- API Key 有效

### 狼人杀相关测试

```bash
pytest tests/werewolf/test_seer_revealed.py
```

### 复盘服务测试

```bash
pytest tests/test_game_review.py
```

### 运行游戏进行手动验证

狼人杀：

```bash
python werewolf_main.py
```

三国杀：

```bash
python threekingdoms.py
```

## 测试说明

| 测试文件 | 用途 | API 依赖 |
|---------|------|---------|
| `tests/common/test_api.py` | 测试 LLM API 连接 | ✅ |
| `tests/werewolf/test_seer_revealed.py` | 验证预言家在不同阶段的信息呈现 | 视测试实现而定 |
| `tests/test_game_review.py` | 验证复盘与漏洞检测流程 | 通常需要 mock 或可用 LLM 配置 |

## 新增测试建议

- 公共测试放在 `tests/common/test_*.py`
- 狼人杀测试放在 `tests/werewolf/test_*.py`
- 三国杀测试放在 `tests/threekingdoms/test_*.py`
- 跨模块集成测试可直接放在 `tests/test_*.py`

## 注意事项

1. API 相关测试需要正确配置 `config/system.json`
2. 狼人杀主入口为 `werewolf_main.py`
3. 部分异步测试需要使用 `pytest` 及相应插件环境
