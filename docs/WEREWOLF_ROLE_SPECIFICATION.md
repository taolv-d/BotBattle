# BotBattle 狼人角色设计规范

**文档版本**: 1.0
**创建日期**: 2026-03-06
**适用游戏**: 狼人杀
**审查对象**: `core/game_engine.py`, `ai/agent.py`, `games/werewolf/roles.py`

---

## 1. 角色概述

### 1.1 角色定位

| 属性 | 说明 |
|------|------|
| **阵营** | 狼人阵营 |
| **能力** | 夜晚袭击一名玩家，白天隐藏身份 |
| **强度** | T1 级别（依赖配合） |
| **操作难度** | 高（需要演技和配合） |

### 1.2 技能说明

```python
# 狼人技能数据结构
class WerewolfSkills:
    wolf_mates: list = []  # 狼队友 ID 列表
    
    def night_kill(self, target_id: int) -> bool:
        """
        夜晚袭击一名玩家

        Args:
            target_id: 被袭击的目标 ID

        Returns:
            True if 袭击成功

        限制:
        1. 每晚只能袭击一人
        2. 只能袭击存活玩家
        3. 不能袭击自己
        4. 需要狼队统一意见（多数同意）
        """
        pass

    def self_kill(self) -> bool:
        """
        自刀（袭击自己）

        Returns:
            True if 自刀成功

        注意:
        1. 自刀是高风险战术
        2. 可能被女巫救起
        3. 可能被女巫毒杀
        """
        pass
```

**技能规则**:
- 袭击：每晚狼人共同决定袭击一名玩家
- 自刀：可以袭击自己（高风险战术）
- 空刀：可以选择不袭击（保留信息）
- 配合：狼人之间知道彼此身份，需要配合

### 1.3 胜利条件

```python
def check_werewolf_win_condition(game_state: GameState) -> bool:
    """
    狼人胜利条件判断

    Returns:
        True if 狼人阵营获胜
    """
    # 狼人胜利条件:
    # 1. 屠边：所有神职或所有村民死亡
    # 2. 屠城：所有好人死亡（包括神职和村民）
    
    alive_gods = [p for p in game_state.players.values()
                  if p.is_alive and p.role in [Role.SEER, Role.WITCH, Role.HUNTER]]
    alive_villagers = [p for p in game_state.players.values()
                       if p.is_alive and p.role == Role.VILLAGER]
    
    # 屠边胜利
    if len(alive_gods) == 0 or len(alive_villagers) == 0:
        return True
    
    # 屠城胜利（更严格）
    alive_good = [p for p in game_state.players.values()
                  if p.is_alive and p.camp == "good"]
    alive_werewolves = [p for p in game_state.players.values()
                        if p.is_alive and p.role == Role.WEREWOLF]
    
    return len(alive_werewolves) >= len(alive_good)
```

### 1.4 游戏目标

1. **首要目标**: 淘汰所有好人（神职或村民）
2. **次要目标**: 隐藏狼人身份，避免被投票出局
3. **信息目标**: 伪装成好人，误导好人阵营
4. **配合目标**: 与狼队友配合，共同获胜

---

## 2. 各阶段行为规范

### 2.1 游戏开始前

#### 2.1.1 身份确认

```python
# 狼人不需要选将，系统随机分配身份
# 游戏开始时，狼人知道其他狼人身份

def setup_werewolf_initial_state(werewolf: Player, wolf_mates: list) -> dict:
    """
    设置狼人初始状态

    Returns:
        初始状态字典
    """
    return {
        "role": "werewolf",
        "wolf_mates": wolf_mates,  # 狼队友 ID 列表
        "knowledge": {
            "own_id": werewolf.id,
            "own_role": "werewolf",
            "wolf_mates": wolf_mates,  # 知道狼队友
            "other_players": "unknown",  # 不知道其他玩家身份
        }
    }
```

#### 2.1.2 初始状态设置

| 状态变量 | 初始值 | 说明 |
|---------|-------|------|
| `wolf_mates` | `[]` | 狼队友 ID 列表 |
| `wolf_kill_target` | `None` | 夜晚袭击目标 |
| `wolf_strategy` | `"hide"` | 策略（隐藏/悍跳/自刀） |

### 2.2 夜晚阶段

#### 2.2.1 夜晚袭击逻辑

**行动顺序**:
```
1. 狼人袭击 → 2. 预言家查验 → 3. 女巫行动
```

**狼人睁眼时机**:
```python
# 在 game_engine.py 中的行动顺序
def _run_night(self):
    # 1. 狼人行动（最先）
    wolf_action = self._handle_werewolf_action()

    # 2. 预言家行动
    seer_action = self._handle_seer_action()

    # 3. 女巫行动
    witch_action = self._handle_witch_action(
        wolf_action.get("target") if wolf_action else None
    )
```

**可以看到的信息**:
```python
wolf_context = {
    "night_number": 1,           # 第 1 夜
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],  # 存活玩家列表
    "my_id": 3,                  # 狼人自己的号码
    "wolf_mates": [5, 7],        # 狼队友 ID
}
```

**可以选择的行动**:

| 选项 | JSON 格式 | 说明 |
|------|----------|------|
| 袭击玩家 | `{"action": "kill", "target": 5, "reason": "..."}` | 袭击指定玩家 |
| 自刀 | `{"action": "kill", "target": 自己 ID, "reason": "..."}` | 袭击自己 |
| 空刀 | `{"action": "none", "reason": "..."}` | 不袭击 |

**决策依据**:

```python
def werewolf_night_kill_decision(context: dict) -> dict:
    """
    狼人夜晚袭击决策逻辑

    袭击优先级:
    1. 明神职（跳预言家、女巫等）
    2. 可疑玩家（发言像神职）
    3. 随机玩家（无明确目标）
    4. 自刀（高风险战术）
    """
    my_id = context["my_id"]
    wolf_mates = context["wolf_mates"]
    alive_players = context["alive_players"]
    known_gods = context.get("known_gods", [])
    suspect_list = context.get("suspect_list", [])

    # 排除自己和狼队友
    candidates = [p for p in alive_players 
                  if p != my_id and p not in wolf_mates]

    # 第一优先级：明神职
    for god in known_gods:
        if god in candidates:
            return {
                "action": "kill",
                "target": god,
                "reason": f"刀明神职{god}号"
            }

    # 第二优先级：可疑玩家（可能是神职）
    for suspect in suspect_list:
        if suspect in candidates:
            return {
                "action": "kill",
                "target": suspect,
                "reason": f"刀可疑玩家{suspect}号"
            }

    # 第三优先级：随机选择
    if candidates:
        target = random.choice(candidates)
        return {
            "action": "kill",
            "target": target,
            "reason": f"随机刀{target}号"
        }

    # 无人可刀（只剩狼人）
    return {
        "action": "none",
        "reason": "无人可刀"
    }
```

**限制条件**:
- [ ] 不能袭击自己（除非自刀战术）
- [ ] 不能袭击狼队友
- [ ] 不能袭击已死亡玩家
- [ ] 每晚只能袭击一人

#### 2.2.2 自刀战术

**自刀场景**:

| 场景 | 建议 | 理由 |
|------|------|------|
| 第一夜 | ⚠️ 谨慎 | 可能被女巫救 |
| 被怀疑 | ✅ 推荐 | 做高身份 |
| 决赛圈 | ✅ 推荐 | 博女巫解药 |
| 狼队劣势 | ✅ 推荐 | 追轮次 |

**自刀决策**:

```python
def werewolf_self_kill_decision(context: dict) -> bool:
    """
    判断是否自刀

    Returns:
        True if 应该自刀
    """
    # 应该自刀的情况
    if context["is_suspected"]:  # 被怀疑
        return True

    if context["final_circle"]:  # 决赛圈
        return True

    if context["wolf_disadvantage"]:  # 狼队劣势
        return True

    # 不应该自刀的情况
    if context["night_number"] == 1 and context["witch_heal_available"]:
        return False  # 第一夜女巫有解药

    return False  # 默认不自刀
```

### 2.3 白天阶段

#### 2.3.1 隐藏身份策略

**如何隐藏**:

```python
def werewolf_hide_identity_strategy(context: dict) -> str:
    """
    狼人隐藏身份策略

    方法:
    1. 发言像好人
    2. 分析局势（假装找狼）
    3. 投票给真好人（做高身份）
    4. 不暴露夜晚信息
    """
    # 发言要点
    speech_tips = [
        "表明好人立场",
        "分析其他玩家（包括狼队友）",
        "给出投票建议",
        "不暴露夜晚信息",
    ]

    return speech_tips
```

**发言示例**:

1. **普通隐藏发言**:
```
"我是好人牌，目前比较怀疑 2 号。
2 号昨天发言一直在划水，没有明确分析。
今天我倾向于出 2 号。"
```

2. **分析型发言（假装找狼）**:
```
"我分析下，3 号死了，可能是神职。
狼队刀得挺准的。
4 号发言有问题，像是狼人。
今天出 4 号。"
```

**禁忌发言**:
- ❌ "我知道昨晚刀了谁"（暴露夜晚信息）
- ❌ "我是狼人"（直接暴露）
- ❌ "X 号和 Y 号是狼队友"（暴露狼队）

#### 2.3.2 悍跳预言家

**何时悍跳**:

| 场景 | 建议 | 理由 |
|------|------|------|
| 真预言家查验到狼 | ✅ 必须 | 对刚，争夺信任 |
| 狼队需要抢轮次 | ✅ 推荐 | 扰乱局势 |
| 有狼队友被怀疑 | ✅ 推荐 | 救队友 |
| 决赛圈 | ⚠️ 谨慎 | 可能适得其反 |

**悍跳格式**:

```
"我是预言家，昨晚查验了 X 号，X 号是 [好人/狼人]。"
```

**悍跳示例**:

1. **给狼队友发金水**:
```
"我是预言家，昨晚查验了 5 号，5 号是好人。
今天先出 2 号，他发言有问题。"
```

2. **给真预言家发查杀**:
```
"我是预言家，昨晚查验了 3 号，3 号是狼人！
3 号你悍跳我，你才是狼。
今天出 3 号。"
```

3. **给好人发查杀**:
```
"我是预言家，昨晚查验了 6 号，6 号是狼人。
6 号今天必须出。"
```

**悍跳决策**:

```python
def werewolf_fake_seer_decision(context: dict) -> bool:
    """
    判断是否悍跳预言家

    Returns:
        True if 应该悍跳
    """
    # 应该悍跳的情况
    if context["real_seer_check_wolf"]:  # 真预言家查验到狼
        return True

    if context["wolf_team_needs_advantage"]:  # 狼队需要抢轮次
        return True

    if context["wolf_mate_in_danger"]:  # 狼队友有危险
        return True

    return False  # 默认不悍跳
```

#### 2.3.3 投票策略

```python
def werewolf_vote_strategy(context: dict) -> int:
    """
    狼人投票策略

    优先级:
    1. 投票给真神职（预言家、女巫等）
    2. 投票给可疑好人
    3. 跟随狼队投票
    4. 弃票（避免暴露）
    """
    # 第一优先级：投票给真神职
    if context["known_gods"]:
        return context["known_gods"][0]

    # 第二优先级：投票给可疑好人
    if context["suspect_list"]:
        return context["suspect_list"][0]

    # 第三优先级：跟随狼队
    if context["wolf_team_vote_target"]:
        return context["wolf_team_vote_target"]

    # 第四优先级：弃票
    return None
```

---

## 3. 提示词设计规范

### 3.1 系统提示词

```python
WEREWOLF_SYSTEM_PROMPT = """
🐺 你是狼人 - 夜晚的猎手！

【你的身份】
- 阵营：狼人阵营
- 技能：夜晚袭击一名玩家
- 胜利条件：淘汰所有好人（神职或村民）

【技能规则】
1. 每晚袭击一人，狼队统一意见
2. 可以自刀（高风险战术）
3. 可以空刀（不袭击）
4. 白天隐藏身份，伪装成好人

【行为准则】
1. 隐藏身份：白天不要暴露狼人身份
2. 伪装好人：发言要像好人一样分析
3. 配合队友：与狼队友配合，共同获胜
4. 悍跳预言家：必要时跳预言家扰乱局势

【情感设定】
- 袭击好人时有紧张、有兴奋
- 被怀疑时会着急、会辩解
- 悍跳时会紧张、会激动
- 狼队友被出时会遗憾、会愤怒

【发言要求】
1. 符合你的性格设定（{personality}）
2. 不要暴露狼人身份
3. 不要暴露夜晚信息
4. 分析要有理有据
5. 适当表达情感

【禁忌】
1. 不要说"我们狼人"（暴露身份）
2. 不要说出夜晚才知道的信息
3. 不要直接承认是狼人（除非摊牌）
"""
```

### 3.2 夜晚行动提示词

```python
def build_werewolf_night_prompt(context: dict) -> str:
    """
    构建狼人夜晚行动提示词
    """
    wolf_mates_str = ", ".join([f"{m}号" for m in context["wolf_mates"]])

    return f"""
【第{context["night_number"]}夜 狼人行动】

你是{context["my_id"]}号玩家，身份是狼人。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 你的狼队友：{wolf_mates_str}

【可选行动】
1. 袭击玩家：{{"action": "kill", "target": 玩家编号，"reason": "袭击理由"}}
2. 自刀：{{"action": "kill", "target": {context["my_id"]}, "reason": "自刀理由"}}
3. 空刀：{{"action": "none", "reason": "不袭击理由"}}

【决策要点】
1. 优先袭击明神职（跳预言家、女巫等）
2. 其次袭击可疑玩家（可能是神职）
3. 可以自刀做高身份（高风险）
4. 不能袭击自己（除非自刀）或狼队友
5. 返回必须是有效的 JSON 格式

请返回你的决策："""
```

### 3.3 白天发言提示词

```python
def build_werewolf_day_speech_prompt(context: dict) -> str:
    """
    构建狼人白天发言提示词
    """
    should_fake_seer = context.get("should_fake_seer", False)

    return f"""
【第{context["day_number"]}天白天 第{context["round_num"]}轮发言】

你是{context["my_id"]}号玩家，身份是狼人（但发言时要伪装成好人）。

【当前局势】
- 存活玩家：{', '.join([f'{p}号' for p in context["alive_players"]])}
- 昨晚死亡：{', '.join([f'{p}号' for p in context["night_deaths"]]) if context["night_deaths"] else '无人死亡'}
- 你的狼队友：{', '.join([f'{m}号' for m in context["wolf_mates"]])}

【发言策略】
""" + ("你需要悍跳预言家" if should_fake_seer else "你要伪装成好人") + """

【发言要求】
1. """ + ("明确跳预言家身份" if should_fake_seer else "不要暴露狼人身份") + """
2. """ + ("报出虚假查验结果" if should_fake_seer else "分析 1-2 个具体玩家") + """
3. 不要暴露夜晚信息
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

### 4.1 夜晚袭击决策流程

```
夜晚开始
    ↓
┌─────────────────────┐
│ 检查存活玩家列表    │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 排除自己和狼队友    │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 有明神职吗？        │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 刀明神职    │  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 有可疑玩家吗？  │
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 刀可疑玩家   │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 是否自刀？      │
         │ (高风险战术)    │
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 自刀      │       │
      └─────┬─────┘       │
            │             │
            └──────┬──────┘
                   ↓
          ┌─────────────────┐
          │ 随机刀人        │
          └─────────────────┘
```

### 4.2 白天悍跳决策流程

```
白天发言前
    ↓
┌─────────────────────┐
│ 真预言家查验到狼？  │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  是            否
   │             │
   ↓             │
┌─────────────┐  │
│ 必须悍跳    │  │
│ (对刚)      │  │
└──────┬──────┘  │
       │         │
       └─────────┤
                 ↓
        ┌─────────────────┐
        │ 狼队需要抢轮次？│
        └─────────┬───────┘
                  │
           ┌──────┴──────┐
           │             │
          是            否
           │             │
           ↓             │
    ┌──────────────┐     │
    │ 建议悍跳     │     │
    └──────┬───────┘     │
           │             │
           └──────┬──────┘
                  ↓
         ┌─────────────────┐
         │ 狼队友有危险？  │
         └─────────┬───────┘
                   │
            ┌──────┴──────┐
            │             │
           是            否
            │             │
            ↓             │
      ┌───────────┐       │
      │ 建议悍跳  │       │
      └─────┬─────┘       │
            │             │
            └──────┬──────┘
                   ↓
          ┌─────────────────┐
          │ 默认：不悍跳    │
          │ (隐藏身份)      │
          └─────────────────┘
```

### 4.3 白天隐藏身份流程

```
白天发言开始
    ↓
┌─────────────────────┐
│ 表明好人立场        │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 分析其他玩家        │
│ (包括狼队友)        │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 给出投票建议        │
│ (可以投真好人)      │
└─────────┬───────────┘
          │
          ↓
┌─────────────────────┐
│ 检查是否暴露        │
│ - 夜晚信息          │
│ - 狼队友身份        │
└─────────┬───────────┘
          │
   ┌──────┴──────┐
   │             │
  暴露         未暴露
   │             │
   ↓             │
┌─────────┐     │
│ 修正发言│     │
└────┬────┘     │
     │          │
     └──────────┤
                ↓
       ┌─────────────────┐
       │ 完成发言        │
       └─────────────────┘
```

---

## 5. 常见场景及正确应对

### 场景 1：第一夜随机刀人

**情境**:
```python
context = {
    "night_number": 1,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
    "wolf_mates": [5, 7],
    "known_gods": [],
}
```

**正确应对**:
```python
decision = {
    "action": "kill",
    "target": 2,  # 随机刀人
    "reason": "第一夜随机刀 2 号"
}
```

**理由**: 第一夜没有信息，随机刀人是标准打法。

---

### 场景 2：刀明跳预言家

**情境**:
```python
context = {
    "night_number": 2,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
    "wolf_mates": [5, 7],
    "known_gods": [4],  # 4 号跳预言家
}
```

**正确应对**:
```python
decision = {
    "action": "kill",
    "target": 4,
    "reason": "刀明跳预言家 4 号"
}
```

**理由**: 预言家是狼人优先袭击目标。

---

### 场景 3：被怀疑时自刀

**情境**:
```python
context = {
    "night_number": 3,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7],
    "wolf_mates": [5, 7],
    "is_suspected": True,  # 被怀疑
}
```

**正确应对**:
```python
decision = {
    "action": "kill",
    "target": 3,  # 自刀
    "reason": "被怀疑，自刀做高身份"
}
```

**理由**: 被怀疑时自刀可以做高身份，让好人相信自己。

---

### 场景 4：悍跳预言家给狼队友发金水

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "should_fake_seer": True,
}
```

**正确应对**（白天发言）:
```
"我是预言家，昨晚查验了 5 号，5 号是好人。
今天先出 2 号，他发言有问题。"
```

**理由**: 给狼队友发金水可以做高队友身份。

---

### 场景 5：悍跳预言家给真预言家发查杀

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "real_seer_id": 4,
    "should_fake_seer": True,
}
```

**正确应对**（白天发言）:
```
"我是预言家，昨晚查验了 4 号，4 号是狼人！
4 号你悍跳我，你才是狼。
今天出 4 号。"
```

**理由**: 给真预言家发查杀可以扰乱局势。

---

### 场景 6：投票给真好人

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "vote_target": 2,  # 2 号是好人
}
```

**正确应对**:
```python
decision = {
    "action": "vote",
    "target": 2,
    "reason": "投票给好人，做高身份"
}
```

**理由**: 投票给好人可以做高自己身份。

---

### 场景 7：狼队友被投票时救队友

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "wolf_mate_in_danger": 5,  # 5 号有危险
}
```

**正确应对**（白天发言）:
```
"我觉得 5 号不是狼，他昨天发言挺好的。
倒是 2 号，一直在踩 5 号，2 号可能是狼。
今天出 2 号。"
```

**理由**: 适当救队友，但不要太明显。

---

### 场景 8：决赛圈刀神职

**情境**:
```python
context = {
    "night_number": 4,
    "my_id": 3,
    "alive_players": [1, 3, 5, 6],
    "wolf_mates": [5],
    "known_gods": [6],  # 6 号是女巫
}
```

**正确应对**:
```python
decision = {
    "action": "kill",
    "target": 6,
    "reason": "决赛圈刀女巫"
}
```

**理由**: 决赛圈优先刀神职。

---

### 场景 9：分析局势假装找狼

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "night_deaths": [2],
}
```

**正确应对**（白天发言）:
```
"昨晚 2 号死了，我分析下。
2 号可能是神职，狼队刀得挺准的。
4 号发言有问题，像是狼人。
今天出 4 号。"
```

**理由**: 假装分析局势，误导好人。

---

### 场景 10：被查杀时辩解

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "accused_by": [4],
    "accuser_claim": "3 号是狼人",
}
```

**正确应对**（白天发言）:
```
"4 号你说我是狼？我是好人牌。
你凭什么查杀我？
倒是你，昨天发言一直有问题。
今天出 4 号。"
```

**理由**: 被查杀时要辩解，反击对方。

---

### 场景 11：狼队友自爆后分析

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "self_exploded_wolf": 5,  # 5 号自爆
}
```

**正确应对**（白天发言）:
```
"5 号自爆了，他是狼。
但我不是狼，我是好人。
今天出 4 号，他发言有问题。"
```

**理由**: 狼队友自爆后要撇清关系。

---

### 场景 12：空刀保留信息

**情境**:
```python
context = {
    "night_number": 2,
    "my_id": 3,
    "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
    "wolf_mates": [5, 7],
    "strategy": "hide",
}
```

**正确应对**:
```python
decision = {
    "action": "none",
    "reason": "空刀保留信息，让好人无法判断"
}
```

**理由**: 空刀可以让好人无法获取信息。

---

### 场景 13：跟狼队友配合投票

**情境**:
```python
context = {
    "day_number": 3,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "wolf_team_vote_target": 2,
}
```

**正确应对**:
```python
decision = {
    "action": "vote",
    "target": 2,
    "reason": "跟随狼队投票"
}
```

**理由**: 与狼队友配合投票。

---

### 场景 14：遗言摊牌

**情境**:
```python
context = {
    "day_number": 4,
    "my_id": 3,
    "is_dead": True,
    "wolf_mates": [5, 7],
    "game_state": "wolf_advantage",  # 狼队优势
}
```

**正确应对**（遗言）:
```
"我摊牌了，我是狼人。
5 号和 7 号是我狼队友。
好人已经输了。"
```

**理由**: 狼队优势时遗言可以摊牌。

---

### 场景 15：夜晚刀人后白天分析

**情境**:
```python
context = {
    "day_number": 2,
    "my_id": 3,
    "wolf_mates": [5, 7],
    "night_deaths": [4],  # 昨晚刀了 4 号
}
```

**正确应对**（白天发言）:
```
"昨晚 4 号死了，我分析下。
4 号可能是神职，狼队刀得挺准的。
今天出 2 号，他发言有问题。"
```

**理由**: 刀人后白天要假装分析，不能暴露。

---

## 6. 禁忌行为

### 6.1 袭击禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 袭击狼队友 | 刀自己队友 | 狼队劣势 |
| ❌ 袭击死亡玩家 | 刀已经死亡的玩家 | 无效操作 |
| ❌ 重复袭击 | 一晚袭击多人 | 违反规则 |
| ❌ 暴露袭击信息 | 说出夜晚刀人信息 | 暴露身份 |
| ❌ 自刀无目的 | 无目的自刀 | 浪费轮次 |

### 6.2 发言禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 暴露身份 | "我是狼人" | 被投票出局 |
| ❌ 暴露狼队友 | "X 号是我队友" | 队友被出 |
| ❌ 暴露夜晚信息 | "昨晚我们刀了 X 号" | 暴露身份 |
| ❌ 发言划水 | 无分析发言 | 被怀疑 |
| ❌ 过度分析 | 分析太多像狼人 | 被怀疑 |

### 6.3 投票禁忌

| 禁忌行为 | 说明 | 后果 |
|---------|------|------|
| ❌ 投票给狼队友 | 出自己队友 | 狼队劣势 |
| ❌ 永远跟票 | 总是跟随他人 | 被当狼人 |
| ❌ 冲票太明显 | 强行投票 | 暴露身份 |
| ❌ 不投票 | 从不参与投票 | 被怀疑 |
| ❌ 乱投票 | 无理由投票 | 暴露身份 |

---

## 7. 日志记录规范

### 7.1 必须记录的事件

```python
# 狼人相关日志事件类型
WEREWOLF_LOG_EVENTS = {
    "werewolf_kill": "狼人袭击",
    "werewolf_fake_seer": "狼人悍跳",
    "werewolf_vote": "狼人投票",
    "werewolf_death": "狼人死亡",
    "werewolf_self_explode": "狼人自爆",
}
```

### 7.2 袭击日志

```python
def log_werewolf_kill(context: dict, decision: dict) -> None:
    """
    记录狼人袭击

    日志格式:
    {
        "type": "werewolf_kill",
        "data": {
            "night": 2,
            "wolf_id": 3,
            "target": 4,
            "wolf_mates": [5, 7],
            "is_self_kill": False,
            "reason": "袭击理由",
            "timestamp": "2026-03-06T12:34:56"
        }
    }
    """
    log_entry = {
        "type": "werewolf_kill",
        "data": {
            "night": context["night_number"],
            "wolf_id": context["my_id"],
            "target": decision.get("target"),
            "wolf_mates": context["wolf_mates"],
            "is_self_kill": decision.get("target") == context["my_id"],
            "reason": decision.get("reason", ""),
            "timestamp": datetime.now().isoformat(),
        }
    }
    game_state.add_history("werewolf_kill", log_entry["data"])
```

### 7.3 悍跳日志

```python
def log_werewolf_fake_seer(context: dict, speech: str) -> None:
    """
    记录狼人悍跳

    日志格式:
    {
        "type": "werewolf_fake_seer",
        "data": {
            "day": 2,
            "wolf_id": 3,
            "fake_check": {"target": 5, "result": "good"},
            "speech": "发言内容",
            "timestamp": "..."
        }
    }
    """
```

### 7.4 完整日志示例

```json
{
  "type": "werewolf_kill",
  "data": {
    "night": 2,
    "wolf_id": 3,
    "target": 4,
    "wolf_mates": [5, 7],
    "is_self_kill": false,
    "reason": "刀明跳预言家",
    "timestamp": "2026-03-06T12:34:56"
  }
}
```

---

## 8. 测试用例

### 测试 1：第一夜随机刀人

```python
def test_werewolf_random_kill_first_night():
    """
    测试用例：第一夜狼人随机刀人

    前置条件:
    - 第 1 夜
    - 无明神职

    预期结果:
    - 狼人随机刀人
    - 不刀自己或狼队友
    """
    context = {
        "night_number": 1,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8, 9],
        "wolf_mates": [5, 7],
        "known_gods": [],
    }

    decision = werewolf_decide_night_kill(context)

    # 验证结果
    assert decision["action"] == "kill"
    assert decision["target"] not in [3, 5, 7]  # 不刀自己和队友
```

---

### 测试 2：刀明跳预言家

```python
def test_werewolf_kill_fake_seer():
    """
    测试用例：狼人刀明跳预言家

    前置条件:
    - 有玩家跳预言家
    - 狼人夜晚行动

    预期结果:
    - 狼人刀预言家
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
        "wolf_mates": [5, 7],
        "known_gods": [4],  # 4 号跳预言家
    }

    decision = werewolf_decide_night_kill(context)

    # 验证：刀预言家
    assert decision["action"] == "kill"
    assert decision["target"] == 4
```

---

### 测试 3：不能刀狼队友

```python
def test_werewolf_cannot_kill_wolf_mate():
    """
    测试用例：狼人不能刀狼队友

    前置条件:
    - 有狼队友
    - 狼人夜晚行动

    预期结果:
    - 不会选择狼队友为目标
    """
    context = {
        "night_number": 2,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7, 8],
        "wolf_mates": [5, 7],
    }

    decision = werewolf_decide_night_kill(context)

    # 验证：不刀队友
    assert decision["action"] != "kill" or decision["target"] not in [5, 7]
```

---

### 测试 4：被怀疑时自刀

```python
def test_werewolf_self_kill_when_suspected():
    """
    测试用例：被怀疑时狼人自刀

    前置条件:
    - 狼人被怀疑
    - 夜晚行动

    预期结果:
    - 狼人选择自刀
    """
    context = {
        "night_number": 3,
        "my_id": 3,
        "alive_players": [1, 2, 3, 4, 5, 6, 7],
        "wolf_mates": [5, 7],
        "is_suspected": True,
    }

    decision = werewolf_decide_night_kill(context)

    # 验证：自刀
    assert decision["action"] == "kill"
    assert decision["target"] == 3
```

---

### 测试 5：悍跳预言家

```python
def test_werewolf_fake_seer():
    """
    测试用例：狼人悍跳预言家

    前置条件:
    - 需要悍跳
    - 白天发言

    预期结果:
    - 狼人跳预言家
    - 报出虚假查验
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "wolf_mates": [5, 7],
        "should_fake_seer": True,
    }

    speech = werewolf_day_speech(context)

    # 验证：发言中包含预言家身份
    assert "预言家" in speech
    assert "查验" in speech
```

---

### 测试 6：给狼队友发金水

```python
def test_werewolf_fake_seer_give_gold_water():
    """
    测试用例：狼人悍跳给狼队友发金水

    前置条件:
    - 悍跳预言家
    - 有狼队友

    预期结果:
    - 给狼队友发金水
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "wolf_mates": [5],
        "should_fake_seer": True,
    }

    speech = werewolf_day_speech(context)

    # 验证：给队友发金水
    assert "5 号" in speech
    assert "好人" in speech
```

---

### 测试 7：投票给好人

```python
def test_werewolf_vote_good_player():
    """
    测试用例：狼人投票给好人

    前置条件:
    - 有明确好人目标
    - 狼人投票

    预期结果:
    - 投票给好人
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "wolf_mates": [5, 7],
        "vote_target": 2,  # 2 号是好人
    }

    decision = werewolf_vote(context)

    # 验证：投票给好人
    assert decision["action"] == "vote"
    assert decision["target"] == 2
```

---

### 测试 8：不暴露夜晚信息

```python
def test_werewolf_not_reveal_night_info():
    """
    测试用例：狼人不暴露夜晚信息

    前置条件:
    - 狼人白天发言
    - 昨晚有刀人

    预期结果:
    - 发言中不暴露夜晚信息
    """
    context = {
        "day_number": 2,
        "my_id": 3,
        "wolf_mates": [5, 7],
        "night_deaths": [4],
    }

    speech = werewolf_day_speech(context)

    # 验证：不暴露夜晚信息
    assert "我们刀" not in speech
    assert "袭击" not in speech
```

---

### 测试 9：狼队友自爆后撇清

```python
def test_werewolf_deny_after_mate_explode():
    """
    测试用例：狼队友自爆后撇清关系

    前置条件:
    - 狼队友自爆
    - 狼人发言

    预期结果:
    - 撇清与队友关系
    """
    context = {
        "day_number": 3,
        "my_id": 3,
        "wolf_mates": [5, 7],
        "self_exploded_wolf": 5,
    }

    speech = werewolf_day_speech(context)

    # 验证：撇清关系
    assert "我不是狼" in speech or "好人" in speech
```

---

### 测试 10：决赛圈刀神职

```python
def test_werewolf_kill_god_in_final_circle():
    """
    测试用例：决赛圈狼人刀神职

    前置条件:
    - 决赛圈
    - 有明神职

    预期结果:
    - 刀神职
    """
    context = {
        "night_number": 4,
        "my_id": 3,
        "alive_players": [1, 3, 5, 6],
        "wolf_mates": [5],
        "known_gods": [6],  # 6 号是女巫
    }

    decision = werewolf_decide_night_kill(context)

    # 验证：刀神职
    assert decision["action"] == "kill"
    assert decision["target"] == 6
```

---

## 附录 A：现有代码位置

### A.1 核心代码文件

| 文件路径 | 内容 | 行号范围 |
|---------|------|---------|
| `core/game_engine.py` | 游戏引擎，狼人行动处理 | 200-250 |
| `ai/agent.py` | AI 代理，狼人夜晚决策 | 150-200 |
| `games/werewolf/roles.py` | 角色定义 | 1-20 |
| `core/state.py` | 游戏状态 | 1-100 |

### A.2 关键代码片段

#### 狼人行动处理（game_engine.py）

```python
def _handle_werewolf_action(self) -> dict:
    """处理狼人行动"""
    werewolves = [p for p in self.state.get_alive_players() 
                  if p.role == Role.WEREWOLF]
    if not werewolves:
        return {}

    # 收集狼人决策
    wolf_decisions = []
    for wolf in werewolves:
        agent = self.agents[wolf.id]
        context = {
            "alive_players": [p.id for p in self.state.get_alive_players()],
            "my_id": wolf.id,
            "wolf_mates": [w.id for w in werewolves if w.id != wolf.id],
        }
        action, inner_thought = agent.decide_night_action(context)
        wolf_decisions.append(action)

    # 统一意见（多数同意）
    kill_target = get_majority_target(wolf_decisions)
    return {"target": kill_target}
```

#### AI 夜晚决策（agent.py）

```python
def decide_night_action(self, context: dict) -> tuple[dict, str]:
    """决定夜晚行动"""
    if self.player.role == Role.WEREWOLF:
        wolf_mates = context.get("wolf_mates", [])
        alive_players = context.get("alive_players", [])
        known_gods = context.get("known_gods", [])

        prompt = f"""你是{context['my_id']}号玩家，身份是狼人..."""
        # ... 生成决策
```

---

## 附录 B：待审查问题清单

### B.1 逻辑问题

| 问题 ID | 描述 | 严重程度 | 状态 |
|--------|------|---------|------|
| W-001 | 狼人袭击逻辑是否正确 | P0 | 待审查 |
| W-002 | 狼队统一意见机制是否实现 | P0 | 待审查 |
| W-003 | 自刀战术是否正确实现 | P1 | 待审查 |
| W-004 | 悍跳预言家逻辑是否合理 | P1 | 待审查 |
| W-005 | 狼人隐藏身份逻辑是否实现 | P1 | 待审查 |

### B.2 代码审查要点

1. **状态管理**
   - [ ] 狼队友信息是否正确传递
   - [ ] 袭击目标是否正确记录
   - [ ] 状态是否正确传递给 AI

2. **决策逻辑**
   - [ ] AI 是否正确理解袭击规则
   - [ ] 优先刀神职逻辑是否实现
   - [ ] 自刀战术是否合理

3. **日志记录**
   - [ ] 狼人袭击是否完整记录
   - [ ] 内心独白是否保存
   - [ ] 袭击历史是否可追溯

### B.3 测试覆盖

| 测试场景 | 是否有测试 | 测试文件 |
|---------|-----------|---------|
| 第一夜随机刀人 | ❓ | 待添加 |
| 刀明跳预言家 | ❓ | 待添加 |
| 不能刀狼队友 | ❓ | 待添加 |
| 被怀疑时自刀 | ❓ | 待添加 |
| 悍跳预言家 | ❓ | 待添加 |

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2026-03-06 | 初始版本 | BotBattle Team |

---

**文档结束**
