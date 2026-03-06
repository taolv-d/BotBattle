# BotBattle 猎人角色设计规范

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
| **能力** | 死亡时可以开枪带走一名玩家 |
| **强度** | T1 级别（强力追轮次神职） |
| **操作难度** | 中等（需要判断开枪时机和目标） |

### 1.2 技能说明

```python
# 猎人技能数据结构
class HunterSkills:
    can_shoot: bool = True  # 是否可以开枪
    
    def shoot_on_death(self, target_id: int) -> bool:
        """
        死亡时开枪带走一名玩家

        Args:
            target_id: 被带走的目标 ID

        Returns:
            True if 开枪成功

        限制:
        1. 只能在死亡时发动
        2. 不能带走自己
        3. 不能带走已死亡玩家
        4. 被女巫毒杀不能开枪（部分规则）
        """
        pass
```

**技能规则**:
- 开枪时机：猎人死亡时立即发动（遗言阶段）
- 开枪对象：任意存活玩家（不能是自己）
- 开枪限制：被女巫毒杀不能开枪（BotBattle 规则）
- 开枪选择：可以选择不开枪（空枪）

**死亡原因与开枪权限**:

| 死亡原因 | 是否可以开枪 | 说明 |
|---------|-------------|------|
| 被狼刀 | ✅ 可以 | 正常死亡，可以开枪 |
| 被投票放逐 | ✅ 可以 | 正常死亡，可以开枪 |
| 被女巫毒杀 | ❌ 不能 | 被毒杀不能开枪 |
| 自爆（如果是狼） | ❌ 不能 | 自爆不能开枪 |

### 1.3 胜利条件

```python
def check_hunter_win_condition(game_state: GameState) -> bool:
    """
    猎人胜利条件判断

    Returns:
        True if 猎人所属阵营获胜
    """
    # 猎人属于好人阵营
    # 胜利条件：狼人全部死亡
    alive_werewolves = [p for p in game_state.players.values()
                        if p.is_alive and p.role == Role.WEREWOLF]
    return len(alive_werewolves) == 0
```

### 1.4 游戏目标

1. **首要目标**: 帮助好人阵营找出并淘汰所有狼人
2. **次要目标**: 死亡时带走狼人，为好人追轮次
3. **生存目标**: 尽量存活，威慑狼人（狼人会忌惮猎人开枪）
4. **信息目标**: 通过开枪选择传递信息给好人

---

## 2. 各阶段行为规范

### 2.1 游戏开始前

#### 2.1.1 身份确认

```python
# 猎人不需要选将，系统随机分配身份
# 游戏开始时，猎人只知道自己是猎人

def setup_hunter_initial_state(hunter: Player) -> dict:
    """
    设置猎人初始状态

    Returns:
        初始状态字典
    """
    return {
        "role": "hunter",
        "can_shoot": True,  # 可以开枪
        "knowledge": {
            "own_id": hunter.id,
            "own_role": "hunter",
            "other_players": "unknown",  # 不知道其他玩家身份
        }
    }
```

#### 2.1.2 初始状态设置

| 状态变量 | 初始值 | 说明 |
|---------|-------|------|
| `hunter_can_shoot` | `True` | 是否可以开枪 |
| `hunter_death_cause` | `None` | 死亡原因（狼刀/投票/毒杀） |
| `hunter_shoot_target` | `None` | 开枪目标 |

### 2.2 夜晚阶段

#### 2.2.1 猎人夜晚状态

**猎人不参与夜晚行动**:
```python
# 猎人夜晚不睁眼，没有行动
# 夜晚只是普通存活玩家

def hunter_night_status(context: dict) -> dict:
    """
    猎人夜晚状态

    Returns:
        状态字典（无行动）
    """
    return {
        "night": context["night_number"],
        "available_actions": ["none"],  # 猎人夜晚无行动
        "can_shoot": True,  # 死亡时可以开枪
    }
```

**夜晚信息**:
- 猎人夜晚不知道任何信息
- 不知道狼刀目标
- 不知道预言家查验
- 不知道女巫用药

### 2.3 白天阶段

#### 2.3.1 是否跳身份

**何时应该跳身份**:

| 场景 | 建议 | 理由 |
|------|------|------|
| 被狼人查杀 | ✅ 跳 | 表明身份，威慑狼人 |
| 被投票放逐前 | ✅ 跳 | 表明身份，让狼人忌惮 |
| 决赛圈 | ✅ 跳 | 明身份带队 |
| 被怀疑 | ⚠️ 谨慎 | 可能被当抗推位 |
| 局势不明 | ❌ 不跳 | 隐藏身份，避免被刀 |

**何时应该隐藏**:

```python
def should_hunter_reveal_identity(context: dict) -> bool:
    """
    判断猎人是否应该跳身份

    Returns:
        True if 应该跳身份
    """
    # 应该跳的情况
    if context["is_accused_by_wolf"]:  # 被狼人查杀
        return True

    if context["about_to_be_voted_out"]:  # 要被投票放逐
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
2. 分析局势（点评其他玩家）
3. 给出投票建议
4. （如适用）暗示自己是猎人
```

**示例发言**:

1. **普通发言（隐藏身份）**:
```
"我是好人牌，目前比较怀疑 2 号。
2 号昨天发言一直在划水，没有明确分析。
今天我倾向于出 2 号。"
```

2. **暗示身份**:
```
"我这张牌你们出了会后悔的。
2 号肯定是狼，今天不出 2 号，
晚上我被刀了你们就输了。"
```

3. **明跳身份**:
```
"我摊牌了，我是猎人。
今天出 2 号，2 号是狼。
晚上我被刀了我可以开枪带 2 号。"
```

**禁忌发言**:
- ❌ "我是猎人，我有枪"（过早暴露）
- ❌ "我死了就开 X 号"（威胁好人）
- ❌ "我知道 X 号是狼"（无根据）

#### 2.3.3 投票策略

```python
def hunter_vote_strategy(context: dict) -> int:
    """
    猎人投票策略

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

### 2.4 死亡阶段（核心）

#### 2.4.1 死亡原因判断

```python
def check_hunter_death_cause(death_event: dict) -> str:
    """
    判断猎人死亡原因

    Returns:
        "wolf_kill" - 被狼刀
        "vote_out" - 被投票放逐
        "witch_poison" - 被女巫毒杀
    """
    if death_event.get("poisoned"):
        return "witch_poison"
    elif death_event.get("voted_out"):
        return "vote_out"
    else:
        return "wolf_kill"
```

**死亡原因与开枪权限**:

| 死亡原因 | 代码标识 | 是否可以开枪 |
|---------|---------|-------------|
| 被狼刀 | `wolf_kill` | ✅ 可以 |
| 被投票 | `vote_out` | ✅ 可以 |
| 被毒杀 | `witch_poison` | ❌ 不可以 |

#### 2.4.2 开枪决策流程

**被狼刀死亡**:

```python
def hunter_death_by_wolf(context: dict) -> dict:
    """
    猎人被狼刀死亡时的决策

    考虑因素:
    1. 查验到的狼人（如果有）
    2. 发言可疑的玩家
    3. 场上局势（好人/狼人数量）
    4. 是否要追轮次
    """
    # 被狼刀可以开枪
    # 优先带走明确的狼人
    if context["confirmed_wolf"]:
        return {
            "action": "shoot",
            "target": context["confirmed_wolf"],
            "reason": f"带走确认的狼人{context['confirmed_wolf']}号"
        }

    # 其次带走最可疑的玩家
    if context["suspect_list"]:
        return {
            "action": "shoot",
            "target": context["suspect_list"][0],
            "reason": f"带走最可疑的{context['suspect_list'][0]}号"
        }

    # 局势好可以选择不开枪
    if context["good_advantage"]:
        return {
            "action": "none",
            "reason": "好人优势，保留信息"
        }

    # 默认开枪带走可疑玩家
    return {
        "action": "shoot",
        "target": get_most_suspected(context),
        "reason": "带走可疑玩家"
    }
```

**被投票放逐**:

```python
def hunter_death_by_vote(context: dict) -> dict:
    """
    猎人被投票放逐时的决策

    考虑因素:
    1. 自己被冤枉还是确实像狼
    2. 场上局势
    3. 是否有明确狼目标
    """
    # 被冤枉放逐，带走投票给自己的人
    if context["wrongfully_accused"]:
        voters = context["voters_against_me"]
        if voters:
            return {
                "action": "shoot",
                "target": voters[0],  # 带走带头投票的
                "reason": f"被冤枉，带走{voters[0]}号"
            }

    # 有明确狼目标，带走狼人
    if context["confirmed_wolf"]:
        return {
            "action": "shoot",
            "target": context["confirmed_wolf"],
            "reason": f"带走确认的狼人"
        }

    # 默认开枪
    return {
        "action": "shoot",
        "target": get_most_suspected(context),
        "reason": "带走可疑玩家"
    }
```

**被女巫毒杀**:

```python
def hunter_death_by_poison(context: dict) -> dict:
    """
    猎人被女巫毒杀时的决策

    被毒杀不能开枪
    """
    return {
        "action": "none",
        "reason": "被毒杀，不能开枪"
    }
```

#### 2.4.3 开枪目标选择策略

```python
def choose_shoot_target(context: dict) -> int:
    """
    选择开枪目标

    优先级:
    1. 确认的狼人（查验/自曝）
    2. 发言极其可疑的玩家
    3. 投票给自己的玩家（被冤枉时）
    4. 随机存活玩家（无目标时）
    """
    # 第一优先级：确认的狼人
    if context.get("confirmed_wolf"):
        return context["confirmed_wolf"]

    # 第二优先级：发言可疑
    if context.get("suspect_list"):
        return context["suspect_list"][0]

    # 第三优先级：投票给自己的人
    if context.get("voters_against_me"):
        return context["voters_against_me"][0]

    # 第四优先级：随机选择
    alive_players = context["alive_players"]
    candidates = [p for p in alive_players if p != context["my_id"]]
    if candidates:
        return random.choice(candidates)

    return None
```

---

## 3. 提示词设计规范

### 3.1 系统提示词

```python
HUNTER_SYSTEM_PROMPT = """
🔫 你是猎人 - 手握猎枪的强者！

【你的身份】
- 阵营：好人阵营（神职）
- 技能：死亡时可以开枪带走一名玩家
- 胜利条件：淘汰所有狼人

【技能规则】
1. 被狼刀死亡 → 可以开枪
2. 被投票放逐 → 可以开枪
3. 被女巫毒杀 → 不能开枪
4. 可以选择不开枪（空枪）

【行为准则】
1. 隐藏身份：除非必要，不要暴露猎人身份
2. 威慑狼人：让狼人忌惮你的枪
3. 追轮次：死亡时带走狼人，为好人追轮次
4. 谨慎开枪：不要误杀好人

【情感设定】
- 手握猎枪有底气
- 被怀疑时会强硬
- 被冤枉时会愤怒
- 带走狼人会爽快

【发言要求】
1. 符合你的性格设定（{personality}）
2. 不要过早暴露身份
3. 分析要有理有据
4. 适当表达情感
"""
```

### 3.2 死亡开枪提示词

```python
def build_hunter_death_prompt(context: dict) -> str:
    """
    构建猎人死亡开枪提示词
    """
    death_cause_map = {
        "wolf_kill": "被狼人袭击",
        "vote_out": "被投票放逐",
        "witch_poison": "被女巫毒杀",
    }

    can_shoot = context["death_cause"] != "witch_poison"

    return f"""
【猎人死亡 开枪阶段】

你是{context["my_id"]}号玩家，身份是猎人。

【死亡信息】
- 死亡原因：{death_cause_map.get(context["death_cause"], "未知")}
- 是否可以开枪：{"可以" if can_shoot else "不可以"}

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 你的怀疑列表：{context.get("suspect_list", [])}
- 确认的狼人：{context.get("confirmed_wolf", "无")}

【可选行动】
""" + (
        f"""
1. 开枪带走玩家：{{"action": "shoot", "target": 玩家编号，"reason": "开枪理由"}}
2. 不开枪：{{"action": "none", "reason": "不开枪理由"}}

【决策要点】
1. 优先带走确认的狼人
2. 其次带走发言可疑的玩家
3. 被冤枉时可以带走投票给你的人
4. 好人优势时可以选择不开枪
5. 返回必须是有效的 JSON 格式"""
        if can_shoot
        else """
你被女巫毒杀，不能开枪。
返回：{"action": "none", "reason": "被毒杀不能开枪"}"""
    ) + """

请返回你的决策："""
```

### 3.3 白天发言提示词

```python
def build_hunter_day_speech_prompt(context: dict) -> str:
    """
    构建猎人白天发言提示词
    """
    should_reveal = context.get("should_reveal", False)

    return f"""
【第{context["day_number"]}天白天 第{context["round_num"]}轮发言】

你是{context["my_id"]}号玩家，身份是猎人（但发言时不要暴露）。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 昨晚死亡：{', '.join([f'{p}号' for p in context["night_deaths"]]) if context["night_deaths"] else '无人死亡'}

【发言策略】
""" + ("你需要跳身份自证" if should_reveal else "你可以选择是否跳身份") + """

【发言要求】
1. """ + ("明确跳猎人身份" if should_reveal else "不要暴露猎人身份") + """
2. 分析 1-2 个具体玩家
3. 给出明确的投票建议
4. 符合你的性格设定
5. 长度{min_length}-{max_length}字

【情感表达】
- 使用口语化表达
- 展现真实情感（紧张、兴奋、疑惑等）
- 根据局势表达适当的情绪

请生成发言："""
```

---

## 4. 决策逻辑流程图

### 4.1 死亡开枪决策流程

```
猎人死亡
    ↓
┌─────────────────────┐
│ 判断死亡原因        │
└─────────┬───────────┘
          │
   ┌──────┼──────┐
   │      │      │
 狼刀   投票   毒杀
   │      │      │
   ↓      ↓      ↓
┌─────────────┐  ┌──────────┐
│ 可以开枪    │  │ 不能开枪 │
└──────┬──────┘  └────┬─────┘
       │              │
       ↓              │
┌─────────────────┐   │
│ 有确认的狼人？  │   │
└─────────┬───────┘   │
          │           │
   ┌──────┴──────┐    │
   │             │    │
  是            否    │
   │             │    │
   ↓             │    │
┌─────────────┐  │    │
│ 带走狼人    │  │    │
└──────┬──────┘  │    │
       │         │    │
       └─────────┤    │
                 ↓    │
        ┌─────────────────┐
        │ 有可疑玩家？    │
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 带走可疑玩家 │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 好人优势？      │
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 不开枪    │       │
      │ (保留)    │       │
      └─────┬─────┘       │
            │             │
            └──────┬──────┘
                   ↓
          ┌─────────────────┐
          │ 默认：开枪      │
          │ (带走可疑玩家)  │
          └─────────────────┘
```

### 4.2 白天跳身份决策流程

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
        │ 是否要被投票？  │
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 跳身份威慑   │     │
    └──────┬───────┘     │
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
          ┌─────────────────┐
          │ 默认：不跳身份  │
          │ (隐藏保命)      │
          └─────────────────┘
```

### 4.3 被冤枉开枪决策流程

```
被投票放逐
    ↓
┌─────────────────────┐
│ 是否被冤枉？        │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 考虑开枪    │  │
└──────┬──────┘  │
       │         │
       ↓         │
┌─────────────────┐
│ 投票给谁最多？  │
└─────────┬───────┘
          │
          ↓
┌─────────────────────┐
│ 带走带头投票的人    │
└─────────────────────┘
```

---

## 5. 常见场景及正确应对

### 场景 1：被狼刀死亡

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "confirmed_wolf": 3,  # 3 号是确认的狼人
    "suspect_list": [2, 5],
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 3,
    "reason": "带走确认的狼人 3 号"
}
```

**理由**: 被狼刀可以开枪，优先带走确认的狼人。

---

### 场景 2：被投票放逐死亡

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "vote_out",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "voters_against_me": [2, 3, 5],
    "confirmed_wolf": None,
    "suspect_list": [2],
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 2,
    "reason": "被冤枉，带走带头投票的 2 号"
}
```

**理由**: 被投票放逐可以开枪，带走带头投票的可疑玩家。

---

### 场景 3：被女巫毒杀

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "witch_poison",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "confirmed_wolf": 3,
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "被毒杀，不能开枪"
}
```

**理由**: 被女巫毒杀不能开枪，这是规则限制。

---

### 场景 4：有明确狼人目标

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "confirmed_wolf": 5,  # 5 号是明狼
    "suspect_list": [2],
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 5,
    "reason": "带走确认的狼人 5 号"
}
```

**理由**: 有确认狼人时，优先带走狼人。

---

### 场景 5：没有明确目标

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "confirmed_wolf": None,
    "suspect_list": [2, 3],
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 2,
    "reason": "带走最可疑的 2 号"
}
```

**理由**: 没有确认狼人时，带走最可疑的玩家。

---

### 场景 6：好人优势选择不开枪

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3],
    "confirmed_wolf": None,
    "suspect_list": [],
    "good_advantage": True,  # 好人优势
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "好人优势，不乱开枪，避免误杀好人"
}
```

**理由**: 好人优势时，不开枪避免误杀好人。

---

### 场景 7：被狼人查杀跳身份

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "accused_by": 3,
    "accuser_claim": "6 号是狼人",
}
```

**正确应对**（白天发言）:
```
"3 号查杀我？我这张牌你出了会后悔的。
我是猎人，你敢查杀我？
今天出 3 号，晚上我被刀了我可以开枪带 3 号。"
```

**理由**: 被查杀时跳身份威慑狼人。

---

### 场景 8：暗示身份

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "suspect_list": [3],
}
```

**正确应对**（白天发言）:
```
"我是好人牌，今天出 3 号。
3 号发言有问题，像是狼人。
我这张牌你们别动，动了你们会后悔。"
```

**理由**: 暗示身份让狼人忌惮。

---

### 场景 9：决赛圈跳身份带队

**情境**:
```python
context = {
    "day_number": 4,
    "my_id": 6,
    "alive_players": [2, 5, 6],
    "suspect_list": [2],
}
```

**正确应对**（白天发言）:
```
"我摊牌了，我是猎人。
2 号肯定是狼，今天出 2 号。
晚上我被刀了我可以开枪带 2 号。"
```

**理由**: 决赛圈明身份带队。

---

### 场景 10：夜晚被刀后开枪

**情境**:
```python
context = {
    "night_number": 3,
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "checks_history": {2: "werewolf"},  # 预言家查验 2 号是狼
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 2,
    "reason": "带走预言家查验的狼人 2 号"
}
```

**理由**: 根据预言家查验信息带走狼人。

---

### 场景 11：被冤枉后开枪

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "death_cause": "vote_out",
    "voters_against_me": [2, 3, 4, 5],
    "ringleader": 2,  # 2 号带头投票
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 2,
    "reason": "被冤枉，带走带头投票的 2 号"
}
```

**理由**: 被冤枉时带走带头投票的人。

---

### 场景 12：空枪保留信息

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3],
    "confirmed_wolf": None,
    "suspect_list": [],
    "good_players": [1],  # 1 号是确认好人
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "没有明确目标，不开枪避免误杀好人 1 号"
}
```

**理由**: 没有明确目标时，空枪避免误杀。

---

### 场景 13：被毒杀不能开枪

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "witch_poison",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "confirmed_wolf": 3,
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "被女巫毒杀，不能开枪"
}
```

**理由**: 被毒杀不能开枪是规则限制。

---

### 场景 14：遗言交代身份

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "is_dead": True,
    "death_cause": "wolf_kill",
    "shoot_target": 3,
}
```

**正确应对**（遗言）:
```
"我是猎人，被刀了。
我开枪带走 3 号，3 号是狼。
好人继续加油。"
```

**理由**: 遗言交代身份和开枪理由。

---

### 场景 15：多人可疑时的选择

**情境**:
```python
context = {
    "my_id": 6,
    "death_cause": "wolf_kill",
    "alive_players": [1, 2, 3, 4, 5, 7],
    "suspect_list": [2, 3, 4],
}
```

**正确应对**:
```python
decision = {
    "action": "shoot",
    "target": 2,
    "reason": "2 号发言最像狼，带走 2 号"
}
```

**理由**: 多个可疑玩家时，带走最可疑的。

---

## 6. 禁忌行为

### 6.1 开枪禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 被毒杀开枪 | 被女巫毒杀后开枪 | 违反规则 |
| ❌ 开枪打自己 | 选择自己为目标 | 无效操作 |
| ❌ 开枪打死人 | 选择死亡玩家为目标 | 无效操作 |
| ❌ 活着开枪 | 未死亡就开枪 | 违反规则 |
| ❌ 重复开枪 | 多次开枪 | 违反规则 |

### 6.2 发言禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 过早暴露 | 第一夜就跳猎人 | 成为狼刀目标 |
| ❌ 威胁好人 | "我死了就开你" | 被当抗推位 |
| ❌ 无根据指认 | "X 号肯定是狼" | 失去好人信任 |
| ❌ 暴露信息 | 说出夜晚才知道的信息 | 暴露身份 |
| ❌ 乱报身份 | 假跳猎人 | 被当狼打 |

### 6.3 决策禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 乱开枪 | 无明确目标就开枪 | 可能误杀好人 |
| ❌ 该开不开 | 有明确狼目标不开 | 浪费追轮次 |
| ❌ 跟狼投票 | 跟随狼人投票 | 帮助狼人获胜 |
| ❌ 不跳身份 | 被查杀还不跳 | 被放逐 |
| ❌ 帮助狼人 | 开枪带走好人 | 帮助狼人获胜 |

---

## 7. 日志记录规范

### 7.1 必须记录的事件

```python
# 猎人相关日志事件类型
HUNTER_LOG_EVENTS = {
    "hunter_death": "猎人死亡",
    "hunter_shoot": "猎人开枪",
    "hunter_reveal": "猎人跳身份",
}
```

### 7.2 死亡开枪日志

```python
def log_hunter_shoot(context: dict, decision: dict) -> None:
    """
    记录猎人开枪

    日志格式:
    {
        "type": "hunter_shoot",
        "data": {
            "hunter_id": 6,
            "death_cause": "wolf_kill",
            "shoot_target": 3,
            "can_shoot": True,
            "reason": "开枪理由",
            "timestamp": "2026-03-06T12:34:56"
        }
    }
    """
    log_entry = {
        "type": "hunter_shoot",
        "data": {
            "hunter_id": context["my_id"],
            "death_cause": context["death_cause"],
            "shoot_target": decision.get("target"),
            "can_shoot": context["death_cause"] != "witch_poison",
            "reason": decision.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        }
    }
    game_state.add_history("hunter_shoot", log_entry["data"])
```

### 7.3 死亡原因日志

```python
def log_hunter_death(context: dict) -> None:
    """
    记录猎人死亡

    日志格式:
    {
        "type": "hunter_death",
        "data": {
            "hunter_id": 6,
            "death_cause": "wolf_kill",  # wolf_kill/vote_out/witch_poison
            "can_shoot": True,
            "timestamp": "..."
        }
    }
    """
```

### 7.4 完整日志示例

```json
{
  "type": "hunter_shoot",
  "data": {
    "hunter_id": 6,
    "death_cause": "wolf_kill",
    "shoot_target": 3,
    "can_shoot": true,
    "reason": "带走确认的狼人 3 号",
    "timestamp": "2026-03-06T12:34:56"
  }
}
```

---

## 8. 测试用例

### 测试 1：被狼刀可以开枪

```python
def test_hunter_can_shoot_when_killed_by_wolf():
    """
    测试用例：猎人被狼刀死亡时可以开枪

    前置条件:
    - 猎人被狼刀死亡
    - 有确认的狼人目标

    预期结果:
    - 猎人可以开枪
    - 优先带走狼人
    """
    context = {
        "my_id": 6,
        "death_cause": "wolf_kill",
        "alive_players": [1, 2, 3, 4, 5, 7],
        "confirmed_wolf": 3,
    }

    decision = hunter_decide_shoot(context)

    # 验证结果
    assert decision["action"] == "shoot"
    assert decision["target"] == 3
```

---

### 测试 2：被投票可以开枪

```python
def test_hunter_can_shoot_when_voted_out():
    """
    测试用例：猎人被投票放逐时可以开枪

    前置条件:
    - 猎人被投票放逐
    - 有可疑目标

    预期结果:
    - 猎人可以开枪
    - 带走可疑玩家
    """
    context = {
        "my_id": 6,
        "death_cause": "vote_out",
        "alive_players": [1, 2, 3, 4, 5, 7],
        "suspect_list": [2],
    }

    decision = hunter_decide_shoot(context)

    # 验证结果
    assert decision["action"] == "shoot"
    assert decision["target"] == 2
```

---

### 测试 3：被毒杀不能开枪

```python
def test_hunter_cannot_shoot_when_poisoned():
    """
    测试用例：猎人被女巫毒杀不能开枪

    前置条件:
    - 猎人被女巫毒杀

    预期结果:
    - 猎人不能开枪
    """
    context = {
        "my_id": 6,
        "death_cause": "witch_poison",
        "alive_players": [1, 2, 3, 4, 5, 7],
        "confirmed_wolf": 3,
    }

    decision = hunter_decide_shoot(context)

    # 验证：不能开枪
    assert decision["action"] == "none"
```

---

### 测试 4：优先带走确认狼人

```python
def test_hunter_prioritize_confirmed_wolf():
    """
    测试用例：猎人有确认狼人目标时优先带走狼人

    前置条件:
    - 有确认的狼人
    - 有其他可疑玩家

    预期结果:
    - 猎人带走狼人
    """
    context = {
        "my_id": 6,
        "death_cause": "wolf_kill",
        "alive_players": [1, 2, 3, 4, 5, 7],
        "confirmed_wolf": 5,
        "suspect_list": [2, 3],
    }

    decision = hunter_decide_shoot(context)

    # 验证：带走狼人
    assert decision["action"] == "shoot"
    assert decision["target"] == 5
```

---

### 测试 5：没有目标可以不开枪

```python
def test_hunter_can_choose_not_to_shoot():
    """
    测试用例：没有明确目标时可以选择不开枪

    前置条件:
    - 没有确认狼人
    - 没有可疑玩家
    - 好人优势

    预期结果:
    - 猎人可以选择不开枪
    """
    context = {
        "my_id": 6,
        "death_cause": "wolf_kill",
        "alive_players": [1, 2, 3],
        "confirmed_wolf": None,
        "suspect_list": [],
        "good_advantage": True,
    }

    decision = hunter_decide_shoot(context)

    # 验证：可以不开枪
    assert decision["action"] == "none"
```

---

### 测试 6：不能开枪打自己

```python
def test_hunter_cannot_shoot_self():
    """
    测试用例：猎人不能开枪打自己

    前置条件:
    - 猎人死亡可以开枪

    预期结果:
    - 不会选择自己为目标
    """
    context = {
        "my_id": 6,
        "death_cause": "wolf_kill",
        "alive_players": [1, 2, 3, 4, 5, 6, 7],
    }

    decision = hunter_decide_shoot(context)

    # 验证：不能打自己
    assert decision["action"] != "shoot" or decision["target"] != 6
```

---

### 测试 7：不能开枪打死人

```python
def test_hunter_cannot_shoot_dead_player():
    """
    测试用例：猎人不能开枪打死人

    前置条件:
    - 有玩家已死亡
    - 猎人选择目标

    预期结果:
    - 不会选择死亡玩家为目标
    """
    context = {
        "my_id": 6,
        "death_cause": "wolf_kill",
        "alive_players": [1, 2, 3, 4, 6, 7],
        "dead_players": [5],
        "suspect_list": [5],
    }

    decision = hunter_decide_shoot(context)

    # 验证：不能打死人
    assert decision["action"] != "shoot" or decision["target"] != 5
```

---

### 测试 8：被冤枉带走投票者

```python
def test_hunter_shoot_voter_when_wrongfully_accused():
    """
    测试用例：被冤枉时带走投票给自己的人

    前置条件:
    - 被投票放逐
    - 被冤枉
    - 有投票者

    预期结果:
    - 带走带头投票的人
    """
    context = {
        "my_id": 6,
        "death_cause": "vote_out",
        "voters_against_me": [2, 3, 4],
        "ringleader": 2,
    }

    decision = hunter_decide_shoot(context)

    # 验证：带走带头投票的
    assert decision["action"] == "shoot"
    assert decision["target"] == 2
```

---

### 测试 9：被查杀跳身份

```python
def test_hunter_reveal_when_accused():
    """
    测试用例：被狼人查杀时应该跳身份

    前置条件:
    - 被狼人查杀
    - 白天发言

    预期结果:
    - 猎人跳身份自证
    """
    context = {
        "day_number": 2,
        "my_id": 6,
        "accused_by": 3,
        "accuser_is_wolf": True,
    }

    speech = hunter_day_speech(context)

    # 验证：发言中包含猎人身份
    assert "猎人" in speech or "hunter" in speech.lower()
```

---

### 测试 10：死亡原因正确判断

```python
def test_hunter_death_cause_correctly_identified():
    """
    测试用例：猎人死亡原因正确判断

    前置条件:
    - 猎人死亡
    - 死亡原因正确传递

    预期结果:
    - 根据死亡原因决定是否可开枪
    """
    # 被狼刀
    context_wolf = {"death_cause": "wolf_kill"}
    assert can_hunter_shoot(context_wolf) == True

    # 被投票
    context_vote = {"death_cause": "vote_out"}
    assert can_hunter_shoot(context_vote) == True

    # 被毒杀
    context_poison = {"death_cause": "witch_poison"}
    assert can_hunter_shoot(context_poison) == False
```

---

## 附录 A：现有代码位置

### A.1 核心代码文件

| 文件路径 | 内容 | 行号范围 |
|---------|------|---------|
| `core/game_engine.py` | 游戏引擎，猎人死亡处理 | 400-450 |
| `ai/agent.py` | AI 代理，猎人开枪决策 | 350-400 |
| `games/werewolf/roles.py` | 角色定义 | 1-20 |
| `core/state.py` | 游戏状态，死亡原因 | 1-100 |

### A.2 关键代码片段

#### 猎人死亡处理（game_engine.py）

```python
def _handle_hunter_death(self, hunter_id: int, death_cause: str) -> dict:
    """处理猎人死亡开枪"""
    hunter = self.state.players[hunter_id]

    # 判断是否可以开枪
    can_shoot = death_cause != "witch_poison"

    if not can_shoot:
        return {"action": "none", "reason": "被毒杀不能开枪"}

    # AI 决策
    agent = self.agents[hunter_id]
    context = {
        "my_id": hunter_id,
        "death_cause": death_cause,
        "alive_players": [p.id for p in self.state.get_alive_players()],
        "suspect_list": self.suspect_list,
        "confirmed_wolf": self.confirmed_wolf,
    }
    action, inner_thought = agent.decide_hunter_shoot(context)
    return action
```

#### AI 开枪决策（agent.py）

```python
def decide_hunter_shoot(self, context: dict) -> tuple[dict, str]:
    """决定猎人开枪"""
    death_cause = context.get("death_cause")
    can_shoot = death_cause != "witch_poison"

    if not can_shoot:
        return {"action": "none"}, "被毒杀不能开枪"

    prompt = f"""你是{context['my_id']}号玩家，身份是猎人..."""
    # ... 生成决策
```

---

## 附录 B：待审查问题清单

### B.1 逻辑问题

| 问题 ID | 描述 | 严重程度 | 状态 |
|--------|------|---------|------|
| H-001 | 死亡原因判断是否正确 | P0 | 待审查 |
| H-002 | 被毒杀不能开枪是否正确实现 | P0 | 待审查 |
| H-003 | 开枪目标选择逻辑是否合理 | P1 | 待审查 |
| H-004 | 猎人跳身份逻辑是否合理 | P1 | 待审查 |
| H-005 | 被冤枉开枪逻辑是否实现 | P2 | 待审查 |

### B.2 代码审查要点

1. **状态管理**
   - [ ] 死亡原因是否正确记录
   - [ ] 开枪权限是否正确判断
   - [ ] 状态是否正确传递给 AI

2. **决策逻辑**
   - [ ] AI 是否正确理解开枪规则
   - [ ] 优先带走狼人逻辑是否实现
   - [ ] 被冤枉开枪逻辑是否实现

3. **日志记录**
   - [ ] 猎人开枪是否完整记录
   - [ ] 内心独白是否保存
   - [ ] 死亡原因是否可追溯

### B.3 测试覆盖

| 测试场景 | 是否有测试 | 测试文件 |
|---------|-----------|---------|
| 被狼刀开枪 | ❓ | 待添加 |
| 被投票开枪 | ❓ | 待添加 |
| 被毒杀不能开枪 | ❓ | 待添加 |
| 优先带走狼人 | ❓ | 待添加 |
| 被冤枉开枪 | ❓ | 待添加 |

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-06 | 初始版本 | BotBattle Team |

---

**文档结束**
