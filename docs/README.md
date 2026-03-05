# BotBattle 文档中心

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

## 🔧 配置文档

### 5. [API_CONFIG.md](API_CONFIG.md)
LLM API 配置指南，包含：
- 支持的 API 提供商
- 配置方法
- 常见问题

### 6. [DEPLOY.md](DEPLOY.md)
部署指南，包含：
- 环境要求
- 安装步骤
- 运行说明
- 故障排查

## 📝 其他文档

### 7. [LICENSE](../LICENSE)
项目许可证

### 8. [requirements.txt](../requirements.txt)
Python 依赖包列表

## 📂 文档分类

```
docs/
├── SDD.md                          # 核心 SDD 文档（狼人杀 + 通用）
├── SDD_ThreeKingdoms.md            # 三国杀 SDD 扩展
├── THREEKINGDOMS_REQUIREMENTS.md   # 三国杀需求总结
├── API_CONFIG.md                   # API 配置指南
└── DEPLOY.md                       # 部署指南
```

## 🔗 快速链接

- [测试指南](../tests/README.md) - 如何运行测试
- [配置示例](../config/system.example.json) - system.json 模板
- [人格配置](../config/personalities.json) - 7 种人格定义

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
