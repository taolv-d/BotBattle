# 狼人杀游戏逻辑测试报告

**测试时间**: 2026-03-06  
**测试版本**: v1.0  
**测试轮次**: 第 1 轮  
**测试状态**: ❌ 不通过（需修复后重测）

---

## 测试概况

| 项目 | 结果 |
|------|------|
| 运行次数 | 1 |
| 发现问题 | 23 个 |
| 致命 bug | 6 个 |
| 测试时长 | ~30 秒 |

---

## 测试环境

- **操作系统**: Windows
- **Python 版本**: 3.x
- **测试模式**: DummyLLM（自动化逻辑测试）
- **游戏配置**: 9 人局（3 狼 3 民 1 预言 1 女巫 1 猎人）

---

## 关键 Bug 清单

### P0 - 致命问题（6 个）

#### P0-1: 预言家查验结果显示具体角色名

**位置**: `core/game_engine.py:419`

**测试日志**:
```
[系统] 预言家查验了 2 号，结果是：witch
```

**问题**: 查验结果应该显示"好人"，但显示了具体角色"witch"

**规范要求**: 
> 查验结果：仅返回"好人"或"狼人"，不区分具体身份
> —— docs/SEER_ROLE_SPECIFICATION.md

**修复代码**:
```python
# 修复前
self.state.seer_check_result = target.role

# 修复后
is_wolf = target.role == Role.WEREWOLF
display_result = "狼人" if is_wolf else "好人"
```

---

#### P0-2: 女巫可以毒杀自己

**位置**: `core/game_engine.py:330-345`

**测试日志**:
```
角色配置：[(1, 'villager'), (2, 'witch'), ...]
[系统] 2 号玩家 被毒杀  # 2 号是女巫自己
```

**问题**: 女巫 AI 返回毒杀 2 号，但 2 号就是女巫自己，代码没有验证

**规范要求**:
> 毒药：可以毒杀任意存活玩家，整局只能用一次
> 不能毒杀自己
> —— docs/WITCH_ROLE_SPECIFICATION.md

**修复代码**:
```python
elif action_type == "poison":
    poison_target = action.get("target")
    # 验证目标不能是自己
    if poison_target == witch.id:
        action = {"action": "none"}
        inner_thought = "不能毒杀自己"
    elif self.witch_poison_used:
        # ...
```

---

#### P0-3: 猎人技能发动时目标列表包含自己

**位置**: `core/game_engine.py:480`

**测试日志**:
```
[DEBUG] 猎人技能发动：猎人=6 号，存活玩家=[1, 4, 5, 6]
# 6 号已死亡但仍在列表中
```

**问题**: 猎人技能的目标列表包含了猎人自己

**规范要求**:
> 不能带走自己
> —— docs/HUNTER_ROLE_SPECIFICATION.md

**修复代码**:
```python
# 修复前
context = {"alive_players": [p for p in alive_players if p != hunter.id]}

# 修复后 - 确保在多个地方都过滤掉猎人自己
valid_targets = [p for p in alive_players if p != hunter.id]
context = {"alive_players": valid_targets}
```

---

#### P0-4: 游戏结束判断过早

**位置**: `core/game_engine.py:463`

**问题**: 在猎人技能发动前就检查游戏结束，可能导致猎人无法带走最后狼人

**规范要求**:
> 猎人死亡时可以带走一名玩家
> —— docs/HUNTER_ROLE_SPECIFICATION.md

**修复代码**:
```python
# 修复前
if killed_by_wolf and not saved:
    # ... 处理死亡
    if target.role == Role.HUNTER:
        self._handle_hunter_skill(target, alive_villagers)
self.state.check_game_over()  # 在猎人技能前检查

# 修复后
if killed_by_wolf and not saved:
    # ... 处理死亡
    if target.role == Role.HUNTER:
        self._handle_hunter_skill(target, alive_villagers)
# 在猎人技能后检查
self.state.check_game_over()
```

---

#### P0-5: 狼人袭击目标验证不完整

**位置**: `core/game_engine.py:195-203`

**问题**: 如果 AI 返回狼队友作为目标，代码不会拦截

**规范要求**:
> 不能袭击狼队友
> —— docs/WEREWOLF_ROLE_SPECIFICATION.md

**修复代码**:
```python
# 添加狼队友验证
wolf_ids = [w.id for w in werewolves]
if target in wolf_ids:
    valid_targets = [p for p in alive_villagers if p not in wolf_ids]
    target = random.choice(valid_targets) if valid_targets else None
```

---

#### P0-6: 女巫第一夜自救逻辑不完整

**位置**: `core/game_engine.py:329`

**问题**: 自救逻辑作为 fallback，不是强制的

**规范要求**:
> 首夜被狼刀可以自救（BotBattle 规则）
> 第一夜被刀 → 必须自救
> —— docs/WITCH_ROLE_SPECIFICATION.md

**修复代码**:
```python
# 在 AI 决策前明确告知女巫自己被刀
if dead_player_id == witch.id and self.state.night_number == 1:
    # 强制自救
    action = {"action": "heal", "target": witch.id}
```

---

### P1 - 严重问题（10 个）

#### P1-1: 女巫药剂状态未正确同步给 AI
#### P1-2: 预言家重复查验问题
#### P1-3: 猎人技能目标验证不完整
#### P1-4: 狼人遗言可能暴露身份
#### P1-5: 村民找狼逻辑缺失
#### P1-6: 发言过于简单没有分析
#### P1-7: 投票逻辑过于简单
#### P1-8: 警长选举 AI 参选概率固定
#### P1-9: 平票处理简单
#### P1-10: 日志记录不完整

---

### P2 - 一般问题（7 个）

#### P2-1: 女巫同一晚使用两种药剂支持不完整
#### P2-2: 毒药目标存活验证缺失
#### P2-3: 预言家夜晚无行动支持
#### P2-4: 狼人空刀支持不完整
#### P2-5: 警长选举逻辑问题
#### P2-6: 投票平票处理简单
#### P2-7: 日志记录不完整

---

## 测试日志分析

### 游戏流程

```
第 1 夜:
  - 狼人袭击 8 号（村民）✓
  - 预言家查验 2 号（女巫）→ 显示"witch" ✗
  - 女巫毒杀 2 号（自己）✗

第 1 天:
  - 警长竞选：4 人参选 ✓
  - 9 号当选警长 ✓
  - 发言：过于简单 ✗
  - 投票：平票 ✓

第 2 夜:
  - 狼人袭击 6 号（猎人）✓
  - 预言家查验 1 号（村民）→ 显示"villager" ✓
  - 猎人被刀，开枪带走 1 号 ✓
  - 游戏结束：狼人胜利 ✓
```

### 死亡记录

| 玩家 | 角色 | 死亡原因 | 记录状态 |
|------|------|---------|---------|
| 8 号 | 村民 | 狼刀 | ✅ 正确 |
| 2 号 | 女巫 | 毒药（自己） | ❌ 错误 |
| 6 号 | 猎人 | 狼刀 | ✅ 正确 |
| 1 号 | 村民 | 猎人技能 | ✅ 正确 |

---

## 修复建议

### 立即修复（本周）

1. **P0-1**: 预言家查验结果转换
2. **P0-2**: 女巫毒药目标验证
3. **P0-3**: 猎人技能目标过滤
4. **P0-4**: 游戏结束判断时机
5. **P0-5**: 狼人袭击目标验证
6. **P0-6**: 女巫自救逻辑

### 尽快修复（下周）

7. P1 问题 1-5（影响游戏平衡）

### 稍后修复（下月）

8. P1 问题 6-10（体验优化）
9. P2 问题（功能完善）

---

## 验证方法

修复后运行以下测试验证：

```bash
# 1. 逻辑测试
python test_logic.py

# 2. 快速游戏测试
python tests\werewolf\test_quick.py

# 3. 完整游戏测试
python tests\werewolf\test_auto.py
```

---

## 测试结论

**当前状态**: ❌ 不通过

**原因**: 
- 6 个 P0 致命 bug 影响核心游戏逻辑
- 10 个 P1 严重问题影响游戏平衡
- 多个问题已在测试中被确认

**建议**: 
1. 优先修复 P0 问题
2. 重新运行测试验证
3. 修复 P1 问题
4. 进行完整游戏测试

---

## 附录

### 测试报告文件

- 详细审查报告：`docs/CODE_REVIEW_REPORT.md`
- 执行摘要：`docs/CODE_REVIEW_SUMMARY.md`
- 测试日志：`logs/test_report.json`
- 游戏日志：`logs/game_*.json`

### 参考文档

- 女巫设计规范：`docs/WITCH_ROLE_SPECIFICATION.md`
- 预言家设计规范：`docs/SEER_ROLE_SPECIFICATION.md`
- 猎人设计规范：`docs/HUNTER_ROLE_SPECIFICATION.md`
- 村民设计规范：`docs/VILLAGER_ROLE_SPECIFICATION.md`
- 狼人设计规范：`docs/WEREWOLF_ROLE_SPECIFICATION.md`

---

**报告生成时间**: 2026-03-06  
**测试员**: AI 逻辑测试专家  
**版本**: v1.0
