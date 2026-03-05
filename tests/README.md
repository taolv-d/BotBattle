# BotBattle 测试指南

## 目录结构

```
tests/
├── __init__.py
├── common/              # 公共测试（不依赖特定游戏模式）
│   ├── __init__.py
│   ├── test_api.py          # LLM API 连接测试
│   ├── test_analyze.py      # AI 发言分析测试
│   ├── test_celebrity.py    # 名人名字系统测试
│   ├── test_god_view.py     # 上帝视角显示测试
│   └── verify.py            # 代码验证（不依赖 API）
├── werewolf/            # 狼人杀游戏测试
│   ├── __init__.py
│   ├── test_auto.py         # 自动化完整测试
│   └── test_quick.py        # 快速测试（一轮）
└── threekingdoms/       # 三国杀游戏测试
    └── __init__.py
```

## 运行测试

### 1. 代码验证（推荐首先运行）

验证代码结构完整性，不依赖 API：

```bash
cd E:\04project\BotBattle
python tests/common/verify.py
```

### 2. API 连接测试

测试 LLM API 连接是否正常：

```bash
python tests/common/test_api.py
```

**前提条件**：
- 已配置 `config/system.json`
- 填入有效的 API Key

### 3. 功能测试

#### AI 发言分析测试
```bash
python tests/common/test_analyze.py
```

#### 名人名字系统测试
```bash
python tests/common/test_celebrity.py
```

#### 上帝视角显示测试
```bash
python tests/common/test_god_view.py
```

### 4. 游戏完整测试

#### 狼人杀 - 快速测试（1 轮）
```bash
python tests/werewolf/test_quick.py
```

#### 狼人杀 - 完整测试
```bash
python tests/werewolf/test_auto.py
```

#### 三国杀测试
```bash
python threekingdoms.py
```

## 测试说明

| 测试文件 | 用途 | API 依赖 | 推荐场景 |
|---------|------|---------|---------|
| `verify.py` | 验证代码完整性 | ❌ | 提交前验证 |
| `test_api.py` | 测试 API 连接 | ✅ | 首次配置后 |
| `test_analyze.py` | 测试 AI 分析逻辑 | ❌ | 开发调试 |
| `test_celebrity.py` | 测试名人名字系统 | ❌ | 开发调试 |
| `test_god_view.py` | 测试上帝视角显示 | ❌ | 开发调试 |
| `test_quick.py` | 快速游戏测试 | ✅ | 功能验证 |
| `test_auto.py` | 完整游戏测试 | ✅ | 回归测试 |

## 新增测试

在对应目录添加测试文件，命名规范：
- 公共测试：`tests/common/test_*.py`
- 狼人杀测试：`tests/werewolf/test_*.py`
- 三国杀测试：`tests/threekingdoms/test_*.py`

## 注意事项

1. **API 相关测试** 需要确保 `config/system.json` 配置正确
2. **完整游戏测试** 会消耗 API 额度，建议先用 `test_quick.py`
3. **验证脚本** `verify.py` 不依赖 API，可随时运行
