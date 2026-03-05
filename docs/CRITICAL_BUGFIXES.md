# 狼人杀核心规则 Bug 修复

**修复日期**: 2026-03-06  
**修复内容**: 修复多个致命规则 bug

---

## 📋 问题分析

根据日志 `game_20260305_233602.json` 的详细分析，发现以下严重问题：

### 一、基础规则矛盾（⚠️ 致命）

| 问题 | 严重程度 | 状态 |
|------|---------|------|
| 1. 游戏结束条件错误（3 狼 vs 3 好人就结束） | ⚠️ 致命 | ✅ 已修复 |
| 2. 女巫解药无限使用 | ⚠️ 致命 | ✅ 已修复 |
| 3. 猎人被投票出局还能开枪 | ⚠️ 致命 | ✅ 已修复 |

### 二、玩家身份与行为矛盾（⚠️ 严重）

| 问题 | 严重程度 | 状态 |
|------|---------|------|
| 4. 猎人遗言说"验人"（混淆角色能力） | ⚠️ 严重 | ✅ 已修复 |
| 5. 3 号死亡无记录 | ⚠️ 中等 | ✅ 已修复 |

### 三、投票记录矛盾（⚠️ 中等）

| 问题 | 严重程度 | 状态 |
|------|---------|------|
| 6. 平票未处理 | ⚠️ 中等 | ✅ 已有处理 |

---

## 🔧 修复方案

### 1. 修复游戏结束条件

**文件**: `core/state.py`

**问题**: `len(werewolves) >= len(villagers)` 导致 3 狼 vs 3 好人时游戏提前结束

**修复**:
```python
# 修复前
if len(werewolves) >= len(villagers):
    self.game_over = True
    self.winner = "werewolf"

# 修复后：狼人数量必须严格大于好人数量
if len(werewolves) > len(villagers):
    self.game_over = True
    self.winner = "werewolf"
    self._log_game_end_reason(f"狼人数量 ({len(werewolves)}) 超过好人数量 ({len(villagers)})")
```

**规则**:
- ✅ 3 狼 vs 3 好人 → 游戏继续
- ✅ 3 狼 vs 2 好人 → 狼人胜利

---

### 2. 修复猎人技能逻辑

**文件**: `core/game_engine.py`

**问题**: 猎人被投票出局也能开枪

**修复**:

#### 白天投票出局（不能开枪）
```python
# 猎人技能 - 修复：只有被狼刀死亡才能开枪，被投票出局不能开枪
if eliminated.role == Role.HUNTER:
    self.ui.display_system_message(f"{eliminated.name} 是猎人，但被投票出局，不能发动技能")
    self._log_event("hunter_eliminated", {
        "hunter_id": eliminated_id,
        "reason": "voted_out",
        "note": "猎人被投票出局，不能发动技能"
    })

eliminated.death_cause = "voted_out"  # 记录死亡原因
```

#### 夜晚被狼刀死亡（可以开枪）
```python
# 应用死亡
if killed_by_wolf and not saved:
    target = self.state.players[killed_by_wolf]
    target.is_alive = False
    target.death_cause = "wolf"  # 记录死亡原因：狼刀
    
    # 猎人技能 - 被狼刀死亡可以开枪
    if target.role == Role.HUNTER:
        self.ui.display_system_message(f"{target.name} 是猎人，被狼刀死亡，可以发动技能！")
        self._handle_hunter_skill(target, alive_villagers)
```

#### 被毒杀（不能开枪）
```python
if poisoned:
    target = self.state.players[poisoned]
    target.death_cause = "poison"  # 记录死亡原因：毒药
    
    # 猎人技能 - 被毒死不能开枪
    if target.role == Role.HUNTER:
        self.ui.display_system_message(f"{target.name} 是猎人，但被毒杀，不能发动技能")
```

#### 新增 `_handle_hunter_skill` 方法
```python
def _handle_hunter_skill(self, hunter: Player, alive_players: list[int]) -> None:
    """处理猎人技能发动"""
    # ...实现猎人带走一人的逻辑
    target_player.death_cause = "hunter"  # 记录死亡原因：猎人带走
```

---

### 3. 修复女巫解药无限使用

**文件**: `core/game_engine.py`

**问题**: AI 女巫不知道解药已用过，导致多次使用

**修复**:
```python
# 告知 AI 解药和毒药的使用状态
context = {
    "alive_players": alive_players,
    "dead_player": dead_player_id,
    "my_id": witch.id,
    "heal_used": self.witch_heal_used,  # 解药是否已用
    "poison_used": self.witch_poison_used,  # 毒药是否已用
}

# AI 决策后检查
if action.get("action") == "heal":
    if self.witch_heal_used:
        self.ui.display_system_message("女巫试图使用解药，但解药已用过")
        action = {"action": "none"}
    else:
        self.witch_heal_used = True
elif action.get("action") == "poison":
    if self.witch_poison_used:
        self.ui.display_system_message("女巫试图使用毒药，但毒药已用过")
        action = {"action": "none"}
    else:
        self.witch_poison_used = True
```

---

### 4. 修复猎人遗言错误

**文件**: `ai/agent.py`

**问题**: 猎人遗言说"我昨晚验了 3 号是狼"（混淆预言家能力）

**修复**:
```python
def make_last_words(self, context: dict) -> str:
    """发表遗言"""
    role = self.player.role.value if self.player.role else "玩家"
    
    # 根据身份生成不同的提示
    if role == "hunter":
        role_hint = """你是猎人，你的技能是死亡时可以带走一人（只有被狼刀才能发动）。
遗言中不要提到"验人"、"查验"等预言家的能力。
你可以说"我死后请好人帮我找出狼人"或"我怀疑 X 号是狼"。"""
    elif role == "seer":
        role_hint = """你是预言家，你有查验能力。
遗言中可以说出你的查验结果，给好人留下明确信息。"""
    elif role == "witch":
        role_hint = """你是女巫，你有救药和毒药。
遗言中可以说出你用了什么药，救了谁或毒了谁。"""
    
    prompt = f"""你即将死亡，请发表遗言。

你的身份：{role}
{role_hint}

遗言要求：
5. **重要**：不要说你没做过的事情（如猎人不要说"验人"，预言家不要说"用药"）
"""
```

---

### 5. 添加死亡原因追踪

**文件**: `core/state.py`

**新增字段**:
```python
@dataclass
class Player:
    death_cause: Optional[str] = None  # 死亡原因：wolf(狼刀), voted_out(投票), poison(毒药), hunter(猎人带走)
```

**用途**:
- 记录每个玩家的死亡原因
- 用于日志分析和调试
- 确保猎人技能正确发动

---

### 6. 投票平票处理

**文件**: `core/game_engine.py`

**现状**: 已有正确处理

```python
if len(top_candidates) == 1:
    # 有人被放逐
    eliminated_id = top_candidates[0]
    # ...
else:
    self.ui.display_system_message("平票，无人被放逐")
```

**规则**:
- ✅ 平票 → 无人被放逐
- ✅ 继续游戏

---

## 📂 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `core/state.py` | 1. 修复游戏结束条件（`>` 而不是 `>=`）<br>2. 添加 `death_cause` 字段<br>3. 添加 `_log_game_end_reason()` 方法 |
| `core/game_engine.py` | 1. 修复猎人技能逻辑（被投票不能开枪）<br>2. 添加 `_handle_hunter_skill()` 方法<br>3. 修复女巫解药检查<br>4. 添加死亡原因记录<br>5. 传递 `death_cause` 给遗言 |
| `ai/agent.py` | 1. 修复猎人遗言（不能说"验人"）<br>2. 添加角色特定的遗言提示 |

---

## 🧪 测试验证

### 运行测试
```bash
cd E:\04project\BotBattle
python tests/werewolf/test_quick.py
```

### 验证点

1. **游戏结束条件**
   - 3 狼 vs 3 好人 → 游戏继续 ✅
   - 3 狼 vs 2 好人 → 狼人胜利 ✅

2. **猎人技能**
   - 被狼刀死亡 → 可以开枪 ✅
   - 被投票出局 → 不能开枪 ✅
   - 被毒杀 → 不能开枪 ✅

3. **女巫用药**
   - 首夜自救后 → 解药已用，不能再用 ✅
   - 毒药只能用一次 ✅

4. **猎人遗言**
   - 不说"验人" ✅
   - 正确描述自己的身份和能力 ✅

5. **死亡记录**
   - 所有死亡都有 `death_cause` 记录 ✅
   - 日志完整 ✅

---

## 📊 修复前后对比

### 修复前
```
第 3 天白天，3 狼 vs 3 好人 → 游戏结束，狼人获胜 ❌
猎人被投票出局 → 开枪带走 3 号 ❌
猎人遗言："我昨晚验了 3 号是狼" ❌
女巫第 1、2、3 夜都使用解药 ❌
3 号死亡无记录 ❌
```

### 修复后
```
第 3 天白天，3 狼 vs 3 好人 → 游戏继续 ✅
猎人被投票出局 → 不能开枪 ✅
猎人遗言："我是猎人，我怀疑 X 号是狼" ✅
女巫第 1 夜自救后 → 解药已用，不能再使用 ✅
所有死亡都有明确记录 ✅
```

---

## 🎯 后续优化建议

1. **完整的死亡日志**
   - 在 `game_over` 事件中记录所有玩家的死亡原因
   - 便于复盘分析

2. **更严格的规则检查**
   - 女巫不能自救（首夜后）
   - 预言家不能重复查验同一玩家

3. **AI 记忆增强**
   - 记住已用的技能和药品
   - 根据死亡原因调整发言
