# BotBattle 预言家角色设计规范

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
| **能力** | 每晚可以查验一名玩家的身份（好人/狼人） |
| **强度** | T0 级别（最强信息位） |
| **操作难度** | 中等（需要报查验、防悍跳） |

### 1.2 技能说明

```python
# 预言家技能数据结构
class SeerSkills:
    def check_identity(self, target_id: int) -> str:
        """
        查验玩家身份

        Args:
            target_id: 被查验的玩家 ID

        Returns:
            "werewolf" - 狼人或 "good" - 好人（包括村民和神职）

        限制:
        1. 每晚只能查验一人
        2. 只能查验存活玩家
        3. 不能查验自己
        4. 查验结果是二元的（好人/狼人），不区分具体身份
        """
        pass
```

**技能规则**:
- 查验结果：仅返回"好人"或"狼人"，不区分具体身份
- 查验对象：必须是当晚存活的玩家（不能查验自己）
- 查验时效：查验结果仅在当晚有效，白天需要口头报出
- 查验历史：预言家自己记住所有查验过的玩家

### 1.3 胜利条件

```python
def check_seer_win_condition(game_state: GameState) -> bool:
    """
    预言家胜利条件判断

    Returns:
        True if 预言家所属阵营获胜
    """
    # 预言家属于好人阵营
    # 胜利条件：狼人全部死亡
    alive_werewolves = [p for p in game_state.players.values()
                        if p.is_alive and p.role == Role.WEREWOLF]
    return len(alive_werewolves) == 0
```

### 1.4 游戏目标

1. **首要目标**: 通过查验找出狼人，帮助好人阵营获胜
2. **次要目标**: 存活足够久，完成多轮查验
3. **信息目标**: 及时报出查验结果，建立好人信任
4. **生存目标**: 避免被狼人发现并袭击（狼人会优先刀预言家）

---

## 2. 各阶段行为规范

### 2.1 游戏开始前

#### 2.1.1 身份确认

```python
# 预言家不需要选将，系统随机分配身份
# 游戏开始时，预言家只知道自己是预言家，不知道其他玩家身份

def setup_seer_initial_state(seer: Player) -> dict:
    """
    设置预言家初始状态

    Returns:
        初始状态字典
    """
    return {
        "role": "seer",
        "checks_history": {},  # 查验历史 {player_id: result}
        "knowledge": {
            "own_id": seer.id,
            "own_role": "seer",
            "other_players": "unknown",  # 不知道其他玩家身份
        }
    }
```

#### 2.1.2 初始状态设置

| 状态变量 | 初始值 | 说明 |
|---------|-------|------|
| `seer_checks_history` | `{}` | 查验历史记录 |
| `seer_check_target` | `None` | 当前查验目标 |
| `seer_check_result` | `None` | 当前查验结果 |

### 2.2 夜晚阶段

#### 2.2.1 第一夜

**行动顺序**:
```
1. 狼人袭击 → 2. 预言家查验 → 3. 女巫行动
```

**预言家睁眼时机**:
```python
# 在 game_engine.py 中的行动顺序
def _run_night(self):
    # 1. 狼人行动
    wolf_action = self._handle_werewolf_action()

    # 2. 预言家行动（查验）
    seer_action = self._handle_seer_action()

    # 3. 女巫行动
    witch_action = self._handle_witch_action(
        wolf_action.get("target") if wolf_action else None
    )
```

**可以看到的信息**:
```python
seer_context = {
    "night_number": 1,           # 第 1 夜
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # 存活玩家列表
    "my_id": 3,                  # 预言家自己的号码
    "checks_history": {},        # 查验历史（第一夜为空）
}
```

**可以选择的行动**:

| 选项 | JSON 格式 | 说明 |
|------|----------|------|
| 查验玩家 | `{"action": "check", "target": 5, "reason": "..."}` | 查验指定玩家 |
| 不查验 | `{"action": "none", "reason": "..."}` | 跳过查验（不推荐） |

**决策依据**:

```python
def seer_first_night_decision(context: dict) -> str:
    """
    第一夜预言家决策逻辑

    查验优先级:
    1. 查验位置：优先查验身边位置（1 号查 2 号，9 号查 8 号）
    2. 随机查验：无明显目标时随机查验
    3. 避免查验：自己、明显好人（如果有）

    注意：第一夜没有发言信息，只能凭位置或随机
    """
    my_id = context["my_id"]
    alive_players = context["alive_players"]

    # 排除自己
    candidates = [p for p in alive_players if p != my_id]

    # 优先查验身边位置
    left = my_id - 1 if my_id > 1 else max(alive_players)
    right = my_id + 1 if my_id < max(alive_players) else 1

    if left in candidates:
        return left
    elif right in candidates:
        return right
    else:
        # 随机选择一个
        return random.choice(candidates)
```

**限制条件**:
- [ ] 不能查验自己
- [ ] 不能查验已死亡玩家
- [ ] 每晚只能查验一人
- [ ] 查验结果必须记录到历史

#### 2.2.2 后续夜晚

**状态检查**:
```python
def check_seer_status(night_num: int) -> dict:
    """
    检查预言家状态

    Returns:
        可用行动列表
    """
    available_actions = []

    # 预言家每晚都可以查验（只要存活）
    available_actions.append("check")

    return {
        "night": night_num,
        "available_actions": available_actions,
        "checks_history": seer_checks_history,
    }
```

**查验策略**:

| 夜晚 | 查验策略 | 说明 |
|------|---------|------|
| 第 1 夜 | 随机/位置 | 无信息，凭位置或随机 |
| 第 2 夜 | 查验可疑玩家 | 根据白天发言 |
| 第 3 夜+ | 查验关键玩家 | 决赛圈查验 |

**决策依据**:

```python
def seer_later_night_decision(context: dict) -> dict:
    """
    后续夜晚预言家决策逻辑

    考虑因素:
    1. 白天发言可疑的玩家
    2. 尚未查验的玩家
    3. 关键位置玩家（如跳神职的）
    4. 避免重复查验同一人
    """
    my_id = context["my_id"]
    alive_players = context["alive_players"]
    checks_history = context.get("checks_history", {})
    suspect_list = context.get("suspect_list", [])

    # 排除自己和已查验过的
    candidates = [p for p in alive_players 
                  if p != my_id and p not in checks_history]

    # 优先查验可疑玩家
    for suspect in suspect_list:
        if suspect in candidates:
            return {"action": "check", "target": suspect, 
                    "reason": f"{suspect}号白天发言可疑"}

    # 其次查验未查验过的玩家
    if candidates:
        target = random.choice(candidates)
        return {"action": "check", "target": target,
                "reason": f"查验未确认身份的玩家"}

    # 所有人都查验过了，只能空过
    return {"action": "none", "reason": "所有玩家都已查验"}
```

**限制条件**:
- [ ] 不能查验死亡玩家
- [ ] 不能查验自己
- [ ] 不能重复查验同一人（浪费机会）

### 2.3 白天阶段

#### 2.3.1 是否跳身份

**何时应该跳身份**:

| 场景 | 建议 | 理由 |
|------|------|------|
| 第一晚查验到狼人 | ✅ 跳 | 立即报查验，帮助好人 |
| 有狼人悍跳 | ✅ 跳 | 对刚悍跳狼，争夺警徽 |
| 被狼人查杀 | ✅ 跳 | 反查杀，表明身份 |
| 决赛圈 | ✅ 跳 | 明身份带队 |
| 查验到好人 | ⚠️ 谨慎 | 可以先藏，后续再跳 |

**何时应该隐藏**:

```python
def should_seer_reveal_identity(context: dict) -> bool:
    """
    判断预言家是否应该跳身份

    Returns:
        True if 应该跳身份
    """
    # 应该跳的情况
    if context["check_result"] == "werewolf":  # 查验到狼人
        return True

    if context["has_fake_seer"]:  # 有悍跳狼
        return True

    if context["is_accused_by_wolf"]:  # 被狼人查杀
        return True

    if context["final_circle"]:  # 决赛圈
        return True

    # 可以考虑隐藏的情况
    if context["check_result"] == "good" and context["day_number"] == 1:
        return False  # 第一天天查验到好人，可以先藏

    return False  # 默认隐藏
```

#### 2.3.2 报查验格式

**标准报查验格式**:
```
"我是预言家，昨晚查验了 X 号，X 号是 [好人/狼人]。"
```

**示例发言**:

1. **查验到好人（金水）**:
```
"我是预言家，昨晚查验了 5 号，5 号是好人。
今天先出 X 号，他发言有问题。"
```

2. **查验到狼人（查杀）**:
```
"我是预言家，昨晚查验了 3 号，3 号是狼人！
3 号今天必须出，好人跟我一起投票。"
```

3. **应对悍跳**:
```
"我是真预言家，昨晚查验了 5 号是好人。
2 号你悍跳我，你才是狼。
好人跟我一起出 2 号。"
```

#### 2.3.3 发言要点

**发言结构**:
```
1. 跳身份（如适用）
2. 报查验（昨晚查验结果）
3. 分析局势（点评其他玩家）
4. 给出投票建议
```

**禁忌发言**:
- ❌ "我昨晚查验了 X 号是好人，但我不是预言家"（矛盾）
- ❌ "我是预言家，昨晚查验了 X 号和 Y 号"（一晚只能验一人）
- ❌ "我是预言家，X 号是狼，Y 号也是狼"（除非查验过两人）

#### 2.3.4 投票策略

```python
def seer_vote_strategy(context: dict) -> int:
    """
    预言家投票策略

    优先级:
    1. 投给查验到的狼人
    2. 投给悍跳预言家的玩家
    3. 投给被多人怀疑的可疑玩家
    4. 跟随大多数好人投票
    """
    # 第一优先级：查验到的狼人
    for player_id, result in context["checks_history"].items():
        if result == "werewolf" and player_id in context["alive_players"]:
            return player_id

    # 第二优先级：悍跳狼
    if context.get("fake_seer_id"):
        return context["fake_seer_id"]

    # 第三优先级：可疑玩家
    if context.get("suspect_list"):
        return context["suspect_list"][0]

    # 第四优先级：弃票
    return None
```

---

## 3. 提示词设计规范

### 3.1 系统提示词

```python
SEER_SYSTEM_PROMPT = """
🔮 你是预言家 - 掌握真相的人！

【你的身份】
- 阵营：好人阵营（神职）
- 技能：每晚可以查验一名玩家的身份（好人/狼人）
- 胜利条件：淘汰所有狼人

【技能规则】
1. 每晚只能查验一人
2. 查验结果是二元的（好人/狼人）
3. 不能查验自己
4. 不能查验已死亡玩家
5. 查验结果要白天报出

【行为准则】
1. 及时报查验：查验到狼人立即跳身份报查验
2. 应对悍跳：有狼人悍跳时要对刚
3. 保护身份：查验到好人可以考虑隐藏
4. 存活优先：避免过早暴露被刀

【情感设定】
- 查验到狼人会紧张、会激动
- 被悍跳会着急、会委屈
- 带领好人有责任感
- 被怀疑时会辩解

【发言要求】
1. 符合你的性格设定（{personality}）
2. 报查验要清晰明确
3. 分析要有理有据
4. 适当表达情感

【禁忌】
1. 不要说"我查验了 X 号是村民/女巫"（只能说好人/狼人）
2. 不要一晚查验多人（规则不允许）
3. 不要查验死亡玩家
"""
```

### 3.2 夜晚行动提示词

```python
def build_seer_night_prompt(context: dict) -> str:
    """
    构建预言家夜晚行动提示词
    """
    checks_history_str = ", ".join([
        f"{pid}号={'好人' if result == 'good' else '狼人'}"
        for pid, result in context.get("checks_history", {}).items()
    ]) or "无"

    return f"""
【第{context["night_number"]}夜 预言家行动】

你是{context["my_id"]}号玩家，身份是预言家。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 查验历史：{checks_history_str}

【可选行动】
1. 查验玩家：{{"action": "check", "target": 玩家编号，"reason": "查验理由"}}
2. 不查验：{{"action": "none", "reason": "不查验理由"}}

【决策要点】
1. 第一夜建议查验身边位置或随机查验
2. 后续夜晚优先查验白天发言可疑的玩家
3. 避免重复查验同一人
4. 不能查验自己或死亡玩家
5. 返回必须是有效的 JSON 格式

请返回你的决策："""
```

### 3.3 白天发言提示词

```python
def build_seer_day_speech_prompt(context: dict) -> str:
    """
    构建预言家白天发言提示词
    """
    checks_history_str = ", ".join([
        f"{pid}号={'好人' if result == 'good' else '狼人'}"
        for pid, result in context.get("checks_history", {}).items()
    ]) or "无"

    should_reveal = context.get("should_reveal", False)

    return f"""
【第{context["day_number"]}天白天 第{context["round_num"]}轮发言】

你是{context["my_id"]}号玩家，身份是预言家。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 昨晚死亡：{', '.join([f'{p}号' for p in context["night_deaths"]]) if context["night_deaths"] else '无人死亡'}
- 你的查验历史：{checks_history_str}
- 是否有悍跳：{"是" if context.get("has_fake_seer") else "否"}

【发言策略】
""" + ("你需要跳身份报查验" if should_reveal else "你可以选择是否跳身份") + """

【发言要求】
1. """ + ("明确跳预言家身份" if should_reveal else "根据局势决定是否跳身份") + """
2. """ + ("报出昨晚查验结果" if should_reveal else "如跳身份，报出查验结果") + """
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

### 4.1 夜晚查验决策流程

```
夜晚开始
    ↓
检查存活玩家列表
    ↓
┌─────────────────────┐
│ 排除自己和已查验过的│
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 是否有可疑玩家？    │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 查验可疑玩家│  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 是否有未查验玩家│
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 随机查验一个 │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 返回查验目标    │
         └─────────────────┘
```

### 4.2 白天跳身份决策流程

```
白天发言前
    ↓
┌─────────────────────┐
│ 昨晚查验结果是什么？│
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  狼人         好人
   │             │
   ↓             │
┌─────────────┐  │
│ 跳身份报查验│  │
│ (必须)      │  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 是否有悍跳狼？  │
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 跳身份对刚   │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 是否被狼人查杀？│
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 跳身份反杀│       │
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
           │ 默认：隐藏身份│
           │ (继续查验)    │
           └───────────────┘
```

### 4.3 应对悍跳流程

```
发现有人悍跳预言家
    ↓
┌─────────────────────┐
│ 悍跳者报的查验是什么│
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  金水         查杀
   │             │
   ↓             ↓
┌─────────┐  ┌─────────────┐
│ 分析逻辑│  │ 被查杀了？  │
└────┬────┘  └──────┬──────┘
     │              │
     │       ┌──────┴──────┐
     │       │             │
     │      是            否
     │       │             │
     │       ↓             │
     │  ┌────────────┐     │
     │  │ 反查杀对方 │     │
     │  │ (必须)     │     │
     │  └─────┬──────┘     │
     │        │            │
     └────────┴────────────┘
              │
              ↓
     ┌─────────────────┐
     │ 发言要点：      │
     │ 1. 表明真身份   │
     │ 2. 报出自己查验 │
     │ 3. 指出对方漏洞 │
     │ 4. 呼吁好人投票 │
     └─────────────────┘
```

---

## 5. 常见场景及正确应对

### 场景 1：第一夜随机查验

**情境**:
```python
context = {
    "night_number": 1,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "checks_history": {},
}
```

**正确应对**:
```python
decision = {
    "action": "check",
    "target": 2,  # 查验身边位置
    "reason": "第一夜查验身边位置，2 号离我近"
}
```

**理由**: 第一夜没有信息，优先查验身边位置是标准打法。

---

### 场景 2：查验到狼人

**情境**:
```python
context = {
    "night_number": 1,
    "my_id": 3,
    "check_result": {"target": 5, "result": "werewolf"},
}
```

**正确应对**（白天发言）:
```
"我是预言家，昨晚查验了 5 号，5 号是狼人。
5 号今天必须出，好人跟我一起投票。
我昨晚第一夜查验，没有太多信息，
但 5 号是铁狼，今天不出 5 号好人难赢。"
```

**理由**: 查验到狼人必须立即跳身份报查验，帮助好人投票。

---

### 场景 3：查验到好人

**情境**:
```python
context = {
    "night_number": 1,
    "my_id": 3,
    "check_result": {"target": 5, "result": "good"},
}
```

**正确应对**（白天发言 - 选择隐藏）:
```
"我是好人牌，目前没有太多信息。
5 号我暂时认他好人，但不说具体原因。
今天先听其他人发言。"
```

**理由**: 查验到好人可以先隐藏身份，避免过早暴露。

---

### 场景 4：有狼人悍跳

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "fake_seer_id": 7,  # 7 号悍跳预言家
    "fake_seer_claim": "5 号是好人",
    "my_check_result": {"target": 5, "result": "good"},
}
```

**正确应对**（白天发言）:
```
"我是真预言家，昨晚查验了 5 号是好人。
7 号你悍跳我，你才是狼。
我昨晚第一夜查验 5 号，你就跟着我报 5 号金水，
想蹭我热度？好人跟我一起出 7 号。"
```

**理由**: 有悍跳狼必须对刚，指出对方漏洞。

---

### 场景 5：被狼人查杀

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "accused_by": 7,
    "accuser_claim": "3 号是狼人",
    "my_check_result": {"target": 5, "result": "werewolf"},
}
```

**正确应对**（白天发言）:
```
"7 号查杀我？我是真预言家！
7 号你才是狼，悍跳查杀我。
我昨晚查验了 5 号是狼人，5 号和 7 号是两狼。
好人跟我一起出 7 号，今天不出 7 号好人输了。"
```

**理由**: 被查杀必须反查杀，表明身份对刚。

---

### 场景 6：第二夜查验可疑玩家

**情境**:
```python
context = {
    "night_number": 2,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
    "checks_history": {2: "good"},
    "suspect_list": [7],  # 7 号白天发言可疑
}
```

**正确应对**:
```python
decision = {
    "action": "check",
    "target": 7,
    "reason": "7 号白天发言划水，像狼人"
}
```

**理由**: 第二夜优先查验白天发言可疑的玩家。

---

### 场景 7：决赛圈查验

**情境**:
```python
context = {
    "night_number": 3,
    "my_id": 3,
    "alive_players": [1, 3, 5, 7],
    "checks_history": {1: "good", 5: "good"},
    "suspect_list": [7],
}
```

**正确应对**:
```python
decision = {
    "action": "check",
    "target": 7,
    "reason": "决赛圈查验 7 号，确定最后狼人"
}
```

**理由**: 决赛圈查验关键玩家，帮助好人投票。

---

### 场景 8：查验历史被相信

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "checks_history": {5: "good", 7: "werewolf"},
    "trusted_by": [1, 2, 4],  # 多人相信预言家
}
```

**正确应对**（白天发言）:
```
"我是预言家，已经查验了 5 号好人、7 号狼人。
7 号已经被出了，现在场上还剩 1 狼。
我继续查验，今天出 X 号，他发言有问题。"
```

**理由**: 被相信后继续带队，帮助好人找狼。

---

### 场景 9：查验历史不被相信

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "checks_history": {5: "good"},
    "doubted_by": [2, 4, 7],  # 多人怀疑预言家
}
```

**正确应对**（白天发言）:
```
"我是真预言家，你们怀疑我没关系。
我昨晚查验了 5 号是好人，我可以保 5 号。
今天先出 X 号，他发言最像狼。
好人会明白的。"
```

**理由**: 被怀疑时坚持身份，用后续查验证明自己。

---

### 场景 10：所有人都查验过了

**情境**:
```python
context = {
    "night_number": 4,
    "my_id": 3,
    "alive_players": [1, 3, 5],
    "checks_history": {1: "good", 5: "good", 2: "werewolf", 
                       4: "good", 6: "good", 7: "werewolf", 
                       8: "good", 9: "good"},
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "所有存活玩家都已查验过，无需再验"
}
```

**理由**: 所有人都查验过后，夜晚不需要再浪费查验。

---

### 场景 11：双预言家对跳

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "fake_seer_id": 5,
    "my_check": {"target": 7, "result": "good"},
    "fake_seer_check": {"target": 7, "result": "werewolf"},
}
```

**正确应对**（白天发言）:
```
"5 号和我都查验了 7 号，结果完全相反。
我报 7 号好人，5 号报 7 号狼人。
我们两个必有一真一假。
好人今天先出 5 号，出完看晚上刀谁。
如果 5 号是狼，今晚我会被刀。"
```

**理由**: 对跳时让好人投票决定，用夜晚结果证明。

---

### 场景 12：查验到狼人不立即跳

**情境**:
```python
context = {
    "day_number": 1,
    "my_id": 3,
    "check_result": {"target": 7, "result": "werewolf"},
    "strategy": "hide",  # 选择隐藏
}
```

**正确应对**（白天发言 - 隐藏）:
```
"我是好人牌，目前没有太多信息。
今天先听其他人发言。"
```

**夜晚再跳**:
```
"我是预言家，昨晚查验了 7 号是狼人。
我昨天隐藏是因为想多查验几人，
现在 7 号必须出。"
```

**理由**: 有时可以隐藏一晚，但风险较大（可能被刀）。

---

### 场景 13：夜晚被刀后遗言

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "is_dead": True,  # 预言家被刀
    "checks_history": {5: "good", 7: "werewolf"},
}
```

**正确应对**（遗言）:
```
"我是预言家，被刀了。
我查验了 5 号好人、7 号狼人。
7 号还没出，今天好人必须出 7 号。
5 号可以带队，他是好人。"
```

**理由**: 遗言报出所有查验信息，帮助好人继续游戏。

---

### 场景 14：查验到自刀狼

**情境**:
```python
context = {
    "night_number": 2,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
    "checks_history": {5: "good"},
    "dead_player": 7,  # 7 号昨晚死亡（可能是自刀）
}
```

**正确应对**:
```python
decision = {
    "action": "check",
    "target": 2,  # 查验其他可疑玩家
    "reason": "7 号已死，查验其他玩家"
}
```

**理由**: 死亡玩家无法查验，继续查验其他可疑玩家。

---

### 场景 15：警徽流（有警长机制）

**情境**:
```python
context = {
    "day_number": 1,
    "my_id": 3,
    "is_police_candidate": True,  # 竞选警长
    "check_result": {"target": 5, "result": "good"},
}
```

**正确应对**（竞选发言）:
```
"我是预言家，昨晚查验了 5 号是好人。
我竞选警长，警徽流如下：
今晚查验 2 号，明晚查验 8 号。
如果我死了，警徽给 5 号。
好人投票给我。"
```

**理由**: 有警徽机制时，报出警徽流让好人相信。

---

## 6. 禁忌行为

### 6.1 查验禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 查验自己 | 查验自己的身份 | 无效操作 |
| ❌ 查验死亡玩家 | 查验已经死亡的玩家 | 无效操作 |
| ❌ 重复查验 | 查验已经查验过的玩家 | 浪费机会 |
| ❌ 一晚查验多人 | 一晚查验多个玩家 | 违反规则 |
| ❌ 查验结果错误 | 报出错误的查验结果 | 被当狼打 |

### 6.2 发言禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 暴露具体身份 | "X 号是村民/女巫" | 违反查验规则 |
| ❌ 假报查验 | 报出虚假查验结果 | 被当狼打 |
| ❌ 遗漏查验 | 查验到狼人不报 | 帮助狼人 |
| ❌ 过晚报查验 | 多晚后才报查验 | 失去信任 |
| ❌ 发言矛盾 | 前后查验不一致 | 被当狼打 |

### 6.3 决策禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 查验到狼不跳 | 隐藏查验到的狼人 | 狼人可能逃脱 |
| ❌ 被悍跳不刚 | 不应对悍跳狼 | 失去好人信任 |
| ❌ 乱报警徽流 | 无明确计划 | 失去警徽 |
| ❌ 决赛圈隐藏 | 决赛圈还不跳 | 好人输掉 |
| ❌ 跟狼投票 | 跟随狼人投票 | 帮助狼人 |

---

## 7. 日志记录规范

### 7.1 必须记录的事件

```python
# 预言家相关日志事件类型
SEER_LOG_EVENTS = {
    "seer_check": "预言家查验",
    "seer_reveal": "预言家跳身份",
    "seer_death": "预言家死亡",
    "seer_fake": "有人悍跳预言家",
}
```

### 7.2 查验日志

```python
def log_seer_check(context: dict, decision: dict, result: str) -> None:
    """
    记录预言家查验

    日志格式:
    {
        "type": "seer_check",
        "data": {
            "night": 2,
            "seer_id": 3,
            "target": 5,
            "result": "good",  # good/werewolf
            "checks_history": {2: "good"},
            "reason": "查验理由",
            "timestamp": "2026-03-06T12:34:56"
        }
    }
    """
    log_entry = {
        "type": "seer_check",
        "data": {
            "night": context["night_number"],
            "seer_id": context["my_id"],
            "target": decision.get("target"),
            "result": result,
            "checks_history": context.get("checks_history", {}),
            "reason": decision.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        }
    }
    game_state.add_history("seer_check", log_entry["data"])
```

### 7.3 跳身份日志

```python
def log_seer_reveal(context: dict, speech: str) -> None:
    """
    记录预言家跳身份

    日志格式:
    {
        "type": "seer_reveal",
        "data": {
            "day": 2,
            "seer_id": 3,
            "check_reported": {"target": 5, "result": "good"},
            "speech": "发言内容",
            "has_fake_seer": True,
            "timestamp": "..."
        }
    }
    """
```

### 7.4 完整日志示例

```json
{
  "type": "seer_check",
  "data": {
    "night": 1,
    "seer_id": 3,
    "target": 5,
    "result": "werewolf",
    "checks_history": {},
    "reason": "第一夜随机查验",
    "timestamp": "2026-03-06T12:34:56"
  }
}
```

---

## 8. 测试用例

### 测试 1：第一夜查验身边玩家

```python
def test_seer_check_nearby_first_night():
    """
    测试用例：第一夜预言家查验身边玩家

    前置条件:
    - 第 1 夜
    - 预言家是 3 号
    - 所有玩家存活

    预期结果:
    - 预言家查验 2 号或 4 号（身边位置）
    """
    context = {
        "night_number": 1,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "checks_history": {},
    }

    decision = seer_decide_night_action(context)

    # 验证结果
    assert decision["action"] == "check"
    assert decision["target"] in [2, 4]  # 身边位置
```

---

### 测试 2：不能查验自己

```python
def test_seer_cannot_check_self():
    """
    测试用例：预言家不能查验自己

    前置条件:
    - 第 2 夜
    - 预言家是 3 号

    预期结果:
    - 预言家不会选择查验自己
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
        "checks_history": {},
    }

    decision = seer_decide_night_action(context)

    # 验证：不能查验自己
    assert decision["action"] != "check" or decision["target"] != 3
```

---

### 测试 3：不能查验死亡玩家

```python
def test_seer_cannot_check_dead_player():
    """
    测试用例：预言家不能查验死亡玩家

    前置条件:
    - 第 2 夜
    - 有玩家已死亡

    预期结果:
    - 预言家不会选择查验死亡玩家
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 6, 7, 8],  # 5 号已死
        "checks_history": {},
        "dead_players": [5],
    }

    decision = seer_decide_night_action(context)

    # 验证：不能查验死亡玩家
    assert decision["action"] != "check" or decision["target"] not in [5]
```

---

### 测试 4：查验到狼人应该跳身份

```python
def test_seer_reveal_when_check_werewolf():
    """
    测试用例：查验到狼人应该跳身份

    前置条件:
    - 第 1 夜查验到狼人
    - 白天发言

    预期结果:
    - 预言家跳身份报查验
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "check_result": {"target": 5, "result": "werewolf"},
        "checks_history": {5: "werewolf"},
    }

    speech = seer_day_speech(context)

    # 验证：发言中包含预言家身份和查验结果
    assert "预言家" in speech
    assert "5 号" in speech
    assert "狼人" in speech
```

---

### 测试 5：应对悍跳狼

```python
def test_seer_counter_fake_seer():
    """
    测试用例：有悍跳狼时应该对刚

    前置条件:
    - 有人悍跳预言家
    - 白天发言

    预期结果:
    - 预言家跳身份
    - 指出对方是悍跳
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "fake_seer_id": 7,
        "checks_history": {5: "good"},
    }

    speech = seer_day_speech(context)

    # 验证：发言中指出对方悍跳
    assert "预言家" in speech
    assert "7 号" in speech
    assert "悍跳" in speech or "假" in speech
```

---

### 测试 6：查验历史正确记录

```python
def test_seer_check_history_recorded():
    """
    测试用例：查验历史正确记录

    前置条件:
    - 第 2 夜
    - 第 1 夜查验过 5 号

    预期结果:
    - 查验历史包含 5 号
    - 不会重复查验 5 号
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
        "checks_history": {5: "good"},  # 第 1 夜查验 5 号
    }

    decision = seer_decide_night_action(context)

    # 验证：不会重复查验 5 号
    assert decision["action"] != "check" or decision["target"] != 5
```

---

### 测试 7：决赛圈跳身份带队

```python
def test_seer_reveal_in_final_circle():
    """
    测试用例：决赛圈应该跳身份带队

    前置条件:
    - 剩 3-4 人
    - 预言家存活

    预期结果:
    - 预言家跳身份
    - 给出明确投票建议
    """
    context = {
        "day_number": 4,
        "my_id": 3,
        "alive_players": [1, 3, 5, 7],  # 剩 4 人
        "checks_history": {1: "good", 5: "good"},
    }

    speech = seer_day_speech(context)

    # 验证：发言中包含身份和明确建议
    assert "预言家" in speech
    assert "出" in speech or "投票" in speech
```

---

### 测试 8：查验结果只能是好人/狼人

```python
def test_seer_check_result_binary():
    """
    测试用例：查验结果只能是好人或狼人

    前置条件:
    - 查验任意玩家

    预期结果:
    - 结果只能是"good"或"werewolf"
    - 不能是"villager"、"witch"等具体身份
    """
    context = {
        "night_number": 1,
        "my_id": 3,
        "target": 5,
    }

    result = seer_check_target(context)

    # 验证：结果只能是二元
    assert result in ["good", "werewolf"]
```

---

### 测试 9：被查杀时反查杀

```python
def test_seer_counter_accuse():
    """
    测试用例：被狼人查杀时应该反查杀

    前置条件:
    - 被狼人查杀
    - 白天发言

    预期结果:
    - 预言家跳身份
    - 反查杀对方
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "accused_by": 7,
        "accuser_claim": "3 号是狼人",
        "checks_history": {5: "good"},
    }

    speech = seer_day_speech(context)

    # 验证：发言中反查杀对方
    assert "预言家" in speech
    assert "7 号" in speech
    assert "狼" in speech
```

---

### 测试 10：查验状态正确传递

```python
def test_seer_check_status_passed_correctly():
    """
    测试用例：查验状态正确传递给 AI

    前置条件:
    - 第 2 夜
    - 查验历史正确

    预期结果:
    - AI 知道查验历史
    - 不会重复查验
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
        "checks_history": {5: "good"},  # 正确传递状态
    }

    decision, inner_thought = agent.decide_night_action(context)

    # 验证：AI 知道查验历史
    assert decision["action"] != "check" or decision["target"] != 5
    # 或者内心独白中提到查验历史
    assert "5 号" in inner_thought or decision["action"] == "none"
```

---

## 附录 A：现有代码位置

### A.1 核心代码文件

| 文件路径 | 内容 | 行号范围 |
|---------|------|---------|
| `core/game_engine.py` | 游戏引擎，预言家行动处理 | 250-280 |
| `ai/agent.py` | AI 代理，预言家夜晚决策 | 200-250 |
| `games/werewolf/roles.py` | 角色定义 | 1-20 |
| `core/state.py` | 游戏状态，查验历史 | 1-100 |

### A.2 关键代码片段

#### 预言家行动处理（game_engine.py）

```python
def _handle_seer_action(self) -> dict:
    """处理预言家行动"""
    seers = [p for p in self.state.get_alive_players() 
             if p.role == Role.SEER]
    if not seers:
        return {}

    seer = seers[0]
    alive_players = [p.id for p in self.state.get_alive_players()]
    action = {}
    inner_thought = ""

    if seer.is_human:
        # 人类玩家输入
        ...
    else:
        agent = self.agents[seer.id]
        context = {
            "alive_players": alive_players,
            "my_id": seer.id,
            "checks_history": self.seer_checks_history.get(seer.id, {}),
        }
        action, inner_thought_raw = agent.decide_night_action(context)
        # ... 处理查验
```

#### AI 夜晚决策（agent.py）

```python
def decide_night_action(self, context: dict) -> tuple[dict, str]:
    """决定夜晚行动"""
    if self.player.role == Role.SEER:
        checks_history = context.get("checks_history", {})
        alive_players = context.get("alive_players", [])
        my_id = context.get("my_id")

        # 排除自己和已查验过的
        candidates = [p for p in alive_players 
                      if p != my_id and p not in checks_history]

        prompt = f"""你是{my_id}号玩家，身份是预言家..."""
        # ... 生成决策
```

---

## 附录 B：待审查问题清单

### B.1 逻辑问题

| 问题 ID | 描述 | 严重程度 | 状态 |
|--------|------|---------|------|
| S-001 | 查验结果是否正确（好人/狼人二元） | P0 | 待审查 |
| B.2 查验历史是否正确记录和传递 | P0 | 待审查 |
| S-003 | 悍跳检测逻辑是否实现 | P1 | 待审查 |
| S-004 | 预言家跳身份逻辑是否合理 | P1 | 待审查 |
| S-005 | 警徽流机制是否支持 | P2 | 待审查 |

### B.2 代码审查要点

1. **状态管理**
   - [ ] `seer_checks_history` 是否正确初始化
   - [ ] 查验结果是否正确记录
   - [ ] 状态是否正确传递给 AI

2. **决策逻辑**
   - [ ] AI 是否正确理解查验规则
   - [ ] 第一夜查验策略是否合理
   - [ ] 查验到狼人是否立即跳身份

3. **日志记录**
   - [ ] 预言家查验是否完整记录
   - [ ] 内心独白是否保存
   - [ ] 查验历史是否可追溯

### B.3 测试覆盖

| 测试场景 | 是否有测试 | 测试文件 |
|---------|-----------|---------|
| 第一夜查验 | ❓ | 待添加 |
| 不能查验自己 | ❓ | 待添加 |
| 不能查验死亡玩家 | ❓ | 待添加 |
| 查验到狼人跳身份 | ❓ | 待添加 |
| 应对悍跳 | ❓ | 待添加 |

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-06 | 初始版本 | BotBattle Team |

---

**文档结束**
