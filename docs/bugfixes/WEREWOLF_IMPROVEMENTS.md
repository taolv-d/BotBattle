# 狼人杀改进说明

**改进日期**: 2026-03-05  
**改进内容**: AI 自我认知 + 夜晚行动内心活动展示 + 投票内心活动展示

---

## 问题 1：AI 不知道自己号码

### 问题描述
AI 发言时会出现逻辑矛盾，例如：
> "4 号玩家说：我要等等 4 号的发言后再决定"

这是不合理的，因为 4 号玩家不会说"等 4 号的发言"。

### 解决方案

在 `ai/agent.py` 的 `speak()` 方法中添加了明确的自我认知提示：

```python
user_prompt = f"""【第{day}天白天 第{round_num}轮发言】
...
7. 注意：你是{self.player.id}号玩家，发言时不要提到自己的号码（如"我 4 号认为"是错误的）
"""
```

### 改进效果
- ✅ AI 清楚知道自己是几号玩家
- ✅ 发言时不会提到自己的号码
- ✅ 逻辑更加合理自然

---

## 问题 2：夜晚行动缺少内心活动展示

### 问题描述
上帝视角只能看到行动结果，看不到：
- 狼人为什么选择袭击这个目标
- 预言家为什么查验这个人
- 女巫为什么使用救药/毒药

### 解决方案

#### 1. 修改 AI 夜晚决策方法

**文件**: `ai/agent.py`

```python
def decide_night_action(self, context: dict) -> tuple[dict, str]:
    """
    决定夜晚行动
    
    Returns:
        (行动决策，内心独白)
    """
    # 添加自我认知
    my_id = context.get("my_id", self.player.id)
    
    # 狼人 prompt
    prompt = f"""你是{my_id}号玩家，身份是狼人...
    请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}"""
    
    # 预言家 prompt
    prompt = f"""你是{my_id}号玩家，身份是预言家...
    请返回 JSON 格式：{{"target": 玩家编号，"reason": "选择理由/内心想法"}}"""
    
    # 女巫 prompt
    prompt = f"""你是{my_id}号玩家，身份是女巫...
    请返回 JSON 格式：{{"action": "heal/poison/none", "target": 玩家编号，"reason": "选择理由/内心想法"}}"""
```

#### 2. 修改游戏引擎处理逻辑

**文件**: `core/game_engine.py`

**狼人行动**:
```python
def _handle_werewolf_action(self) -> dict:
    # 收集狼人选择
    action, inner_thought = agent.decide_night_action(context)
    
    # 记录内心活动
    wolf_thoughts.append(f"{wolf.id}号 ({wolf.celebrity_name}) 的内心：{inner_thought}")
    
    # 显示狼人内心活动（上帝视角）
    self.ui.display_system_message("=== 狼人行动（上帝视角） ===")
    for thought in wolf_thoughts:
        self.ui.display_inner_thought("狼人", thought)
```

**预言家行动**:
```python
def _handle_seer_action(self) -> dict:
    action, inner_thought = agent.decide_night_action(context)
    inner_thought = f"{seer.id}号 ({seer.celebrity_name}) 的内心：{inner_thought}"
    return {"target": action.get("target"), "thought": inner_thought}
```

**女巫行动**:
```python
def _handle_witch_action(self, dead_player_id: Optional[int]) -> dict:
    action, inner_thought_raw = agent.decide_night_action(context)
    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}"
    
    # 显示女巫内心活动（上帝视角）
    if inner_thought:
        self.ui.display_system_message("=== 女巫行动（上帝视角） ===")
        self.ui.display_inner_thought("女巫", inner_thought)
```

**夜晚结果处理**:
```python
def _process_night_results(self, wolf_action, seer_action, witch_action):
    # 显示预言家内心活动和查验结果（上帝视角）
    if seer_action.get("target"):
        thought = seer_action.get("thought", "")
        if thought:
            self.ui.display_system_message("=== 预言家行动（上帝视角） ===")
            self.ui.display_inner_thought("预言家", thought)
        
        # 显示查验结果
        self.ui.display_system_message(f"预言家查验了 {target_id}号，结果是：{role_name}")
```

### 改进效果

#### 上帝视角示例输出

```
=== 狼人行动（上帝视角） ===
[狼人] 4 号 (曹操) 的内心：3 号玩家发言很可疑，像是预言家，今晚先刀他
[狼人] 7 号 (司马懿) 的内心：同意刀 3 号，他是明好人
狼人选择了袭击 3 号玩家

=== 预言家行动（上帝视角） ===
[预言家] 2 号 (诸葛亮) 的内心：查验 5 号，他发言太少了，需要更多信息
预言家查验了 5 号，结果是：村民

=== 女巫行动（上帝视角） ===
[女巫] 6 号 (华佗) 的内心：3 号是好人，使用救药救他
女巫使用了解药
```

---

## 问题 3：投票时缺少内心活动展示

### 问题描述
上帝视角只能看到投票结果，看不到：
- 每个玩家投给了谁
- 为什么投给这个玩家
- 投票的推理过程

### 解决方案

#### 1. 修改 AI 投票方法

**文件**: `ai/agent.py`

```python
def vote(self, context: dict) -> tuple[Optional[int], str]:
    """
    投票决定放逐谁
    
    Returns:
        (投票目标，内心独白)
    """
    my_id = context.get("my_id", self.player.id)  # 自己的号码
    
    prompt = f"""你是{my_id}号玩家，身份是{self.player.role.value}...
    请返回 JSON 格式：{{"vote": 玩家编号 或 null, "reason": "投票理由/内心想法"}}"""
```

#### 2. 修改游戏引擎投票处理

**文件**: `core/game_engine.py`

```python
def _run_vote(self) -> None:
    """运行投票阶段 - 展示内心活动"""
    
    # 收集投票
    for player in alive_players:
        if not player.is_human:
            vote, inner_thought = agent.vote(context)
            vote_thoughts[player.id] = f"{player.id}号 ({player.celebrity_name}-{player.role.value}) 投票给 {vote}号：{inner_thought}"
    
    # 显示所有玩家的投票内心活动（上帝视角）
    self.ui.display_system_message("--- 投票详情（上帝视角） ---")
    for voter_id in sorted(vote_thoughts.keys()):
        thought = vote_thoughts[voter_id]
        self.ui.display_inner_thought(f"{voter_id}号", thought)
```

### 改进效果

#### 上帝视角示例输出

```
=== 投票阶段（上帝视角） ===
--- 投票详情（上帝视角） ---
[1 号] 1 号 (李白 -villager) 投票给 7 号：7 号发言太少了，一直在划水
[2 号] 2 号 (曹操 -werewolf) 投票给 3 号：3 号跳预言家，但我怀疑他是假的
[3 号] 3 号 (诸葛亮 -seer) 投票给 7 号：我是真预言家，7 号明显是狼
[4 号] 4 号 (华佗 -witch) 投票给 7 号：7 号不敢分析别人，行为可疑
[5 号] 5 号 (鲁迅 -villager) 投票给 2 号：2 号无故踩我，可能是狼
[6 号] 6 号 (嬴政 -hunter) 投票给 7 号：大家都投 7 号，我跟随
[7 号] 7 号 (项羽 -villager)：弃权，没有明确目标

3 号玩家被放逐，请留遗言：
```

### 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `ai/agent.py` | 1. `vote()` 返回 `(vote, reason)`<br>2. 添加自我认知和信任/怀疑提示 |
| `core/game_engine.py` | 1. `_run_vote()` 显示投票内心活动<br>2. `_run_president_election()` 显示警长投票内心活动 |

---

## 修改文件清单

| 文件 | 修改内容 |
|------|---------|
| `ai/agent.py` | 1. `speak()` 添加自我认知提示<br>2. `decide_night_action()` 返回内心独白<br>3. `vote()` 返回投票理由 |
| `core/game_engine.py` | 1. `_handle_werewolf_action()` 显示狼人内心<br>2. `_handle_seer_action()` 返回预言家内心<br>3. `_handle_witch_action()` 显示女巫内心<br>4. `_process_night_results()` 显示查验结果<br>5. `_run_vote()` 显示投票内心活动<br>6. `_run_president_election()` 显示警长投票内心活动 |

---

## 测试方法

### 运行测试脚本
```bash
cd E:\04project\BotBattle

# 改进功能综合测试
python tests/werewolf/test_improvements.py

# 投票内心活动测试
python tests/werewolf/test_vote_thoughts.py

# 完整游戏测试
python tests/werewolf/test_quick.py
```

### 测试覆盖

| 测试文件 | 测试内容 |
|---------|---------|
| `test_improvements.py` | 1. AI 自我认知<br>2. 夜晚行动内心独白 |
| `test_vote_thoughts.py` | 投票内心活动展示 |
| `test_quick.py` | 完整游戏流程 |

---

## 使用示例

### AI 发言（已知自己号码）
```
[4 号玩家 (诸葛亮)-村民] 我认为 7 号玩家发言很可疑，大家要注意。
  -> (4 号玩家的内心独白：我确实是村民，7 号刚才的发言逻辑有问题)
```

### 夜晚行动（上帝视角）
```
=== 狼人行动（上帝视角） ===
[狼人] 4 号 (曹操) 的内心：5 号玩家一直在划水，可能是神职，今晚刀他
[狼人] 7 号 (司马懿) 的内心：5 号确实可疑，同意

=== 预言家行动（上帝视角） ===
[预言家] 2 号 (诸葛亮) 的内心：查验 4 号，他发言太激进了
预言家查验了 4 号，结果是：狼人

=== 女巫行动（上帝视角） ===
[女巫] 6 号 (华佗) 的内心：今晚不救人，留毒药后面用
```

---

## 后续优化建议

1. **更详细的内心活动**
   - 记录 AI 的完整思考过程
   - 保存到日志文件供复盘使用

2. **多狼人交流**
   - 狼人之间可以讨论战术
   - 记录讨论过程（上帝视角可见）

3. **白天发言优化**
   - 添加发言前的思考时间
   - 显示 AI 分析其他玩家的过程

4. **日志增强**
   - 所有内心活动写入日志
   - 支持赛后完整复盘
