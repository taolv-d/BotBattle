# BotBattle 文档中心

**最后更新**: 2026-03-24

---

## 文档目录

```text
docs/
├── README.md                        # 本文档索引
├── CONFIG_GUIDE.md                  # API 与运行配置指南
├── SDD_ThreeKingdoms.md             # 三国杀 SDD
├── THREEKINGDOMS_REQUIREMENTS.md    # 三国杀需求与决策
├── ui/
│   └── WEREWOLF_UI_IMPLEMENTATION.md # 狼人杀 UI 实现说明
└── refactor_202603/                 # 狼人杀重构文档
    ├── README.md                    # 重构索引
    ├── WEREWOLF_GUIDE.md            # 狼人杀主说明文档
    └── PENDING_ITEMS.md             # 临时未完成事项
```

---

## 核心文档

### 狼人杀

| 文档 | 描述 |
|------|------|
| [refactor_202603/README.md](refactor_202603/README.md) | 狼人杀文档索引 |
| [refactor_202603/WEREWOLF_GUIDE.md](refactor_202603/WEREWOLF_GUIDE.md) | 狼人杀主说明文档 |
| [refactor_202603/PENDING_ITEMS.md](refactor_202603/PENDING_ITEMS.md) | 当前待补实现与验证事项 |
| [ui/WEREWOLF_UI_IMPLEMENTATION.md](ui/WEREWOLF_UI_IMPLEMENTATION.md) | UI 实现说明 |

### 三国杀

| 文档 | 描述 |
|------|------|
| [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) | 规范文档 |
| [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md) | 需求与取舍说明 |

### 配置

| 文档 | 描述 |
|------|------|
| [CONFIG_GUIDE.md](CONFIG_GUIDE.md) | LLM、模型与运行配置指南 |

---

## 快速开始

### 初始化配置

```bash
python init.py
```

### 运行狼人杀

```bash
python werewolf_main.py
```

### 运行三国杀

```bash
python threekingdoms.py
```

### 测试 API 连接

```bash
python tests/common/test_api.py
```

---

## 项目结构

```text
BotBattle/
├── werewolf_main.py          # 狼人杀入口
├── threekingdoms.py          # 三国杀入口
├── config_loader.py          # 配置加载器
├── init.py                   # 初始化脚本
├── config/                   # 配置文件
├── docs/                     # 文档
├── games/
│   ├── werewolf/             # 狼人杀模块（新架构）
│   └── threekingdoms/        # 三国杀模块
├── services/                 # 公共服务
├── tests/                    # 测试
├── ui/                       # 用户界面
└── logs/                     # 日志输出
```

---

## 阅读顺序建议

### 新开发者

1. [CONFIG_GUIDE.md](CONFIG_GUIDE.md) - 配置 API 与运行环境
2. [refactor_202603/README.md](refactor_202603/README.md) - 了解狼人杀新架构
3. [tests/README.md](../tests/README.md) - 查看当前测试覆盖

### 开发狼人杀

1. [refactor_202603/WEREWOLF_GUIDE.md](refactor_202603/WEREWOLF_GUIDE.md) - 阅读当前实现说明
2. [refactor_202603/PENDING_ITEMS.md](refactor_202603/PENDING_ITEMS.md) - 查看待补事项
3. [tests/README.md](../tests/README.md) - 查看测试入口

### 开发三国杀

1. [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) - 规范文档
2. [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md) - 需求决策

---

## 说明

- 旧文档中曾提到的 `API_CONFIG.md`、`DEPLOY.md` 目前仓库内不存在，相关内容已由 `CONFIG_GUIDE.md` 和当前入口脚本替代。
- 部分重构 TODO 仍保留历史表述，但代码已先行实现；如遇冲突，请优先参考代码现状。
