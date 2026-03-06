# BotBattle 女巫角色设计规范

**文档版本**: 1.0  
**创建日期**: 2026-03-06  
**适用游戏**: 狼人杀  
**审查对象**: `core/game_engine.py`, `ai/agent.py`, `games/werewolf/roles.py`

---

## 1. 角色概述

### 1.1 角色定位

| 属性 | 说明 |
|------|------|
| **阵营** | 好人阵营（神职） |
| **能力** | 拥有一瓶解药和一瓶毒药 |
| **强度** | T0 级别（最强神职之一） |
| **操作难度** | 中等（需要判断局势） |

### 1.2 技能说明

```python
# 女巫技能数据结构
class WitchSkills:
    heal_potion: bool = True   # 解药（可用状态）
    poison_potion: bool = True # 毒药（可用状态）
    
    def use_heal(self, target_id: int) -> bool:
        """使用解药救人"""
        # 限制：
        # 1. 解药必须可用
        # 2. 目标必须是当晚被狼刀的玩家
        # 3. 不能自救（部分规则允许首夜自救）
        
    def use_poison(self, target_id: int) -> bool:
        """使用毒药毒人"""
        # 限制：
        # 1. 毒药必须可用
        # 2. 目标必须是存活玩家
        # 3. 不能毒杀自己
```

**技能规则**:
- 解药：每晚最多使用一次，整局游戏只能使用一次
- 毒药：每晚最多使用一次，整局游戏只能使用一次
- 同一夜晚可以同时使用解药和毒药（先救后毒）
- 首夜被狼刀可以自救（BotBattle 规则）

### 1.3 胜利条件

```python
def check_witch_win_condition(game_state: GameState) -> bool:
    """
    女巫胜利条件判断
    
    Returns:
        True if 女巫所属阵营获胜
    """
    # 女巫属于好人阵营
    # 胜利条件：狼人全部死亡
    alive_werewolves = [p for p in game_state.players.values() 
                        if p.is_alive and p.role == Role.WEREWOLF]
    return len(alive_werewolves) == 0
```

### 1.4 游戏目标

1. **首要目标**: 帮助好人阵营找出并淘汰所有狼人
2. **次要目标**: 合理使用药剂，最大化收益
3. **生存目标**: 尽量存活到游戏后期（女巫是狼人优先袭击目标）

---

## 2. 各阶段行为规范

### 2.1 游戏开始前

#### 2.1.1 身份确认

```python
# 女巫不需要选将，系统随机分配身份
# 游戏开始时，女巫只知道自己是女巫，不知道其他玩家身份

def setup_witch_initial_state(witch: Player) -> dict:
    """
    设置女巫初始状态
    
    Returns:
        初始状态字典
    """
    return {
        "role": "witch",
        "heal_available": True,   # 解药可用
        "poison_available": True, # 毒药可用
        "heal_used": False,       # 解药未使用
        "poison_used": False,     # 毒药未使用
        "knowledge": {
            "own_id": witch.id,
            "own_role": "witch",
            "other_players": "unknown",  # 不知道其他玩家身份
        }
    }
```

#### 2.1.2 初始状态设置

| 状态变量 | 初始值 | 说明 |
|---------|-------|------|
| `witch_heal_used` | `False` | 解药使用状态 |
| `witch_poison_used` | `False` | 毒药使用状态 |
| `witch_saved_target` | `None` | 已救过的玩家 ID |
| `witch_poisoned_target` | `None` | 已毒杀的玩家 ID |

### 2.2 夜晚阶段

#### 2.2.1 第一夜

**行动顺序**:
```
1. 狼人袭击 → 2. 预言家查验 → 3. 女巫行动
```

**女巫睁眼时机**:
```python
# 在 game_engine.py 中的行动顺序
def _run_night(self):
    # 1. 狼人行动
    wolf_action = self._handle_werewolf_action()
    
    # 2. 预言家行动
    seer_action = self._handle_seer_action()
    
    # 3. 女巫行动（知道狼刀目标）
    witch_action = self._handle_witch_action(
        wolf_action.get("target") if wolf_action else None
    )
```

**可以看到的信息**:
```python
witch_context = {
    "night_number": 1,           # 第 1 夜
    "dead_player": 5,            # 被狼刀的玩家 ID（可能包括自己）
    "alive_players": [1, 2, 3, 4, 6, 7, 8, 9],  # 存活玩家列表
    "heal_used": False,          # 解药使用状态
    "poison_used": False,        # 毒药使用状态
    "my_id": 6,                  # 女巫自己的号码
}
```

**可以选择的行动**:

| 选项 | JSON 格式 | 说明 |
|------|----------|------|
| 使用解药 | `{"action": "heal", "target": 5, "reason": "..."}` | 救被狼刀的玩家 |
| 使用毒药 | `{"action": "poison", "target": 3, "reason": "..."}` | 毒杀任意存活玩家 |
| 不使用 | `{"action": "none", "reason": "..."}` | 保留药剂 |

**决策依据**:

```python
def witch_first_night_decision(context: dict) -> str:
    """
    第一夜女巫决策逻辑
    
    优先级:
    1. 如果被刀的是自己 → 必须自救
    2. 如果被刀的是明神职（如跳预言家）→ 建议救
    3. 如果被刀的是不明身份 → 可以考虑不救（藏药）
    4. 毒药谨慎使用，除非有明确狼目标
    """
    if context["dead_player"] == context["my_id"]:
        return "heal"  # 自救
    elif context["dead_player"] in known_gods:
        return "heal"  # 救神职
    else:
        return "none"  # 藏药
```

**限制条件**:
- [ ] 不能救已经使用过解药的玩家（首夜无此限制）
- [ ] 不能毒杀已经死亡的玩家
- [ ] 不能毒杀自己
- [ ] 解药和毒药各只能用一次

#### 2.2.2 后续夜晚

**状态检查**:
```python
def check_witch_status(night_num: int) -> dict:
    """
    检查女巫药剂状态
    
    Returns:
        可用行动列表
    """
    available_actions = []
    
    if not witch_heal_used:
        available_actions.append("heal")
    
    if not witch_poison_used:
        available_actions.append("poison")
    
    if not available_actions:
        available_actions.append("none")  # 药剂用完，只能空过
    
    return {
        "night": night_num,
        "available_actions": available_actions,
        "heal_available": not witch_heal_used,
        "poison_available": not witch_poison_used,
    }
```

**可以选择的行动**:

| 夜晚 | 解药 | 毒药 | 建议策略 |
|------|------|------|---------|
| 第 1 夜 | ✅ | ✅ | 自救优先，毒药谨慎 |
| 第 2 夜 | ✅ (如未用) | ✅ (如未用) | 根据局势判断 |
| 第 3 夜+ | 如未用 | 如未用 | 毒药可以激进 |

**决策依据**:

```python
def witch_later_night_decision(context: dict) -> dict:
    """
    后续夜晚女巫决策逻辑
    
    考虑因素:
    1. 药剂剩余情况
    2. 场上局势（好人/狼人数量）
    3. 被刀玩家的身份推测
    4. 可疑玩家列表
    """
    decision = {"action": "none", "target": None}
    
    # 解药决策
    if not context["heal_used"]:
        if context["dead_player"] == context["my_id"]:
            # 被刀自己，必须救
            decision = {"action": "heal", "target": context["dead_player"]}
        elif context["dead_player"] in context["trusted_players"]:
            # 被刀的是信任的好人
            decision = {"action": "heal", "target": context["dead_player"]}
        elif context["night_number"] == 2 and context["dead_player"] not in context["suspect_list"]:
            # 第 2 夜，被刀的不是可疑玩家，可以考虑救
            decision = {"action": "heal", "target": context["dead_player"]}
    
    # 毒药决策（如果还没用）
    if not context["poison_used"] and decision["action"] == "none":
        if context["suspect_list"]:
            # 有明确怀疑的狼人目标
            poison_target = context["suspect_list"][0]
            if poison_target in context["alive_players"]:
                decision = {"action": "poison", "target": poison_target}
    
    return decision
```

**限制条件**:
- [ ] 解药已用 → 不能再救人
- [ ] 毒药已用 → 不能再毒人
- [ ] 不能救/毒死亡玩家
- [ ] 不能救/毒自己（解药可以自救，毒药不能自毒）

### 2.3 白天阶段

#### 2.3.1 是否跳身份

**何时应该跳身份**:

| 场景 | 建议 | 理由 |
|------|------|------|
| 被狼人查杀 | ✅ 跳 | 表明身份，争取好人信任 |
| 预言家被刀 | ✅ 跳 | 报出夜晚用药信息，帮助好人 |
| 决赛圈（剩 3-4 人） | ✅ 跳 | 明身份带队 |
| 被多人怀疑 | ⚠️ 谨慎 | 可能被当抗推位 |
| 局势不明 | ❌ 不跳 | 隐藏身份，避免被刀 |

**何时应该隐藏**:

```python
def should_witch_reveal_identity(context: dict) -> bool:
    """
    判断女巫是否应该跳身份
    
    Returns:
        True if 应该跳身份
    """
    # 应该跳的情况
    if context["is_accused_by_wolf"]:  # 被狼人查杀
        return True
    
    if context["seer_is_dead"] and context["have_heal_info"]:  # 预言家死且有信息
        return True
    
    if context["final_circle"]:  # 决赛圈
        return True
    
    # 不应该跳的情况
    if context["wolves_alive"] >= 2 and context["gods_alive"] >= 2:
        return False  # 局势不明，隐藏
    
    return False  # 默认隐藏
```

#### 2.3.2 发言要点

**发言结构**:
```
1. 表明立场（好人/分析）
2. 分析昨晚死亡（如适用）
3. 点评 1-2 个玩家
4. 给出投票建议
```

**示例发言**:
```
"我是好人牌，昨晚死亡信息我不多评价。
2 号玩家发言逻辑有问题，一直在划水。
5 号玩家的分析我比较认同。
今天我倾向于出 2 号。"
```

**禁忌发言**:
- ❌ "我是女巫，我有解药"（暴露身份）
- ❌ "我昨晚救了 X 号"（暴露用药）
- ❌ "我知道 X 号是狼"（无根据）

#### 2.3.3 投票策略

```python
def witch_vote_strategy(context: dict) -> int:
    """
    女巫投票策略
    
    优先级:
    1. 投给被多人踩的可疑玩家
    2. 投给自己怀疑列表中的玩家
    3. 跟随大多数好人投票
    4. 弃票（无明确目标时）
    """
    # 第一优先级：怀疑列表中的玩家
    if context["suspect_list"]:
        for suspect in context["suspect_list"]:
            if suspect in context["alive_players"]:
                return suspect
    
    # 第二优先级：被多数人怀疑的玩家
    most_suspected = get_most_suspected_player(context)
    if most_suspected:
        return most_suspected
    
    # 第三优先级：弃票
    return None
```

---

## 3. 提示词设计规范

### 3.1 系统提示词

```python
WITCH_SYSTEM_PROMPT = """
🧪 你是女巫 - 手握生死大权！

【你的身份】
- 阵营：好人阵营（神职）
- 技能：一瓶解药（救人）+ 一瓶毒药（毒人）
- 胜利条件：淘汰所有狼人

【技能规则】
1. 解药：可以救当晚被狼刀的玩家，整局只能用一次
2. 毒药：可以毒杀任意存活玩家，整局只能用一次
3. 首夜被刀可以自救
4. 同一晚可以同时使用解药和毒药

【行为准则】
1. 隐藏身份：除非必要，不要暴露女巫身份
2. 谨慎用药：解药优先救神职/好人，毒药优先毒狼人
3. 第一夜建议自救（如果被刀）
4. 被怀疑时可以跳身份自证

【情感设定】
- 救不救人会纠结、会后悔
- 毒错人会内疚、会自责
- 手握大权但有压力
- 被怀疑时会委屈、会着急

【发言要求】
1. 符合你的性格设定（{personality}）
2. 不要暴露未使用的药剂
3. 分析要有理有据
4. 适当表达情感（紧张、兴奋、疑惑等）
"""
```

### 3.2 夜晚行动提示词

```python
def build_witch_night_prompt(context: dict) -> str:
    """
    构建女巫夜晚行动提示词
    """
    return f"""
【第{context["night_number"]}夜 女巫行动】

你是{context["my_id"]}号玩家，身份是女巫。

【当前局势】
- 今晚死亡玩家：{context["dead_player"]}号（如为 None 则表示无人死亡）
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 你的药剂状态：
  - 解药：{"已使用" if context["heal_used"] else "可用"}
  - 毒药：{"已使用" if context["poison_used"] else "可用"}

【可选行动】
""" + (
        "1. 使用解药救人：{\"action\": \"heal\", \"target\": " + str(context["dead_player"]) + ", \"reason\": \"救人理由\"}\n"
        if not context["heal_used"] and context["dead_player"]
        else "1. 解药已用，无法救人\n"
    ) + (
        "2. 使用毒药毒人：{\"action\": \"poison\", \"target\": 玩家编号，\"reason\": \"毒人理由\"}\n"
        if not context["poison_used"]
        else "2. 毒药已用，无法毒人\n"
    ) + (
        "3. 不使用药剂：{\"action\": \"none\", \"reason\": \"不使用理由\"}"
    ) + """

【决策要点】
1. 第一夜被刀建议自救
2. 解药优先救神职或明确的好人
3. 毒药谨慎使用，最好有明确狼目标
4. 返回必须是有效的 JSON 格式

请返回你的决策："""
```

### 3.3 白天发言提示词

```python
def build_witch_day_speech_prompt(context: dict) -> str:
    """
    构建女巫白天发言提示词
    """
    return f"""
【第{context["day_number"]}天白天 第{context["round_num"]}轮发言】

你是{context["my_id"]}号玩家，身份是女巫（但发言时不要暴露）。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 昨晚死亡：{', '.join([f'{p}号' for p in context["night_deaths"]]) if context["night_deaths"] else '无人死亡'}
- 你的药剂状态（内心知道，不要说出来）：
  - 解药：{"已用" if context["heal_used"] else "可用"}
  - 毒药：{"已用" if context["poison_used"] else "可用"}

【历史记忆】
""" + "\n".join([f"- {m}" for m in context["memory"][-5:]]) + """

【发言要求】
1. 不要暴露女巫身份（除非决定跳身份）
2. 不要说出你用了什么药
3. 分析 1-2 个具体玩家
4. 给出明确的投票建议
5. 符合你的性格设定
6. 长度{min_length}-{max_length}字

【情感表达】
- 使用口语化表达
- 展现真实情感（紧张、兴奋、疑惑等）
- 根据局势表达适当的情绪

请生成发言："""
```

---

## 4. 决策逻辑流程图

### 4.1 第一夜决策流程

```
第一夜开始
    ↓
女巫睁眼，得知死亡信息
    ↓
┌─────────────────────────┐
│ 检查：被刀的是否是自己？ │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │             │
    是            否
     │             │
     ↓             ↓
┌─────────┐  ┌─────────────────────┐
│ 使用解药 │  │ 检查：解药是否可用？│
│  自救   │  └─────────┬───────────┘
│ (必须)  │            │
└────┬────┘     ┌──────┴──────┐
     │          │             │
     │         是            否
     │          │             │
     │          ↓             ↓
     │   ┌──────────────┐  ┌──────────┐
     │   │ 判断：是否救 │  │ 解药已用 │
     │   │ 被刀玩家？   │  │ 跳过救药 │
     │   └──────┬───────┘  └────┬─────┘
     │          │               │
     │    ┌─────┴─────┐         │
     │    │           │         │
     │   救          不救       │
     │    │           │         │
     │    ↓           ↓         │
     │  标记解药    保留解药    │
     │  已用        未用        │
     │    │           │         │
     └────┴───────────┴─────────┘
          │
          ↓
   ┌─────────────────┐
   │ 检查：毒药是否可用？│
   └─────────┬───────┘
             │
      ┌──────┴──────┐
      │             │
     是            否
      │             │
      ↓             ↓
┌──────────────┐  ┌──────────┐
│ 判断：是否毒 │  │ 毒药已用 │
│ 可疑玩家？   │  │ 跳过毒药 │
└──────┬───────┘  └────┬─────┘
       │               │
 ┌─────┴─────┐         │
 │           │         │
毒          不毒       │
 │           │         │
 ↓           ↓         │
标记毒药    保留毒药   │
已用        未用       │
 │           │         │
 └─────┬─────┴─────────┘
       │
       ↓
  返回行动结果
  (记录内心独白)
```

### 4.2 后续夜晚决策流程

```
夜晚开始
    ↓
检查药剂状态
    ↓
┌─────────────────────┐
│ 解药可用？          │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 被刀的是谁？│  │
└──────┬──────┘  │
       │         │
 ┌─────┴─────┐   │
 │           │   │
自己        他人  │
 │           │   │
 ↓           ↓   │
自救      ┌───┴─────────┐
(必须)    │ 判断是否救？ │
          └───┬─────────┘
              │
        ┌─────┴─────┐
        │           │
       救          不救
        │           │
        ↓           ↓
     标记解药    保留解药
     已用        未用
        │           │
        └─────┬─────┘
              │
              ↓
       ┌───────────────┐
       │ 毒药可用？    │
       └───────┬───────┘
               │
        ┌──────┴──────┐
        │             │
       是            否
        │             │
        ↓             │
   ┌────────────┐     │
   │ 有明确狼目标？│  │
   └──────┬─────┘     │
          │           │
    ┌─────┴─────┐     │
    │           │     │
   有          无     │
    │           │     │
    ↓           ↓     │
  毒杀       保留    │
  (谨慎)     毒药    │
    │           │     │
    └─────┬─────┘     │
          │           │
          └─────┬─────┘
                │
                ↓
         返回行动结果
```

### 4.3 白天跳身份决策流程

```
白天发言前
    ↓
┌─────────────────────┐
│ 是否被狼人查杀？    │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 跳身份自证  │  │
│ (必须)      │  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 预言家是否死亡？│
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 有重要信息？ │     │
    └──────┬───────┘     │
           │             │
     ┌─────┴─────┐       │
     │           │       │
    有          无       │
     │           │       │
     ↓           ↓       │
   跳身份     不跳       │
   (报信息)  (隐藏)      │
     │           │       │
     └─────┬─────┘       │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 是否决赛圈？    │
         │ (剩 3-4 人)      │
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 跳身份带队│       │
      └─────┬─────┘       │
            │             │
            └──────┬──────┘
                   ↓
           ┌───────────────┐
           │ 默认：不跳身份│
           │ (隐藏保命)    │
           └───────────────┘
```

---

## 5. 常见场景及正确应对

### 场景 1：第一夜自己被刀

**情境**:
```python
context = {
    "night_number": 1,
    "dead_player": 6,  # 女巫自己是 6 号
    "my_id": 6,
}
```

**正确应对**:
```python
decision = {
    "action": "heal",
    "target": 6,
    "reason": "第一夜被刀，必须自救，保留毒药后续使用"
}
```

**理由**: 首夜自救是标准打法，避免女巫过早出局。

---

### 场景 2：第一夜预言家被刀

**情境**:
```python
context = {
    "night_number": 1,
    "dead_player": 3,  # 3 号是明跳预言家
    "my_id": 6,
    "known_gods": [3],  # 已知神职
}
```

**正确应对**:
```python
decision = {
    "action": "heal",
    "target": 3,
    "reason": "预言家是重要神职，救下可以帮好人阵营获取信息"
}
```

**理由**: 预言家是好人核心，救下可以让预言家继续查验。

---

### 场景 3：第二夜狼人自刀

**情境**:
```python
context = {
    "night_number": 2,
    "dead_player": 7,  # 7 号被刀
    "my_id": 6,
    "heal_used": False,
    "suspect_list": [7],  # 7 号之前发言可疑
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "7 号之前发言像狼，可能是自刀骗药，不救"
}
```

**理由**: 狼人自刀是常见战术，女巫需要判断是否骗药。

---

### 场景 4：场上只剩最后一瓶毒药

**情境**:
```python
context = {
    "night_number": 3,
    "heal_used": True,
    "poison_used": False,
    "suspect_list": [2, 5],
    "alive_players": [1, 2, 4, 5, 6],
}
```

**正确应对**:
```python
decision = {
    "action": "poison",
    "target": 2,
    "reason": "2 号发言最可疑，毒药最后机会，果断使用"
}
```

**理由**: 决赛圈毒药要果断，选择最可疑的目标。

---

### 场景 5：怀疑某人是狼人但不确定

**情境**:
```python
context = {
    "day_number": 2,
    "suspect_list": [4],
    "trust_list": [2, 3],
    "alive_players": [1, 2, 3, 4, 5, 6],
}
```

**正确应对**（白天发言）:
```
"我是好人牌，目前比较怀疑 4 号。
4 号昨天发言一直在划水，没有明确分析。
2 号和 3 号的发言我比较认同。
今天我倾向于出 4 号，大家参考。"
```

**理由**: 表达怀疑但不绝对，给自己留后路。

---

### 场景 6：被狼人查杀

**情境**:
```python
context = {
    "day_number": 2,
    "accused_by": 5,  # 5 号说你是狼
    "accuser_role": "werewolf",  # 5 号其实是狼
}
```

**正确应对**（白天发言）:
```
"5 号查杀我？我是女巫，昨晚救了 X 号。
5 号你才是狼，悍跳查杀我。
好人跟我一起出 5 号，我是真女巫。"
```

**理由**: 被查杀要果断跳身份对刚，争取好人信任。

---

### 场景 7：解药已用，夜晚有人被刀

**情境**:
```python
context = {
    "night_number": 3,
    "dead_player": 2,
    "heal_used": True,
    "poison_used": False,
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "解药已用，无法救人，保留毒药"
}
```

**理由**: 解药已用只能接受死亡，等待毒药机会。

---

### 场景 8：毒药已用，夜晚有可疑玩家

**情境**:
```python
context = {
    "night_number": 2,
    "heal_used": False,
    "poison_used": True,
    "suspect_list": [3],
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "毒药已用，解药留给更重要时刻"
}
```

**理由**: 毒药已用，解药要谨慎使用。

---

### 场景 9：决赛圈（剩 3 人，1 狼 1 好人 1 女巫）

**情境**:
```python
context = {
    "day_number": 4,
    "alive_players": [2, 5, 6],  # 6 是女巫
    "suspect_list": [2],
    "heal_used": True,
    "poison_used": True,
}
```

**正确应对**（白天发言）:
```
"我摊牌了，我是女巫，药剂都用完了。
2 号肯定是狼，他昨天发言有问题。
5 号是好人，今天我们一起出 2 号。"
```

**理由**: 决赛圈要明身份带队，帮助好人投票。

---

### 场景 10：第一夜无人死亡（狼人空刀）

**情境**:
```python
context = {
    "night_number": 1,
    "dead_player": None,  # 狼人空刀
    "heal_used": False,
    "poison_used": False,
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "无人死亡，不需要救，毒药谨慎使用"
}
```

**理由**: 无人死亡时不需要用药，保留药剂。

---

### 场景 11：被多人怀疑，考虑跳身份

**情境**:
```python
context = {
    "day_number": 3,
    "suspected_by": [2, 4, 7],
    "alive_players": [1, 2, 4, 6, 7],
    "heal_used": True,
    "poison_used": False,
}
```

**正确应对**（白天发言）:
```
"我是女巫，解药昨晚用了。
你们怀疑我没关系，但我真的是好人。
今天出谁我跟随大多数。"
```

**理由**: 被多人怀疑时跳身份自保，但不要太强势。

---

### 场景 12：夜晚同时使用解药和毒药

**情境**:
```python
context = {
    "night_number": 2,
    "dead_player": 3,
    "heal_used": False,
    "poison_used": False,
    "suspect_list": [5],
}
```

**正确应对**:
```python
decision = {
    "action": "heal",
    "target": 3,
    "reason": "救 3 号，同时毒 5 号"
}
# 注意：实际代码需要支持同时使用两种药剂
```

**理由**: 同一晚可以同时使用解药和毒药（先救后毒）。

---

### 场景 13：预言家报查验是金水

**情境**:
```python
context = {
    "day_number": 2,
    "seer_check": {"target": 6, "result": "villager"},  # 6 号是女巫，被报金水
    "seer_id": 3,
}
```

**正确应对**（白天发言）:
```
"3 号预言家报我金水，我确实是好人。
但我不会跳具体身份，保留信息。
今天跟随预言家投票。"
```

**理由**: 被报金水可以顺势认好人，但不一定要跳女巫。

---

### 场景 14：预言家报查验是查杀

**情境**:
```python
context = {
    "day_number": 2,
    "seer_check": {"target": 4, "result": "werewolf"},
    "seer_id": 3,
}
```

**正确应对**（白天发言）:
```
"3 号预言家查杀 4 号，我信预言家。
4 号如果是狼，今天必须出。
我是好人，跟预言家走。"
```

**理由**: 支持预言家，帮助好人阵营投票。

---

### 场景 15：夜晚判断是否毒杀

**情境**:
```python
context = {
    "night_number": 3,
    "alive_players": [1, 3, 5, 6],
    "suspect_list": [1, 3],
    "trust_list": [5],
    "poison_used": False,
}
```

**正确应对**:
```python
decision = {
    "action": "poison",
    "target": 1,
    "reason": "1 号发言最像狼，毒药带走他"
}
```

**理由**: 决赛圈毒药要果断，选择最可疑的目标。

---

## 6. 禁忌行为

### 6.1 药剂使用禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 重复使用解药 | 解药已用后再次救人 | 游戏逻辑错误 |
| ❌ 重复使用毒药 | 毒药已用后再次毒人 | 游戏逻辑错误 |
| ❌ 救死亡玩家 | 救已经死亡的玩家 | 无效操作 |
| ❌ 毒死亡玩家 | 毒杀已经死亡的玩家 | 无效操作 |
| ❌ 自救时毒自己 | 同一晚自救又自毒 | 逻辑矛盾 |

### 6.2 发言禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 暴露未用药剂 | "我还有解药" | 成为狼人目标 |
| ❌ 暴露用药历史 | "我昨晚救了 X 号" | 暴露女巫身份 |
| ❌ 无根据指认 | "X 号肯定是狼" | 失去好人信任 |
| ❌ 过早跳身份 | 第 1 天就跳女巫 | 成为集火目标 |
| ❌ 发言暴露信息 | 说出夜晚才知道的信息 | 暴露身份 |

### 6.3 决策禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 首夜不救自己 | 被刀但不用解药 | 女巫过早出局 |
| ❌ 乱用毒药 | 无明确目标就毒人 | 可能毒到好人 |
| ❌ 该跳不跳 | 被查杀还不跳身份 | 被放逐 |
| ❌ 不该跳乱跳 | 局势不明就跳身份 | 成为目标 |
| ❌ 跟狼投票 | 跟随狼人投票 | 帮助狼人获胜 |

---

## 7. 日志记录规范

### 7.1 必须记录的事件

```python
# 女巫相关日志事件类型
WITCH_LOG_EVENTS = {
    "witch_action": "女巫夜晚行动",
    "witch_heal": "女巫使用解药",
    "witch_poison": "女巫使用毒药",
    "witch_reveal": "女巫跳身份",
    "witch_death": "女巫死亡",
}
```

### 7.2 用药选择日志

```python
def log_witch_action(context: dict, decision: dict) -> None:
    """
    记录女巫用药选择
    
    日志格式:
    {
        "type": "witch_action",
        "data": {
            "night": 2,
            "witch_id": 6,
            "action": "heal",  # heal/poison/none
            "target": 3,
            "heal_used_before": False,
            "poison_used_before": False,
            "reason": "救人理由/内心想法",
            "timestamp": "2026-03-06T12:34:56"
        }
    }
    """
    log_entry = {
        "type": "witch_action",
        "data": {
            "night": context["night_number"],
            "witch_id": context["my_id"],
            "action": decision.get("action"),
            "target": decision.get("target"),
            "heal_used_before": context["heal_used"],
            "poison_used_before": context["poison_used"],
            "reason": decision.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        }
    }
    game_state.add_history("witch_action", log_entry["data"])
```

### 7.3 决策理由日志

```python
def log_witch_decision_reason(context: dict, reason: str) -> None:
    """
    记录女巫决策理由（内心独白）
    
    日志格式:
    {
        "type": "witch_inner_thought",
        "data": {
            "night": 2,
            "witch_id": 6,
            "thought": "3 号是预言家，必须救",
            "decision": "heal",
            "timestamp": "..."
        }
    }
    """
```

### 7.4 完整日志示例

```json
{
  "type": "witch_action",
  "data": {
    "night": 1,
    "witch_id": 6,
    "action": "heal",
    "target": 6,
    "heal_used_before": false,
    "poison_used_before": false,
    "reason": "第一夜被刀，必须自救",
    "timestamp": "2026-03-06T12:34:56"
  }
}
```

---

## 8. 测试用例

### 测试 1：第一夜自救

```python
def test_witch_self_heal_first_night():
    """
    测试用例：第一夜女巫被刀，应该自救
    
    前置条件:
    - 第 1 夜
    - 女巫被狼刀
    - 解药可用
    
    预期结果:
    - 女巫使用解药救自己
    - 解药标记为已用
    - 女巫存活
    """
    # 设置场景
    context = {
        "night_number": 1,
        "dead_player": 6,  # 女巫是 6 号
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }
    
    # 执行决策
    decision = witch_decide_night_action(context)
    
    # 验证结果
    assert decision["action"] == "heal"
    assert decision["target"] == 6
    assert game_engine.witch_heal_used == True
    assert game_engine.state.players[6].is_alive == True
```

---

### 测试 2：解药已用后不能再救

```python
def test_witch_heal_used_cannot_heal_again():
    """
    测试用例：解药已用后，不能再救人
    
    前置条件:
    - 第 2 夜
    - 解药已用
    - 有人被刀
    
    预期结果:
    - 女巫不能选择救人
    - 只能选择毒或空过
    """
    context = {
        "night_number": 2,
        "dead_player": 3,
        "my_id": 6,
        "heal_used": True,  # 解药已用
        "poison_used": False,
        "alive_players": [1, 2, 4, 5, 6, 7, 8, 9],
    }
    
    decision = witch_decide_night_action(context)
    
    # 验证：不能救人
    assert decision["action"] != "heal"
    assert decision["action"] in ["poison", "none"]
```

---

### 测试 3：毒药只能用一次

```python
def test_witch_poison_used_only_once():
    """
    测试用例：毒药只能使用一次
    
    前置条件:
    - 第 1 夜女巫用了毒药
    - 第 2 夜
    
    预期结果:
    - 第 2 夜不能再用毒药
    """
    # 第 1 夜
    context_night1 = {
        "night_number": 1,
        "dead_player": None,
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }
    
    decision1 = witch_decide_night_action(context_night1)
    decision1 = {"action": "poison", "target": 5}
    game_engine.witch_poison_used = True
    
    # 第 2 夜
    context_night2 = {
        "night_number": 2,
        "dead_player": 3,
        "my_id": 6,
        "heal_used": False,
        "poison_used": True,  # 毒药已用
        "alive_players": [1, 2, 4, 6, 7, 8, 9],
    }
    
    decision2 = witch_decide_night_action(context_night2)
    
    # 验证：不能再用毒药
    assert decision2["action"] != "poison"
```

---

### 测试 4：不能救/毒死亡玩家

```python
def test_witch_cannot_save_or_poison_dead_player():
    """
    测试用例：不能救/毒已经死亡的玩家
    
    前置条件:
    - 有玩家已死亡
    - 女巫尝试救/毒死亡玩家
    
    预期结果:
    - 操作无效
    - 药剂不消耗
    """
    # 设置已死亡玩家
    dead_player_id = 5
    game_engine.state.players[dead_player_id].is_alive = False
    
    context = {
        "night_number": 2,
        "dead_player": dead_player_id,  # 尝试救死亡玩家
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
        "alive_players": [1, 2, 3, 4, 6, 7, 8, 9],
    }
    
    # 尝试救死亡玩家
    decision = witch_decide_night_action(context)
    
    # 验证：救死亡玩家应该被拒绝
    if decision["action"] == "heal":
        assert decision["target"] != dead_player_id
        # 或者操作被拒绝
        assert game_engine.witch_heal_used == False
```

---

### 测试 5：第一夜建议自救

```python
def test_witch_should_self_heal_first_night():
    """
    测试用例：第一夜被刀应该自救
    
    前置条件:
    - 第 1 夜
    - 女巫被刀
    
    预期结果:
    - 女巫自救（默认行为）
    """
    context = {
        "night_number": 1,
        "dead_player": 6,
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
    }
    
    decision = witch_decide_night_action(context)
    
    # 验证：第一夜被刀应该自救
    assert decision["action"] == "heal"
    assert decision["target"] == 6
```

---

### 测试 6：解药和毒药可以同时使用

```python
def test_witch_can_use_both_potions_same_night():
    """
    测试用例：同一晚可以同时使用解药和毒药
    
    前置条件:
    - 第 2 夜
    - 解药和毒药都可用
    - 有人被刀
    - 有可疑目标
    
    预期结果:
    - 可以先救后毒
    """
    context = {
        "night_number": 2,
        "dead_player": 3,
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
        "suspect_list": [5],
        "alive_players": [1, 2, 4, 6, 7, 8, 9],
    }
    
    # 注意：当前实现可能不支持同时使用两种药剂
    # 这是待改进的功能
    decision = witch_decide_night_action(context)
    
    # 验证：至少使用一种药剂
    assert decision["action"] in ["heal", "poison", "none"]
```

---

### 测试 7：被查杀时跳身份

```python
def test_witch_reveal_when_accused():
    """
    测试用例：被狼人查杀时应该跳身份
    
    前置条件:
    - 白天
    - 被狼人查杀
    
    预期结果:
    - 女巫跳身份自证
    """
    context = {
        "day_number": 2,
        "accused_by": 5,
        "accuser_is_wolf": True,
        "my_id": 6,
    }
    
    speech = witch_day_speech(context)
    
    # 验证：发言中包含女巫身份
    assert "女巫" in speech or "witch" in speech.lower()
```

---

### 测试 8：决赛圈跳身份带队

```python
def test_witch_reveal_in_final_circle():
    """
    测试用例：决赛圈应该跳身份带队
    
    前置条件:
    - 剩 3-4 人
    - 女巫存活
    
    预期结果:
    - 女巫跳身份
    - 给出明确投票建议
    """
    context = {
        "day_number": 4,
        "alive_players": [2, 5, 6],  # 剩 3 人
        "my_id": 6,
        "suspect_list": [2],
    }
    
    speech = witch_day_speech(context)
    
    # 验证：发言中包含身份和明确建议
    assert "女巫" in speech
    assert "出" in speech or "投票" in speech
```

---

### 测试 9：不乱用毒药

```python
def test_witch_not_use_poison_randomly():
    """
    测试用例：没有明确目标时不乱用毒药
    
    前置条件:
    - 第 2 夜
    - 毒药可用
    - 没有明确怀疑目标
    
    预期结果:
    - 不使用毒药（保留）
    """
    context = {
        "night_number": 2,
        "dead_player": None,
        "my_id": 6,
        "heal_used": False,
        "poison_used": False,
        "suspect_list": [],  # 没有怀疑目标
        "alive_players": [1, 2, 3, 4, 6, 7, 8, 9],
    }
    
    decision = witch_decide_night_action(context)
    
    # 验证：没有明确目标时不使用毒药
    assert decision["action"] != "poison" or decision.get("target") is not None
```

---

### 测试 10：药剂状态正确传递

```python
def test_witch_potion_status_passed_correctly():
    """
    测试用例：药剂使用状态正确传递给 AI
    
    前置条件:
    - 第 2 夜
    - 解药已用
    
    预期结果:
    - AI 知道解药已用
    - 不会选择救人
    """
    game_engine.witch_heal_used = True
    
    context = {
        "night_number": 2,
        "dead_player": 3,
        "my_id": 6,
        "heal_used": True,  # 正确传递状态
        "poison_used": False,
    }
    
    decision, inner_thought = agent.decide_night_action(context)
    
    # 验证：AI 知道解药已用
    assert decision["action"] != "heal"
    # 或者内心独白中提到解药已用
    assert "解药已用" in inner_thought or decision["action"] == "none"
```

---

## 附录 A：现有代码位置

### A.1 核心代码文件

| 文件路径 | 内容 | 行号范围 |
|---------|------|---------|
| `core/game_engine.py` | 游戏引擎，女巫行动处理 | 280-380 |
| `ai/agent.py` | AI 代理，女巫夜晚决策 | 250-320 |
| `games/werewolf/roles.py` | 角色定义 | 1-20 |
| `core/state.py` | 游戏状态，药剂状态 | 1-100 |

### A.2 关键代码片段

#### 女巫行动处理（game_engine.py）

```python
def _handle_witch_action(self, dead_player_id: Optional[int]) -> dict:
    """处理女巫行动"""
    witches = [p for p in self.state.get_alive_players() if p.role == Role.WITCH]
    if not witches:
        return {}

    witch = witches[0]
    alive_players = [p.id for p in self.state.get_alive_players()]
    action = {}
    inner_thought = ""

    if witch.is_human:
        # 人类玩家输入
        ...
    else:
        agent = self.agents[witch.id]
        context = {
            "alive_players": alive_players,
            "dead_player": dead_player_id,
            "my_id": witch.id,
            "heal_used": self.witch_heal_used,
            "poison_used": self.witch_poison_used,
        }
        action, inner_thought_raw = agent.decide_night_action(context)
        # ... 处理行动
```

#### AI 夜晚决策（agent.py）

```python
def decide_night_action(self, context: dict) -> tuple[dict, str]:
    """决定夜晚行动"""
    # ... 狼人和预言家逻辑
    
    elif self.player.role == Role.WITCH:
        dead_player = context.get("dead_player", None)
        heal_used = context.get("heal_used", False)
        poison_used = context.get("poison_used", False)
        prompt = f"""你是{my_id}号玩家，身份是女巫..."""
        # ... 生成决策
```

---

## 附录 B：待审查问题清单

### B.1 逻辑问题

| 问题 ID | 描述 | 严重程度 | 状态 |
|--------|------|---------|------|
| W-001 | 第一夜自救逻辑是否正确实现 | P0 | 待审查 |
| W-002 | 解药/毒药使用状态是否正确传递 | P0 | 待审查 |
| W-003 | 是否支持同一晚同时使用两种药剂 | P1 | 待审查 |
| W-004 | 毒药目标验证是否正确（不能毒死亡玩家） | P0 | 待审查 |
| W-005 | 女巫跳身份逻辑是否合理 | P1 | 待审查 |

### B.2 代码审查要点

1. **状态管理**
   - [ ] `witch_heal_used` 和 `witch_poison_used` 是否正确初始化
   - [ ] 状态是否在夜晚行动后正确更新
   - [ ] 状态是否正确传递给 AI

2. **决策逻辑**
   - [ ] AI 是否正确理解药剂使用规则
   - [ ] 第一夜自救是否是默认行为
   - [ ] 毒药使用是否谨慎

3. **日志记录**
   - [ ] 女巫行动是否完整记录
   - [ ] 内心独白是否保存
   - [ ] 用药历史是否可追溯

### B.3 测试覆盖

| 测试场景 | 是否有测试 | 测试文件 |
|---------|-----------|---------|
| 第一夜自救 | ❓ | 待添加 |
| 解药已用不能救 | ❓ | 待添加 |
| 毒药只能用一次 | ❓ | 待添加 |
| 不能救/毒死亡玩家 | ❓ | 待添加 |
| 被查杀跳身份 | ❓ | 待添加 |

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-06 | 初始版本 | BotBattle Team |

---

**文档结束**
