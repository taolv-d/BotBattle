# BotBattle

AI 驱动的桌游对战项目，目前包含狼人杀与三国杀两个游戏方向。项目以可扩展的游戏模块、LLM 服务封装、日志与复盘能力为核心，支持观察模式和部分玩家参与模式。

## 当前状态

- 狼人杀主线已迁移到 `games/werewolf/` 新架构
- 三国杀实现位于 `games/threekingdoms/`
- 提供公共服务层：LLM、日志、TTS、游戏复盘
- 文档中心位于 `docs/`

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd BotBattle
```

### 2. 初始化配置

```bash
python init.py
```

如果没有使用初始化脚本，也可以手动复制：

```bash
cp config/system.example.json config/system.json
```

### 3. 配置 API Key

编辑 `config/system.json`，填入可用的 API 配置。详细说明见 [docs/CONFIG_GUIDE.md](docs/CONFIG_GUIDE.md)。

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 测试 API 连接

```bash
python tests/common/test_api.py
```

### 6. 运行游戏

狼人杀：

```bash
python werewolf_main.py
```

三国杀：

```bash
python threekingdoms.py
```

## 目录概览

```text
BotBattle/
├── werewolf_main.py              # 狼人杀入口
├── threekingdoms.py              # 三国杀入口
├── init.py                       # 初始化脚本
├── config_loader.py              # 配置加载
├── config/                       # 系统与游戏配置
├── docs/                         # 项目文档
├── games/
│   ├── werewolf/                 # 狼人杀新架构
│   └── threekingdoms/            # 三国杀实现
├── services/                     # LLM、日志、TTS、复盘等服务
├── tests/                        # 测试
├── ui/                           # CLI/UI 抽象
└── logs/                         # 游戏日志输出
```

## 文档入口

- 项目文档索引：[docs/README.md](docs/README.md)
- 配置指南：[docs/CONFIG_GUIDE.md](docs/CONFIG_GUIDE.md)
- 狼人杀重构索引：[docs/refactor_202603/README.md](docs/refactor_202603/README.md)
- 狼人杀主说明：[docs/refactor_202603/WEREWOLF_GUIDE.md](docs/refactor_202603/WEREWOLF_GUIDE.md)
- 三国杀设计：[docs/SDD_ThreeKingdoms.md](docs/SDD_ThreeKingdoms.md)

## 测试

当前仓库中可以看到的测试包括：

- `tests/common/test_api.py`：LLM API 连接测试
- `tests/werewolf/test_seer_revealed.py`：狼人杀发言与预言家信息测试
- `tests/test_game_review.py`：复盘服务测试
- `test_threekingdoms_fixes.py`：三国杀修复验证脚本

## 注意事项

- `config/system.json` 含有 API Key，不应提交到 Git
- 狼人杀相关重构文档中有部分 TODO 未完全回写，阅读时请以代码现状为准
- 复盘功能会在游戏结束后生成 `reviews/` 目录下的报告文件
