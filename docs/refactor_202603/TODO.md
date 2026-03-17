# 狼人杀多 Agents 重构 TODO

**版本**: v1.0  
**日期**: 2026-03-17  
**状态**: 待实现  

---

## 📋 实现计划（4 周）

### Week 1: 基础设施

- [ ] 创建 `services/` 目录
- [ ] 实现 `LoggerService`（日志服务）
- [ ] 实现 `TTSInterface`（TTS 接口）
- [ ] 实现 `LLMService`（LLM 服务）
- [ ] 编写单元测试

### Week 2: Agent 框架

- [ ] 创建 `games/werewolf/config.py`（游戏配置）
- [ ] 创建 `games/werewolf/state.py`（游戏状态）
- [ ] 实现 `WerewolfAgent` 基类
- [ ] 实现 6 个角色 Agent（狼人/村民/预言家/女巫/猎人/守卫）
- [ ] 封装 `WerewolfGroupChat`（AutoGen 群聊）
- [ ] 编写单元测试

### Week 3: 编排器

- [ ] 实现 `WerewolfOrchestrator`（游戏编排器）
- [ ] 实现 `_run_night()`（夜晚行动）
- [ ] 实现 `_run_president_election()`（警长竞选）
- [ ] 实现 `_run_vote()`（投票，含平票处理）
- [ ] 实现 `_run_hunter_skill()`（猎人技能）
- [ ] 实现自爆检查
- [ ] 实现警长继承机制
- [ ] 集成日志服务
- [ ] 集成 TTS 接口
- [ ] 编写集成测试

### Week 4: 测试和优化

- [ ] 运行完整游戏测试（10 次）
- [ ] 修复 Bug
- [ ] 性能优化
- [ ] 更新文档

---

## 📊 详细设计参考

- **FINAL_DESIGN.md**: 详细设计文档（约 1100 行）
- **BUG_LIST.md**: Bug 检查清单（47 个问题已修复）
- **README.md**: 重构索引

---

## ✅ 总体评估

**设计状态**: ✅ 完善，可以直接用于实现  
**预计工作量**: 3-5 人天
