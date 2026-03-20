# BotBattle 文档中心

**最后更新**: 2026-03-20

---

## 文档目录

```
docs/
├── README.md                        # 本文档索引
├── API_CONFIG.md                    # API 配置指南
├── DEPLOY.md                        # 部署指南
├── SDD_ThreeKingdoms.md             # 三国杀 SDD
├── THREEKINGDOMS_REQUIREMENTS.md    # 三国杀需求
│
└── refactor_202603/                 # 狼人杀重构文档
    ├── README.md                    # 重构索引
    ├── FINAL_DESIGN.md              # 详细设计文档
    ├── BUG_LIST.md                  # Bug 检查清单
    └── TODO.md                      # 实现计划
```

---

## 核心文档

### 狼人杀（新架构）

| 文档 | 描述 |
|------|------|
| [refactor_202603/README.md](refactor_202603/README.md) | 重构索引 |
| [refactor_202603/FINAL_DESIGN.md](refactor_202603/FINAL_DESIGN.md) | 详细设计文档（v9.0） |
| [refactor_202603/BUG_LIST.md](refactor_202603/BUG_LIST.md) | Bug 检查清单（45个问题已修复） |

### 三国杀

| 文档 | 描述 |
|------|------|
| [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) | 三国杀规范文档 |
| [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md) | 三国杀需求决策 |

### 配置和部署

| 文档 | 描述 |
|------|------|
| [API_CONFIG.md](API_CONFIG.md) | LLM API 配置指南 |
| [DEPLOY.md](DEPLOY.md) | 部署指南 |

---

## 快速开始

### 运行狼人杀
```bash
python werewolf_main.py
```

### 运行三国杀
```bash
python threekingdoms.py
```

### 初始化配置
```bash
python init.py
```

---

## 项目结构

```
BotBattle/
├── werewolf_main.py          # 狼人杀入口
├── threekingdoms.py          # 三国杀入口
├── config_loader.py          # 配置加载器
├── init.py                   # 初始化脚本
│
├── games/
│   ├── werewolf/             # 狼人杀模块（新架构）
│   │   ├── orchestrator.py   # 游戏编排器
│   │   ├── state.py          # 游戏状态
│   │   ├── config.py         # 游戏配置
│   │   └── agents/           # 角色 Agent
│   │
│   └── threekingdoms/        # 三国杀模块
│
├── services/                 # 服务模块
│   ├── llm_service.py        # LLM 服务
│   ├── logger_service.py     # 日志服务
│   └── tts_interface.py      # TTS 接口
│
├── ai/                       # AI 模块
├── ui/                       # 用户界面
├── core/                     # 核心模块
├── config/                   # 配置文件
├── docs/                     # 文档
└── logs/                     # 日志输出
```

---

## 阅读顺序建议

### 新开发者
1. [DEPLOY.md](DEPLOY.md) - 搭建环境
2. [API_CONFIG.md](API_CONFIG.md) - 配置 API
3. [refactor_202603/README.md](refactor_202603/README.md) - 了解架构

### 开发狼人杀
1. [refactor_202603/FINAL_DESIGN.md](refactor_202603/FINAL_DESIGN.md) - 详细设计
2. [refactor_202603/BUG_LIST.md](refactor_202603/BUG_LIST.md) - 已修复问题

### 开发三国杀
1. [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) - 规范文档
2. [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md) - 需求决策