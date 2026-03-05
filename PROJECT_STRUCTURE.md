# BotBattle 项目结构

```
BotBattle/
│
├── 📄 核心入口文件
│   ├── main.py                   # 狼人杀主入口
│   ├── threekingdoms.py          # 三国杀主入口
│   ├── config_loader.py          # 配置加载器
│   └── init.py                   # 初始化脚本
│
├── 📁 核心模块
│   ├── core/                     # 核心游戏引擎
│   │   ├── __init__.py
│   │   ├── game_engine.py        # 游戏引擎（狼人杀）
│   │   └── state.py              # 游戏状态定义
│   │
│   ├── ai/                       # AI 模块
│   │   ├── __init__.py
│   │   ├── agent.py              # AI 代理
│   │   ├── llm_client.py         # LLM 客户端
│   │   ├── personality.py        # 人格系统
│   │   └── names.py              # 名人名字生成器 ⭐ NEW
│   │
│   ├── ui/                       # 用户界面
│   │   ├── __init__.py
│   │   ├── base.py               # UI 基类
│   │   ├── cli.py                # 命令行界面（狼人杀）⭐ UPDATED
│   │   └── threekingdoms_cli.py  # 三国杀命令行界面 ⭐ UPDATED
│   │
│   └── games/                    # 游戏实现
│       ├── __init__.py
│       ├── werewolf/             # 狼人杀游戏
│       │   ├── __init__.py
│       │   ├── roles.py
│       │   └── phases.py
│       │
│       └── threekingdoms/        # 三国杀游戏 ⭐ UPDATED
│           ├── __init__.py
│           ├── engine.py         # 游戏引擎
│           ├── state.py          # 状态定义 ⭐ UPDATED
│           └── agent.py          # AI 代理
│
├── 📁 配置文件
│   └── config/
│       ├── system.json           # 系统配置（需手动创建）
│       ├── system.example.json   # 系统配置示例
│       ├── personalities.json    # 人格配置
│       ├── werewolf_default.json # 狼人杀配置
│       └── threekingdoms_default.json  # 三国杀配置
│
├── 📁 测试目录 🆕
│   └── tests/
│       ├── __init__.py
│       ├── README.md             # 测试指南
│       │
│       ├── common/               # 公共测试
│       │   ├── __init__.py
│       │   ├── verify.py         # 代码验证（无 API 依赖）
│       │   ├── test_api.py       # API 连接测试
│       │   ├── test_analyze.py   # AI 分析测试
│       │   ├── test_celebrity.py # 名人名字测试 ⭐ NEW
│       │   └── test_god_view.py  # 上帝视角测试 ⭐ NEW
│       │
│       ├── werewolf/             # 狼人杀测试
│       │   ├── __init__.py
│       │   ├── test_auto.py      # 自动化测试
│       │   └── test_quick.py     # 快速测试
│       │
│       └── threekingdoms/        # 三国杀测试
│           └── __init__.py
│
├── 📁 文档目录 🆕
│   └── docs/
│       ├── README.md             # 文档索引
│       ├── SDD.md                # 核心 SDD 文档
│       ├── SDD_ThreeKingdoms.md  # 三国杀 SDD
│       ├── THREEKINGDOMS_REQUIREMENTS.md  # 三国杀需求
│       ├── API_CONFIG.md         # API 配置指南
│       └── DEPLOY.md             # 部署指南
│
├── 📁 日志目录
│   └── logs/                     # 游戏日志输出
│
├── 📄 其他文件
│   ├── README.md                 # 项目说明
│   ├── requirements.txt          # Python 依赖
│   ├── LICENSE                   # 许可证
│   └── .gitignore                # Git 忽略配置
│
└── 📁 版本控制
    └── .git/
```

## 📝 变更说明

### 2026-03-05 项目整理 ⭐

#### 测试文件整理
- ✅ 创建 `tests/` 目录，按游戏类型分类
- ✅ 公共测试 → `tests/common/`
- ✅ 狼人杀测试 → `tests/werewolf/`
- ✅ 三国杀测试 → `tests/threekingdoms/`
- ✅ 更新所有测试文件的路径引用

#### 文档整理
- ✅ 创建 `docs/` 目录
- ✅ 移动 SDD 文档 → `docs/SDD.md`
- ✅ 移动三国杀文档 → `docs/SDD_ThreeKingdoms.md` 等
- ✅ 创建文档索引 `docs/README.md`
- ✅ 创建测试指南 `tests/README.md`

#### 新增功能
- ✅ 名人名字系统 → `ai/names.py`
- ✅ 上帝视角显示身份功能
- ✅ 玩家名字显示：`7 号玩家 (诸葛亮)- 预言家`

## 🚀 快速开始

### 运行测试
```bash
# 代码验证（推荐首先运行）
python tests/common/verify.py

# 名人名字测试
python tests/common/test_celebrity.py

# 狼人杀快速测试
python tests/werewolf/test_quick.py
```

### 运行游戏
```bash
# 狼人杀
python main.py

# 三国杀
python threekingdoms.py
```

## 📊 模块依赖关系

```
main.py / threekingdoms.py
    │
    ├── config_loader.py
    │
    ├── core/game_engine.py 或 games/threekingdoms/engine.py
    │   │
    │   ├── core/state.py 或 games/threekingdoms/state.py
    │   │
    │   ├── ai/
    │   │   ├── agent.py
    │   │   ├── llm_client.py
    │   │   ├── personality.py
    │   │   └── names.py ⭐
    │   │
    │   └── ui/
    │       ├── cli.py 或 threekingdoms_cli.py
    │       └── base.py
    │
    └── config/*.json
```

## 📖 文档导航

- **新手入门**: [README.md](../README.md) → [DEPLOY.md](docs/DEPLOY.md)
- **开发者**: [SDD.md](docs/SDD.md) → [tests/README.md](tests/README.md)
- **添加游戏**: [SDD_ThreeKingdoms.md](docs/SDD_ThreeKingdoms.md) 作为参考
