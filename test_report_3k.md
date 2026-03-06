# 三国杀游戏测试报告

**测试时间**: 2026-03-06 22:53
**测试版本**: 1.0 (开发版)
**测试轮次**: 第 1 轮全面测试
**测试人员**: AI 测试员

---

## 测试概况

| 项目 | 结果 |
|------|------|
| 运行次数 | 2 |
| 发现问题 | 8 个 |
| P0 致命问题 | 2 个 |
| P1 严重问题 | 3 个 |
| P2 一般问题 | 3 个 |
| 游戏日志 | `logs/3k_game_20260306_225323.json` |

---

## 问题清单

### [P0] 问题 1: ThreeKingdomsPlayer 缺少 is_human/is_bot 属性

**严重程度**: P0 (致命)

**发现位置**: `games/threekingdoms/state.py`

**问题描述**: 
`ThreeKingdomsPlayer` 数据类缺少 `is_human` 和 `is_bot` 属性，但 `engine.py` 中多处代码使用了这些属性，导致游戏启动时抛出 `AttributeError` 异常，游戏无法运行。

**错误信息**:
```
AttributeError: 'ThreeKingdomsPlayer' object has no attribute 'is_human'
```

**复现步骤**:
1. 运行 `python threekingdoms.py`
2. 选择观察模式
3. 游戏初始化后尝试访问玩家属性

**日志证据**:
```
File "E:\04project\BotBattle\games\threekingdoms\engine.py", line 240, in start
    if player.is_human:
AttributeError: 'ThreeKingdomsPlayer' object has no attribute 'is_human'
```

**涉及代码位置**:
- `games/threekingdoms/engine.py`: 第 240, 416, 775 行
- `games/threekingdoms/state.py`: `ThreeKingdomsPlayer` 类定义

**建议修复**: 
在 `ThreeKingdomsPlayer` 类中添加 `is_human: bool = False` 和 `is_bot: bool = True` 属性，并在 `setup()` 方法中根据 `human_player_id` 正确设置。

**修复状态**: ✅ 已修复

---

### [P0] 问题 2: 游戏结束消息重复显示

**严重程度**: P0 (致命)

**发现位置**: `games/threekingdoms/engine.py` - `_check_game_over()` 和 `_run_turn()`

**问题描述**: 
游戏结束时，获胜消息（如"主公死亡，反贼获胜！"）会显示两次。这是因为：
1. `_check_game_over()` 方法内部直接调用 `ui.display_system_message()` 显示消息
2. `_run_turn()` 在回合结束时调用 `_check_game_over()` 后返回
3. 主循环 `while not self._check_game_over()` 再次调用该方法

**日志证据** (游戏输出):
```
[系统] 主公死亡，反贼获胜！
[系统] 主公死亡，反贼获胜！
```

**复现步骤**:
1. 运行完整游戏直到主公死亡
2. 观察游戏结束时的消息输出

**涉及代码位置**:
- `games/threekingdoms/engine.py`: 第 720-737 行 (`_check_game_over`)
- `games/threekingdoms/engine.py`: 第 297-299 行 (`_run_turn`)
- `games/threekingdoms/engine.py`: 第 250 行 (主循环)

**建议修复**: 
将消息显示逻辑从 `_check_game_over()` 中分离，该方法只返回布尔值。在 `_run_turn()` 和 `_end_game()` 中调用新方法来获取并显示获胜消息。

**修复状态**: ✅ 已修复

---

### [P1] 问题 3: 濒死求桃逻辑中 AI 行为不合理

**严重程度**: P1 (严重)

**发现位置**: `games/threekingdoms/engine.py` - `_dying_request()`

**问题描述**: 
在濒死求桃流程中，AI 只要有桃就会使用，不考虑身份关系。测试中观察到反贼（3 号司马懿）使用桃救了主公（2 号黄忠），这不符合反贼的游戏目标。

**日志证据**:
```json
{
  "type": "card_responded",
  "data": {
    "player_id": 3,
    "response_card": "桃",
    "target": 2
  }
}
```
3 号玩家是反贼，2 号玩家是主公，反贼救主公不符合游戏逻辑。

**复现步骤**:
1. 让主公进入濒死状态
2. 确保反贼手中有桃
3. 观察反贼是否会救主公

**涉及代码位置**:
- `games/threekingdoms/engine.py`: 第 660-690 行 (`_dying_request`)

**建议修复**: 
在 `_dying_request()` 中添加 AI 决策逻辑，根据身份关系决定是否使用桃：
- 忠臣应该救主公
- 反贼不应该救主公（除非是内奸伪装）
- 内奸根据局势决定

---

### [P1] 问题 4: 锦囊牌效果未实现

**严重程度**: P1 (严重)

**发现位置**: `games/threekingdoms/engine.py` - `_play_card()` 和 `_ai_play_phase()`

**问题描述**: 
锦囊牌（过河拆桥、顺手牵羊、桃园结义、南蛮入侵、万箭齐发、决斗等）的效果完全没有实现。AI 摸到锦囊牌后只能弃置，无法使用。

**日志证据**:
```json
{
  "type": "phase_discard",
  "data": {
    "player_id": 5,
    "discarded_cards": ["乐不思蜀"]
  }
}
```
延时锦囊乐不思蜀被直接弃置，没有触发判定效果。

**复现步骤**:
1. 观察 AI 摸到锦囊牌后的行为
2. 发现锦囊牌最终被弃置

**涉及代码位置**:
- `games/threekingdoms/engine.py`: 第 550-590 行 (`_play_card`)
- `games/threekingdoms/engine.py`: 第 430-470 行 (`_ai_play_phase`)

**建议修复**: 
实现所有锦囊牌的效果逻辑，包括：
- 非延时锦囊：过河拆桥、顺手牵羊、桃园结义、南蛮入侵、万箭齐发、决斗
- 延时锦囊：乐不思蜀、兵粮寸断、闪电（部分已实现判定，但未实现使用）

---

### [P1] 问题 5: 距离计算和攻击范围未正确实现

**严重程度**: P1 (严重)

**发现位置**: `games/threekingdoms/state.py` - `get_distance_to()` 和 `can_attack()`

**问题描述**: 
距离计算过于简化，始终返回 1，没有考虑玩家座位位置。攻击范围判断虽然存在，但由于距离计算问题，实际上所有玩家都可以互相攻击。

**代码问题**:
```python
def get_distance_to(self, target: "ThreeKingdomsPlayer") -> int:
    # 基础距离为位置差（简化为 1）
    base_distance = 1  # ← 问题：始终为 1
```

**复现步骤**:
1. 观察任意玩家的攻击行为
2. 发现可以攻击任何位置的玩家

**涉及代码位置**:
- `games/threekingdoms/state.py`: 第 220-235 行

**建议修复**: 
实现正确的距离计算逻辑：
```python
def get_distance_to(self, target: "ThreeKingdomsPlayer") -> int:
    # 计算座位距离（逆时针）
    if target.id > self.id:
        base_distance = target.id - self.id
    else:
        base_distance = len(players) - self.id + target.id
    
    # 马的效果
    if self.equipped.horse_minus:
        base_distance -= 1
    if target.equipped.horse_plus:
        base_distance += 1
    
    return max(1, base_distance)
```

---

### [P2] 问题 6: AI 出牌逻辑过于简单

**严重程度**: P2 (一般)

**发现位置**: `games/threekingdoms/engine.py` - `_ai_play_phase()`

**问题描述**: 
AI 出牌逻辑非常简单，只有两个行为：
1. 有杀就出杀（随机选择目标）
2. 有装备就装备

没有考虑：
- 身份关系（集火反贼/保护主公）
- 血量情况（低血使用桃）
- 手牌管理（保留关键牌）
- 装备策略（替换更好的装备）

**代码问题**:
```python
# 简化 AI：有杀就出，有装备就装
```

**涉及代码位置**:
- `games/threekingdoms/engine.py`: 第 430-470 行

**建议修复**: 
实现更智能的 AI 决策：
1. 根据身份选择攻击目标
2. 低血量优先使用桃/酒
3. 评估装备价值再决定是否替换
4. 保留关键锦囊牌

---

### [P2] 问题 7: 酒的效果未实现

**严重程度**: P2 (一般)

**发现位置**: `games/threekingdoms/engine.py`

**问题描述**: 
酒的效果（本回合下一次杀伤害 +1，或濒死时自救）完全没有实现。AI 摸到酒后只能弃置。

**日志证据**:
```json
{
  "type": "phase_discard",
  "data": {
    "player_id": 2,
    "discarded_cards": ["酒"]
  }
}
```

**涉及代码位置**:
- `games/threekingdoms/engine.py`: `_play_card()` 方法

**建议修复**: 
添加酒的状态标记和使用逻辑：
1. 使用酒后设置 `player.wine_used = True`
2. 下一次杀结算时检查此标记，伤害 +1
3. 濒死时可以使用酒自救

---

### [P2] 问题 8: 武将技能未实现

**严重程度**: P2 (一般)

**发现位置**: 全局

**问题描述**: 
所有武将（曹操、刘备、关羽、张飞、诸葛亮等）的技能都没有实现，游戏变成了没有技能的标准杀。

**涉及代码位置**:
- 需要新增武将技能系统

**建议修复**: 
为每个武将实现技能：
- 曹操：奸雄（受到伤害后获得造成伤害的牌）
- 刘备：仁德（出牌阶段可以将手牌交给其他玩家）
- 关羽：武圣（可以将红色牌当杀使用）
- 等等...

---

## 测试结论

**当前状态**: ❌ 不通过 - 存在致命 bug 和多个严重问题

### 已修复问题
1. ✅ [P0] ThreeKingdomsPlayer 缺少 is_human/is_bot 属性
2. ✅ [P0] 游戏结束消息重复显示

### 待修复问题
| 优先级 | 数量 | 描述 |
|--------|------|------|
| P1 | 3 | 濒死求桃 AI 逻辑、锦囊牌效果、距离计算 |
| P2 | 3 | AI 出牌逻辑、酒效果、武将技能 |

---

## 下一步建议

### 立即修复 (P0/P1)
1. **修复濒死求桃 AI 逻辑** - 根据身份关系决定是否使用桃
2. **实现基本锦囊牌效果** - 至少实现过河拆桥、顺手牵羊、桃园结义
3. **修复距离计算** - 实现正确的座位距离计算

### 尽快修复 (P2)
4. **改进 AI 出牌逻辑** - 增加身份判断和战术决策
5. **实现酒的效果** - 伤害加成和自救功能
6. **实现武将技能** - 从热门武将开始（曹操、刘备、关羽等）

### 长期优化
7. 添加人类玩家出牌界面
8. 实现完整的响应机制（无懈可击、八卦阵判定等）
9. 增加游戏回放功能
10. 优化日志格式和可读性

---

## 附录：测试日志

**游戏日志路径**: `logs/3k_game_20260306_225323.json`

**游戏结果**:
- 获胜方：反贼
- 存活玩家：3 号司马懿（反贼）、4 号刘备（反贼）、5 号貂蝉（忠臣）
- 死亡玩家：1 号赵云（内奸）、2 号黄忠（主公）
- 游戏回合数：约 10 回合

---

*报告生成时间：2026-03-06 22:55*
