# BotBattle 文档中心

**最后更新**: 2026-03-16

---

## 📂 文档目录结构

```
docs/
├── README.md                         # 本文档索引
├── PROJECT_STRUCTURE.md              # 项目结构说明
│
├── # 核心规范文档
├── SDD.md                            # 核心 SDD（狼人杀 + 通用架构）
├── SDD_ThreeKingdoms.md              # 三国杀 SDD 扩展
├── THREEKINGDOMS_REQUIREMENTS.md     # 三国杀需求总结
│
├── # 角色规范文档
├── WEREWOLF_ROLE_SPECIFICATION.md    # 狼人角色规范
├── VILLAGER_ROLE_SPECIFICATION.md    # 村民角色规范
├── SEER_ROLE_SPECIFICATION.md        # 预言家角色规范
├── WITCH_ROLE_SPECIFICATION.md       # 女巫角色规范
├── HUNTER_ROLE_SPECIFICATION.md      # 猎人角色规范
│
├── # 配置和部署文档
├── API_CONFIG.md                     # API 配置指南
├── DEPLOY.md                         # 部署指南
│
├── # 专题文档目录
├── bugfixes/                         # Bug 修复文档
│   ├── README.md                     # 索引
│   ├── CODE_REVIEW_SUMMARY.md        # 代码审查执行摘要
│   ├── CODE_REVIEW_REPORT.md         # 完整代码审查报告
│   ├── CRITICAL_BUGFIXES.md          # 致命 Bug 修复
│   ├── EMOTIONAL_AI_IMPROVEMENTS.md  # 情感 AI 改进
│   ├── WEREWOLF_IMPROVEMENTS.md      # 狼人杀功能改进
│   ├── BUGFIX_REPORT.md              # Bug 修复报告
│   ├── FINAL_VERIFICATION_REPORT.md  # 最终验证报告
│   ├── test_report*.md               # 测试报告 (4 个)
│   ├── test_report_3k.md             # 三国杀测试报告
│   ├── THREEKINGDOMS_FIX_REPORT.md   # 三国杀修复报告
│   └── VERIFICATION_REPORT_3K.md     # 三国杀验证报告
│
└── refactor_202603/                  # 2026 年 3 月重构文档
    ├── README.md                     # 重构索引
    └── REFACTOR_DESIGN_WEREWOLF.md   # 狼人杀多 Agents 重构设计
```

---

## 📚 核心文档

### 1. [README.md](../README.md)
项目介绍、快速开始、功能特性

### 2. [SDD.md](SDD.md) - 规范驱动开发文档
**适用范围**：狼人杀、通用架构

**内容**：
- 架构规范（模块依赖、数据流）
- 核心模块规范（GameEngine, AIAgent, GameState, UI）
- 日志规范（事件类型、格式）
- 配置规范（system.json, 游戏配置，人格配置）
- AI 发言质量规范
- 测试规范
- 扩展规范（新游戏、新 UI）

### 3. [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) - 三国杀扩展文档
**适用范围**：三国杀游戏模式

**内容**：
- 三国杀核心规范（与狼人杀对比）
- 数据结构（玩家状态、卡牌结构）
- 游戏流程（回合流程、响应机制）
- AI 决策规范（决策场景、思考过程记录）
- UI 规范（全局看板布局）
- 配置规范（三国杀配置、武将技能）

### 4. [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md)
三国杀需求决策总结，包含：
- 游戏规则确认
- AI 设计决策
- UI 设计规范
- 信息可见性规则

---

## 🎭 角色规范文档

| 文档 | 描述 |
|------|------|
| [WEREWOLF_ROLE_SPECIFICATION.md](WEREWOLF_ROLE_SPECIFICATION.md) | 狼人角色行为和决策规范 |
| [VILLAGER_ROLE_SPECIFICATION.md](VILLAGER_ROLE_SPECIFICATION.md) | 村民角色行为和决策规范 |
| [SEER_ROLE_SPECIFICATION.md](SEER_ROLE_SPECIFICATION.md) | 预言家角色行为和决策规范 |
| [WITCH_ROLE_SPECIFICATION.md](WITCH_ROLE_SPECIFICATION.md) | 女巫角色行为和决策规范 |
| [HUNTER_ROLE_SPECIFICATION.md](HUNTER_ROLE_SPECIFICATION.md) | 猎人角色行为和决策规范 |

---

## 🔧 配置和部署文档

### [API_CONFIG.md](API_CONFIG.md)
LLM API 配置指南，包含：
- 支持的 API 提供商（DeepSeek/Kimi/通义千问）
- 配置方法
- 常见问题

### [DEPLOY.md](DEPLOY.md)
部署指南，包含：
- 环境要求
- 安装步骤
- 运行说明
- 故障排查

---

## 🐛 Bug 修复文档

**目录**: [`bugfixes/`](bugfixes/)

| 文档 | 描述 |
|------|------|
| [CODE_REVIEW_SUMMARY.md](bugfixes/CODE_REVIEW_SUMMARY.md) | 代码审查执行摘要（23 个问题） |
| [CODE_REVIEW_REPORT.md](bugfixes/CODE_REVIEW_REPORT.md) | 完整代码审查报告 |
| [CRITICAL_BUGFIXES.md](bugfixes/CRITICAL_BUGFIXES.md) | 致命 Bug 修复详情 |
| [EMOTIONAL_AI_IMPROVEMENTS.md](bugfixes/EMOTIONAL_AI_IMPROVEMENTS.md) | 情感 AI 改进文档 |
| [WEREWOLF_IMPROVEMENTS.md](bugfixes/WEREWOLF_IMPROVEMENTS.md) | 狼人杀功能改进总结 |
| 测试报告 ×4 | 狼人杀测试报告 |
| 三国杀报告 ×3 | 三国杀测试/修复/验证报告 |

📝 **详细说明**: [bugfixes/README.md](bugfixes/README.md)

---

## 🔄 重构文档

**目录**: [`refactor_202603/`](refactor_202603/)

| 文档 | 描述 |
|------|------|
| [REFACTOR_DESIGN_WEREWOLF.md](refactor_202603/REFACTOR_DESIGN_WEREWOLF.md) | 狼人杀多 Agents 重构设计文档 |

**重构内容**：
- 引入 AutoGen 多 Agents 框架
- 集成 Python logging 模块
- TTS 接口抽象
- 模块化重构

📝 **详细说明**: [refactor_202603/README.md](refactor_202603/README.md)

---

## 🔗 快速链接

- [测试指南](../tests/README.md) - 如何运行测试
- [配置示例](../config/system.example.json) - system.json 模板
- [人格配置](../config/personalities.json) - 7 种人格定义
- [项目结构](PROJECT_STRUCTURE.md) - 完整目录结构

---

## 📖 阅读顺序建议

### 新开发者
1. [README.md](../README.md) - 了解项目
2. [DEPLOY.md](DEPLOY.md) - 搭建环境
3. [API_CONFIG.md](API_CONFIG.md) - 配置 API
4. [SDD.md](SDD.md) - 理解架构
5. [tests/README.md](../tests/README.md) - 运行测试

### 添加新游戏模式
1. [SDD.md](SDD.md) 第七节 - 扩展规范
2. [SDD_ThreeKingdoms.md](SDD_ThreeKingdoms.md) - 参考三国杀实现
3. [THREEKINGDOMS_REQUIREMENTS.md](THREEKINGDOMS_REQUIREMENTS.md) - 需求决策参考

### 修改现有功能
1. [SDD.md](SDD.md) 对应章节 - 查看规范
2. 运行 `python tests/common/verify.py` - 验证代码
3. 运行对应测试 - 确保功能正常

### 了解重构计划
1. [refactor_202603/README.md](refactor_202603/README.md) - 重构设计
2. [bugfixes/CODE_REVIEW_SUMMARY.md](bugfixes/CODE_REVIEW_SUMMARY.md) - 了解历史问题
