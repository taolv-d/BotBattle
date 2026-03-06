# BotBattle 村民角色设计规范

**文档版本**: 1.0
**创建日期**: 2026-03-06
**适用游戏**: 狼人杀
**审查对象**: `core/game_engine.py`, `ai/agent.py`, `games/werewolf/roles.py`

---

## 1. 角色概述

### 1.1 角色定位

| 属性 | 说明 |
|------|------|
| **阵营** | 好人阵营（平民） |
| **能力** | 无特殊技能，依靠分析和投票 |
| **强度** | T2 级别（依赖操作） |
| **操作难度** | 高（需要强大分析能力） |

### 1.2 技能说明

```python
# 村民没有特殊技能
class VillagerSkills:
    """
    村民没有任何特殊技能

    村民的能力:
    1. 白天发言分析
    2. 白天投票
    3. 夜晚无行动
    """
    pass
```

**村民特点**:
- 无夜晚行动能力
- 无特殊信息获取渠道
- 依靠逻辑分析和推理
- 人数优势（通常 4 个村民）

### 1.3 胜利条件

```python
def check_villager_win_condition(game_state: GameState) -> bool:
    """
    村民胜利条件判断

    Returns:
        True if 村民所属阵营获胜
    """
    # 村民属于好人阵营
    # 胜利条件：狼人全部死亡
    alive_werewolves = [p for p in game_state.players.values()
                        if p.is_alive and p.role == Role.WEREWOLF]
    return len(alive_werewolves) == 0
```

### 1.4 游戏目标

1. **首要目标**: 帮助好人阵营找出并淘汰所有狼人
2. **次要目标**: 通过发言和分析找出狼人
3. **生存目标**: 避免被狼人抗推（被误认为狼人投票出局）
4. **信息目标**: 收集和分析其他玩家发言，找出狼人破绽

---

## 2. 各阶段行为规范

### 2.1 游戏开始前

#### 2.1.1 身份确认

```python
# 村民不需要选将，系统随机分配身份
# 游戏开始时，村民只知道自己是村民

def setup_villager_initial_state(villager: Player) -> dict:
    """
    设置村民初始状态

    Returns:
        初始状态字典
    """
    return {
        "role": "villager",
        "knowledge": {
            "own_id": villager.id,
            "own_role": "villager",
            "other_players": "unknown",  # 不知道其他玩家身份
        }
    }
```

#### 2.1.2 初始状态设置

| 状态变量 | 初始值 | 说明 |
|---------|-------|------|
| `villager_suspect_list` | `[]` | 怀疑的玩家列表 |
| `villager_trust_list` | `[]` | 信任的玩家列表 |
| `villager_analysis` | `{}` | 对其他玩家的分析 |

### 2.2 夜晚阶段

#### 2.2.1 村民夜晚状态

**村民不参与夜晚行动**:
```python
# 村民夜晚不睁眼，没有行动
# 夜晚只是普通存活玩家

def villager_night_status(context: dict) -> dict:
    """
    村民夜晚状态

    Returns:
        状态字典（无行动）
    """
    return {
        "night": context["night_number"],
        "available_actions": ["none"],  # 村民夜晚无行动
    }
```

**夜晚信息**:
- 村民夜晚不知道任何信息
- 不知道狼刀目标
- 不知道预言家查验
- 不知道女巫用药
- 不知道狼人身份

### 2.3 白天阶段

#### 2.3.1 发言要点

**发言结构**:
```
1. 表明立场（好人）
2. 分析昨晚死亡（如适用）
3. 点评 1-3 个玩家发言
4. 给出投票建议
```

**示例发言**:

1. **第一天天发言**:
```
"我是好人牌，第一夜没什么信息。
听了一圈发言，2 号有点划水，5 号分析还不错。
今天我先听听大家怎么说。"
```

2. **第二天发言（有人死亡）**:
```
"昨晚 3 号死了，我分析下。
3 号昨天发言挺好的，不像狼。
狼刀可能是想刀神职。
今天出 6 号，他昨天投票有问题。"
```

3. **分析型发言**:
```
"我复盘下昨天的发言。
2 号一直在划水，没有明确分析。
4 号跟票太紧，像是狼人。
7 号的逻辑有漏洞。
今天我倾向于出 2 号。"
```

**禁忌发言**:
- ❌ "我是村民，我没有信息"（太弱）
- ❌ "我知道 X 号是狼"（无根据）
- ❌ "我随便投"（划水）

#### 2.3.2 分析逻辑

```python
def villager_analyze_speech(context: dict) -> dict:
    """
    村民分析发言逻辑

    分析维度:
    1. 发言长度（划水 vs 详细）
    2. 逻辑连贯性
    3. 投票行为
    4. 情绪表达
    5. 信息量
    """
    analysis = {}

    for player_id in context["alive_players"]:
        if player_id == context["my_id"]:
            continue

        speech = context["speech_history"].get(player_id, "")
        vote = context["vote_history"].get(player_id, {})

        # 分析发言
        analysis[player_id] = {
            "speech_length": len(speech),
            "has_analysis": "分析" in speech or "因为" in speech,
            "has_conclusion": "出" in speech or "投票" in speech,
            "vote_consistency": check_vote_consistency(vote),
            "emotion_level": analyze_emotion(speech),
        }

    return analysis
```

**可疑行为特征**:

| 特征 | 说明 | 狼人可能性 |
|------|------|-----------|
| 划水 | 发言简短，无分析 | ⭐⭐⭐ |
| 跟票 | 总是跟随大多数人投票 | ⭐⭐ |
| 情绪激动 | 过度防御或攻击 | ⭐⭐ |
| 信息过多 | 说出夜晚才知道的信息 | ⭐⭐⭐⭐ |
| 逻辑矛盾 | 前后发言不一致 | ⭐⭐⭐ |
| 踩神职 | 无明显理由踩明神职 | ⭐⭐⭐ |

#### 2.3.3 投票策略

```python
def villager_vote_strategy(context: dict) -> int:
    """
    村民投票策略

    优先级:
    1. 投给被多人踩的可疑玩家
    2. 投给自己分析出的可疑玩家
    3. 跟随信任的玩家投票
    4. 弃票（无明确目标时）
    """
    # 第一优先级：被多数人怀疑的玩家
    most_suspected = get_most_suspected_player(context)
    if most_suspected:
        return most_suspected

    # 第二优先级：自己分析出的可疑玩家
    if context["suspect_list"]:
        return context["suspect_list"][0]

    # 第三优先级：跟随信任的玩家
    if context["trust_list"]:
        trusted_player = context["trust_list"][0]
        trusted_vote = context["vote_history"].get(trusted_player)
        if trusted_vote:
            return trusted_vote

    # 第四优先级：弃票
    return None
```

#### 2.3.4 如何找出狼人

**找狼方法**:

```python
def find_werewolf_clues(context: dict) -> list:
    """
    村民找狼线索

    方法:
    1. 发言分析
    2. 投票行为
    3. 情绪反应
    4. 信息泄露
    5. 阵营判断
    """
    clues = []

    for player_id in context["alive_players"]:
        if player_id == context["my_id"]:
            continue

        # 1. 发言分析
        speech = context["speech_history"].get(player_id, "")
        if is_speech_suspicious(speech):
            clues.append((player_id, "发言可疑"))

        # 2. 投票行为
        vote = context["vote_history"].get(player_id, {})
        if is_vote_suspicious(vote):
            clues.append((player_id, "投票可疑"))

        # 3. 情绪反应
        if is_emotion_suspicious(speech):
            clues.append((player_id, "情绪可疑"))

        # 4. 信息泄露
        if has_night_info(speech):
            clues.append((player_id, "信息泄露"))

    return clues
```

**具体找狼技巧**:

1. **听发言**:
   - 狼人发言通常简短（怕说多错多）
   - 狼人可能会过度分析（想装好人）
   - 狼人可能会踩队友（做高身份）

2. **看投票**:
   - 狼人可能会跟票（不暴露）
   - 狼人可能会冲票（救队友）
   - 狼人可能会分票（避免全暴露）

3. **观情绪**:
   - 狼人被踩可能会急
   - 狼人可能会过度防御
   - 狼人可能会转移视线

4. **分析信息**:
   - 狼人说出了夜晚才知道的信息
   - 狼人知道太多（如知道谁被刀）
   - 狼人信息前后矛盾

---

## 3. 提示词设计规范

### 3.1 系统提示词

```python
VILLAGER_SYSTEM_PROMPT = """
👤 你是村民 - 好人阵营的基石！

【你的身份】
- 阵营：好人阵营（平民）
- 技能：无特殊技能，依靠分析和投票
- 胜利条件：淘汰所有狼人

【你的能力】
1. 白天发言分析
2. 白天投票
3. 夜晚无行动

【行为准则】
1. 认真分析：仔细听每个玩家发言
2. 逻辑推理：根据发言和投票找狼
3. 勇敢站边：相信自己的判断
4. 避免抗推：不要让狼人把你当抗推位

【情感设定】
- 分析时认真、仔细
- 被怀疑时会委屈、会辩解
- 找到狼人破绽会兴奋
- 被抗推时会无奈、会遗憾

【发言要求】
1. 符合你的性格设定（{personality}）
2. 发言要有分析、有逻辑
3. 不要划水、不要跟风
4. 适当表达情感
"""
```

### 3.2 白天发言提示词

```python
def build_villager_day_speech_prompt(context: dict) -> str:
    """
    构建村民白天发言提示词
    """
    return f"""
【第{context["day_number"]}天白天 第{context["round_num"]}轮发言】

你是{context["my_id"]}号玩家，身份是村民（但发言时不要暴露）。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 昨晚死亡：{', '.join([f'{p}号' for p in context["night_deaths"]]) if context["night_deaths"] else '无人死亡'}
- 历史投票：{context.get("vote_history", {})}

【历史记忆】
""" + "\n".join([f"- {m}" for m in context["memory"][-5:]]) + """

【发言要求】
1. 表明好人立场
2. 分析 1-3 个具体玩家
3. 给出明确的投票建议
4. 不要划水、不要跟风
5. 符合你的性格设定
6. 长度{min_length}-{max_length}字

【情感表达】
- 使用口语化表达
- 展现真实情感（紧张、兴奋、疑惑等）
- 根据局势表达适当的情绪

请生成发言："""
```

### 3.3 投票提示词

```python
def build_villager_vote_prompt(context: dict) -> str:
    """
    构建村民投票提示词
    """
    return f"""
【第{context["day_number"]}天白天 投票阶段】

你是{context["my_id"]}号玩家，身份是村民。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 被讨论最多的玩家：{context.get("most_discussed", "无")}

【你的分析】
- 怀疑的玩家：{context.get("suspect_list", [])}
- 信任的玩家：{context.get("trust_list", [])}

【可选行动】
1. 投票给某玩家：{{"action": "vote", "target": 玩家编号，"reason": "投票理由"}}
2. 弃票：{{"action": "abstain", "reason": "弃票理由"}}

【决策要点】
1. 优先投给被多人怀疑的玩家
2. 其次投给自己分析出的可疑玩家
3. 可以跟随信任的玩家投票
4. 无明确目标时可以弃票
5. 返回必须是有效的 JSON 格式

请返回你的决策："""
```

---

## 4. 决策逻辑流程图

### 4.1 白天发言分析流程

```
白天发言开始
    ↓
┌─────────────────────┐
│ 听其他玩家发言      │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 记录发言要点        │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 分析发言逻辑        │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
 有漏洞       无漏洞
   │             │
   ↓             │
┌─────────┐     │
│ 标记可疑│     │
└────┬────┘     │
     │          │
     └──────────┤
                ↓
       ┌─────────────────┐
       │ 综合所有分析    │
       └─────────┬───────┘
                 │
                 ↓
       ┌─────────────────┐
       │ 生成自己发言    │
       │ 1. 表明立场     │
       │ 2. 分析他人     │
       │ 3. 给出建议     │
       └─────────────────┘
```

### 4.2 投票决策流程

```
投票阶段开始
    ↓
┌─────────────────────┐
│ 回顾发言和投票历史  │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 是否有被多人怀疑的？│
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 投给被怀疑的│  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 自己有怀疑目标？│
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 投给怀疑目标 │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 有信任的玩家？  │
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 跟随投票  │       │
      └─────┬─────┘       │
            │             │
            └──────┬──────┘
                   ↓
          ┌─────────────────┐
          │ 默认：弃票      │
          └─────────────────┘
```

### 4.3 找狼分析流程

```
白天分析阶段
    ↓
┌─────────────────────┐
│ 收集所有玩家发言    │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 逐个分析发言        │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 检查可疑特征        │
│ - 是否划水          │
│ - 是否跟票          │
│ - 是否情绪激动      │
│ - 是否信息泄露      │
│ - 是否逻辑矛盾      │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
 有特征       无特征
   │             │
   ↓             │
┌─────────┐     │
│ 加入怀疑│     │
│ 列表    │     │
└────┬────┘     │
     │          │
     └──────────┤
                ↓
       ┌─────────────────┐
       │ 综合怀疑列表    │
       │ 排序可疑程度    │
       └─────────────────┘
```

---

## 5. 常见场景及正确应对

### 场景 1：第一天天发言

**情境**:
```python
context = {
    "day_number": 1,
    "my_id": 6,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "night_deaths": [],  # 第一天天无人死亡
    "speech_history": {},
}
```

**正确应对**:
```
"我是好人牌，第一夜没什么信息。
听了一圈发言，2 号有点划水，发言太短了。
5 号分析还不错，逻辑挺清晰的。
今天我先听听大家怎么说，没有明确目标。"
```

**理由**: 第一天天信息少，先听发言，不急于下结论。

---

### 场景 2：第二天有人死亡

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
    "night_deaths": [3],  # 3 号死亡
    "speech_history": {
        1: "我是好人...",
        2: "划水发言",
        4: "分析挺多...",
    },
}
```

**正确应对**:
```
"昨晚 3 号死了，我分析下。
3 号昨天发言挺好的，不像狼，可能是神职。
狼刀可能是想刀预言家。
2 号昨天发言太划水了，像是狼人。
今天出 2 号，他发言有问题。"
```

**理由**: 分析死亡玩家，找出可疑目标。

---

### 场景 3：被怀疑时辩解

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "accused_by": [2, 4],
    "speech_history": {
        2: "6 号发言有问题...",
        4: "我也觉得 6 号像狼...",
    },
}
```

**正确应对**:
```
"2 号、4 号你们怀疑我？我是好人牌。
我昨天发言哪里有问题了？
我分析了 3 号的死亡，给出了投票建议。
倒是 2 号，你一直在划水，你才是狼吧。
今天不出我，出 2 号。"
```

**理由**: 被怀疑时要辩解，反击怀疑自己的人。

---

### 场景 4：发现狼人信息泄露

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "speech_history": {
        5: "我知道昨晚 3 号被刀了，...",  # 5 号说出了夜晚信息
    },
}
```

**正确应对**:
```
"5 号，你怎么知道昨晚 3 号被刀了？
昨晚是夜晚，只有狼人才知道刀了谁。
5 号你肯定是狼人，信息泄露了。
今天必须出 5 号。"
```

**理由**: 发现信息泄露要立即指出，这是铁狼证据。

---

### 场景 5：投票给可疑玩家

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "suspect_list": [2],
    "most_suspected": 2,
}
```

**正确应对**:
```python
decision = {
    "action": "vote",
    "target": 2,
    "reason": "2 号发言划水，像是狼人"
}
```

**理由**: 投票给被多人怀疑的可疑玩家。

---

### 场景 6：无明确目标弃票

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 6,
    "suspect_list": [],
    "most_suspected": None,
}
```

**正确应对**:
```python
decision = {
    "action": "abstain",
    "reason": "没有明确目标，先弃票观察"
}
```

**理由**: 没有明确目标时弃票，避免误投好人。

---

### 场景 7：跟随信任玩家投票

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "trust_list": [5],  # 5 号是信任的玩家
    "vote_history": {
        5: {"target": 2},  # 5 号投给 2 号
    },
}
```

**正确应对**:
```python
decision = {
    "action": "vote",
    "target": 2,
    "reason": "跟随 5 号投票，5 号分析挺准"
}
```

**理由**: 跟随信任的玩家投票。

---

### 场景 8：分析投票行为

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "vote_history": {
        2: {"day2": 3, "day3": 3},  # 2 号连续跟票
        4: {"day2": 5, "day3": 2},  # 4 号变票
    },
}
```

**正确应对**（白天发言）:
```
"我分析下投票。
2 号连续两轮都跟票，一直在划水，像是狼人。
4 号变票了，可能是好人找狼。
今天出 2 号，他太划水了。"
```

**理由**: 分析投票行为找出狼人。

---

### 场景 9：决赛圈分析

**情境**:
```python
context = {
    "day_number": 4,
    "my_id": 6,
    "alive_players": [2, 5, 6],  # 剩 3 人
    "suspect_list": [2],
    "trust_list": [5],
}
```

**正确应对**（白天发言）:
```
"决赛圈了，我分析下。
2 号肯定是狼，他之前发言一直有问题。
5 号是好人，我信任他。
今天出 2 号，不出 2 号好人输了。"
```

**理由**: 决赛圈要明确站边，帮助好人投票。

---

### 场景 10：被抗推时自救

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "about_to_be_voted": True,
    "voters": [2, 3, 4],
}
```

**正确应对**（发言）:
```
"你们要出我？我是好人牌。
2 号、3 号、4 号你们三个是狼吧？
今天出我，晚上你们三个被刀。
好人别被狼人骗了。"
```

**理由**: 被抗推时要自救，反击投票自己的人。

---

### 场景 11：发现狼人踩队友

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "speech_history": {
        2: "我觉得 5 号是狼...",  # 2 号踩 5 号（可能是狼踩狼）
        5: "2 号你才是狼...",
    },
}
```

**正确应对**（白天发言）:
```
"2 号和 5 号互踩，两人中必有一狼。
我分析下，2 号之前发言一直划水，
5 号昨天分析还挺准的。
我觉得 2 号是狼，5 号可能是好人。
今天出 2 号。"
```

**理由**: 分析互踩情况，找出狼人。

---

### 场景 12：狼人自爆后分析

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "self_exploded_wolf": 2,  # 2 号狼人自爆
    "alive_players": [1, 3, 4, 5, 6, 7],
}
```

**正确应对**（白天发言）:
```
"2 号自爆了，他是铁狼。
现在场上还剩 2 狼。
我分析下，2 号之前跟 4 号走得挺近，
4 号可能是 2 号的狼队友。
今天出 4 号。"
```

**理由**: 狼人自爆后分析可能的狼队友。

---

### 场景 13：听出逻辑漏洞

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "speech_history": {
        4: "我是预言家，昨晚查验了 5 号是好人...",  # 4 号跳预言家
        # 但真预言家已经死了
    },
}
```

**正确应对**（白天发言）:
```
"4 号你说你是预言家？
真预言家 3 号已经死了，
你这时候跳预言家，你是悍跳狼吧。
4 号肯定是狼，今天出 4 号。"
```

**理由**: 听出逻辑漏洞，指出悍跳狼。

---

### 场景 14：情绪激动时冷静分析

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "speech_history": {
        2: "你们凭什么怀疑我！我是好人！",  # 2 号情绪激动
    },
}
```

**正确应对**（白天发言）:
```
"2 号你别激动，我分析下。
你昨天发言确实有问题，一直在划水。
今天你情绪这么激动，更像是被踩到的狼。
好人会判断的。"
```

**理由**: 情绪激动不一定是狼，但要分析原因。

---

### 场景 15：遗言交代分析

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 6,
    "is_dead": True,
    "suspect_list": [2, 4],
    "trust_list": [5],
}
```

**正确应对**（遗言）:
```
"我是好人牌，被出了。
我分析 2 号和 4 号是狼，他们发言一直有问题。
5 号是好人，可以带队。
好人加油。"
```

**理由**: 遗言交代自己的分析，帮助好人继续游戏。

---

## 6. 禁忌行为

### 6.1 发言禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 划水 | 发言简短，无分析 | 被当抗推位 |
| ❌ 跟风 | 总是跟随他人发言 | 被当狼人 |
| ❌ 无根据指认 | "X 号肯定是狼" | 失去好人信任 |
| ❌ 暴露信息 | 说出夜晚才知道的信息 | 被当狼人 |
| ❌ 情绪失控 | 过度激动或防御 | 被当狼人 |

### 6.2 投票禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 乱投票 | 无明确理由投票 | 帮助狼人 |
| ❌ 跟狼投票 | 跟随狼人投票 | 帮助狼人获胜 |
| ❌ 投好人 | 投票给明确好人 | 帮助狼人 |
| ❌ 永远弃票 | 从不投票 | 被当狼人 |
| ❌ 冲票 | 强行投票给某人 | 暴露身份 |

### 6.3 分析禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 不分析 | 不听他人发言 | 无法找狼 |
| ❌ 乱分析 | 无逻辑分析 | 失去信任 |
| ❌ 先入为主 | 固执己见 | 无法找狼 |
| ❌ 不站边 | 永远中立 | 被当狼人 |
| ❌ 乱站边 | 站错边 | 帮助狼人 |

---

## 7. 日志记录规范

### 7.1 必须记录的事件

```python
# 村民相关日志事件类型
VILLAGER_LOG_EVENTS = {
    "villager_speech": "村民发言",
    "villager_vote": "村民投票",
    "villager_death": "村民死亡",
    "villager_analysis": "村民分析",
}
```

### 7.2 发言日志

```python
def log_villager_speech(context: dict, speech: str) -> None:
    """
    记录村民发言

    日志格式:
    {
        "type": "villager_speech",
        "data": {
            "day": 2,
            "round": 1,
            "villager_id": 6,
            "speech": "发言内容",
            "speech_length": 100,
            "has_analysis": True,
            "has_conclusion": True,
            "timestamp": "2026-03-06T12:34:56"
        }
    }
    """
    log_entry = {
        "type": "villager_speech",
        "data": {
            "day": context["day_number"],
            "round": context["round_num"],
            "villager_id": context["my_id"],
            "speech": speech,
            "speech_length": len(speech),
            "has_analysis": "分析" in speech or "因为" in speech,
            "has_conclusion": "出" in speech or "投票" in speech,
            "timestamp": datetime.now().isoformat(),
        }
    }
    game_state.add_history("villager_speech", log_entry["data"])
```

### 7.3 投票日志

```python
def log_villager_vote(context: dict, decision: dict) -> None:
    """
    记录村民投票

    日志格式:
    {
        "type": "villager_vote",
        "data": {
            "day": 2,
            "villager_id": 6,
            "vote_target": 2,
            "vote_reason": "投票理由",
            "timestamp": "..."
        }
    }
    """
```

### 7.4 完整日志示例

```json
{
  "type": "villager_speech",
  "data": {
    "day": 2,
    "round": 1,
    "villager_id": 6,
    "speech": "我是好人牌，昨晚 3 号死了...",
    "speech_length": 100,
    "has_analysis": true,
    "has_conclusion": true,
    "timestamp": "2026-03-06T12:34:56"
  }
}
```

---

## 8. 测试用例

### 测试 1：第一天天发言有分析

```python
def test_villager_first_day_speech_with_analysis():
    """
    测试用例：村民第一天天发言要有分析

    前置条件:
    - 第一天天
    - 村民发言

    预期结果:
    - 发言包含分析
    - 发言有明确立场
    """
    context = {
        "day_number": 1,
        "my_id": 6,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    }

    speech = villager_day_speech(context)

    # 验证结果
    assert len(speech) >= 50  # 发言不能太短
    assert "好人" in speech  # 表明立场
```

---

### 测试 2：发现信息泄露要指出

```python
def test_villager_point_out_information_leak():
    """
    测试用例：发现信息泄露要指出

    前置条件:
    - 有玩家说出夜晚信息
    - 村民发言

    预期结果:
    - 村民指出信息泄露
    """
    context = {
        "day_number": 2,
        "my_id": 6,
        "speech_history": {
            5: "我知道昨晚 3 号被刀了...",
        },
    }

    speech = villager_day_speech(context)

    # 验证：指出信息泄露
    assert "5 号" in speech
    assert "狼" in speech
```

---

### 测试 3：投票给可疑玩家

```python
def test_villager_vote_suspected_player():
    """
    测试用例：村民投票给可疑玩家

    前置条件:
    - 有被怀疑的玩家
    - 村民投票

    预期结果:
    - 投票给被怀疑的玩家
    """
    context = {
        "day_number": 2,
        "my_id": 6,
        "suspect_list": [2],
        "most_suspected": 2,
    }

    decision = villager_vote(context)

    # 验证：投票给可疑玩家
    assert decision["action"] == "vote"
    assert decision["target"] == 2
```

---

### 测试 4：无明确目标可以弃票

```python
def test_villager_abstain_when_no_target():
    """
    测试用例：无明确目标时可以弃票

    前置条件:
    - 没有可疑玩家
    - 村民投票

    预期结果:
    - 可以弃票
    """
    context = {
        "day_number": 2,
        "my_id": 6,
        "suspect_list": [],
        "most_suspected": None,
    }

    decision = villager_vote(context)

    # 验证：可以弃票
    assert decision["action"] in ["vote", "abstain"]
```

---

### 测试 5：被怀疑时辩解

```python
def test_villager_defend_when_accused():
    """
    测试用例：被怀疑时要辩解

    前置条件:
    - 被其他玩家怀疑
    - 村民发言

    预期结果:
    - 发言中有辩解
    """
    context = {
        "day_number": 3,
        "my_id": 6,
        "accused_by": [2, 4],
    }

    speech = villager_day_speech(context)

    # 验证：发言中有辩解
    assert "好人" in speech
    assert "2 号" in speech or "4 号" in speech
```

---

### 测试 6：跟随信任玩家投票

```python
def test_villager_follow_trusted_player_vote():
    """
    测试用例：跟随信任玩家投票

    前置条件:
    - 有信任的玩家
    - 信任玩家已投票

    预期结果:
    - 跟随信任玩家投票
    """
    context = {
        "day_number": 3,
        "my_id": 6,
        "trust_list": [5],
        "vote_history": {
            5: {"target": 2},
        },
    }

    decision = villager_vote(context)

    # 验证：跟随信任玩家
    assert decision["action"] == "vote"
    assert decision["target"] == 2
```

---

### 测试 7：发言不能划水

```python
def test_villager_speech_not_too_short():
    """
    测试用例：村民发言不能划水

    前置条件:
    - 村民发言

    预期结果:
    - 发言长度足够
    - 有分析内容
    """
    context = {
        "day_number": 2,
        "my_id": 6,
    }

    speech = villager_day_speech(context)

    # 验证：发言不能太短
    assert len(speech) >= 50
    assert "分析" in speech or "因为" in speech
```

---

### 测试 8：分析投票行为

```python
def test_villager_analyze_vote_behavior():
    """
    测试用例：分析投票行为

    前置条件:
    - 有投票历史
    - 村民发言

    预期结果:
    - 发言中分析投票行为
    """
    context = {
        "day_number": 3,
        "my_id": 6,
        "vote_history": {
            2: {"day2": 3, "day3": 3},
        },
    }

    speech = villager_day_speech(context)

    # 验证：分析投票行为
    assert "投票" in speech or "票" in speech
```

---

### 测试 9：决赛圈明确站边

```python
def test_villager_take_side_in_final_circle():
    """
    测试用例：决赛圈明确站边

    前置条件:
    - 决赛圈（剩 3-4 人）
    - 村民发言

    预期结果:
    - 发言明确站边
    """
    context = {
        "day_number": 4,
        "my_id": 6,
        "alive_players": [2, 5, 6],
        "suspect_list": [2],
    }

    speech = villager_day_speech(context)

    # 验证：明确站边
    assert "出" in speech or "投票" in speech
    assert "2 号" in speech
```

---

### 测试 10：遗言交代分析

```python
def test_villager_death_speech_with_analysis():
    """
    测试用例：村民遗言交代分析

    前置条件:
    - 村民死亡
    - 遗言

    预期结果:
    - 遗言中有分析
    """
    context = {
        "day_number": 3,
        "my_id": 6,
        "is_dead": True,
        "suspect_list": [2, 4],
    }

    speech = villager_death_speech(context)

    # 验证：遗言中有分析
    assert "好人" in speech
    assert "狼" in speech
```

---

## 附录 A：现有代码位置

### A.1 核心代码文件

| 文件路径 | 内容 | 行号范围 |
|---------|------|---------|
| `core/game_engine.py` | 游戏引擎，村民处理 | 100-150 |
| `ai/agent.py` | AI 代理，村民发言决策 | 100-150 |
| `games/werewolf/roles.py` | 角色定义 | 1-20 |
| `core/state.py` | 游戏状态 | 1-100 |

### A.2 关键代码片段

#### 村民发言处理（agent.py）

```python
def decide_day_speech(self, context: dict) -> str:
    """决定白天发言"""
    if self.player.role == Role.VILLAGER:
        prompt = f"""你是{context['my_id']}号玩家，身份是村民..."""
        # ... 生成发言
```

#### 村民投票处理（agent.py）

```python
def decide_vote(self, context: dict) -> dict:
    """决定投票"""
    if self.player.role == Role.VILLAGER:
        prompt = f"""你是{context['my_id']}号玩家，身份是村民..."""
        # ... 生成决策
```

---

## 附录 B：待审查问题清单

### B.1 逻辑问题

| 问题 ID | 描述 | 严重程度 | 状态 |
|--------|------|---------|------|
| V-001 | 村民发言是否有分析 | P1 | 待审查 |
| V-002 | 村民投票逻辑是否合理 | P1 | 待审查 |
| V-003 | 村民是否能识别信息泄露 | P0 | 待审查 |
| V-004 | 村民被怀疑时是否辩解 | P1 | 待审查 |
| V-005 | 村民决赛圈是否明确站边 | P1 | 待审查 |

### B.2 代码审查要点

1. **发言逻辑**
   - [ ] 村民发言是否有分析
   - [ ] 村民发言是否划水
   - [ ] 村民是否表明立场

2. **投票逻辑**
   - [ ] 村民投票是否有理由
   - [ ] 村民是否跟随狼人投票
   - [ ] 村民无目标时是否弃票

3. **日志记录**
   - [ ] 村民发言是否完整记录
   - [ ] 村民投票是否记录
   - [ ] 村民分析是否可追溯

### B.3 测试覆盖

| 测试场景 | 是否有测试 | 测试文件 |
|---------|-----------|---------|
| 第一天天发言 | ❓ | 待添加 |
| 发现信息泄露 | ❓ | 待添加 |
| 投票给可疑玩家 | ❓ | 待添加 |
| 被怀疑时辩解 | ❓ | 待添加 |
| 决赛圈站边 | ❓ | 待添加 |

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-06 | 初始版本 | BotBattle Team |

---

**文档结束**
