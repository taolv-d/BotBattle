# BotBattle 测试指南

## 目录结构

```
tests/
├── __init__.py
├── README.md
├── common/              # 公共测试
│   ├── __init__.py
│   └── test_api.py          # LLM API 连接测试
└── threekingdoms/       # 三国杀游戏测试
    └── __init__.py
```

## 运行测试

### API 连接测试

测试 LLM API 连接是否正常：

```bash
python tests/common/test_api.py
```

**前提条件**：
- 已配置 `config/system.json`
- 填入有效的 API Key

### 运行游戏

#### 狼人杀
```bash
python werewolf_main.py
```

#### 三国杀
```bash
python threekingdoms.py
```

## 测试说明

| 测试文件 | 用途 | API 依赖 |
|---------|------|---------|
| `test_api.py` | 测试 API 连接 | ✅ |

## 新增测试

在对应目录添加测试文件，命名规范：
- 公共测试：`tests/common/test_*.py`
- 三国杀测试：`tests/threekingdoms/test_*.py`

## 注意事项

1. **API 相关测试** 需要确保 `config/system.json` 配置正确
2. 狼人杀使用新架构（`games/werewolf/`），入口文件为 `werewolf_main.py`