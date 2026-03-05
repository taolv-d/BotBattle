# BotBattle 规范驱动开发 (SDD) 文档

## 项目概述

**项目名称**: BotBattle - AI 狼人杀游戏引擎

**核心目标**: 提供一个可扩展的 AI 大乱斗游戏框架，支持狼人杀、剧本杀等轮流对话型游戏。

**技术栈**:
- Python 3.10+
- LLM API (DeepSeek/Kimi/通义千问等)
- 模块化架构 (UI 与逻辑分离)

---

## 一、架构规范

### 1.1 模块依赖关系

```
┌─────────────┐
│    main.py  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  config_loader  │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌──────┐  ┌────────┐
│  UI  │  │ Engine │
└──────┘  └───┬────┘
              │
         ┌────┴────┐
         ▼         ▼
      ┌────┐   ┌──────┐
      │ AI │   │Games │
      └────┘   └──────┘
```

**规范**:
- `main.py` 只能导入 `config_loader`, `UI`, `GameEngine`
- `UI` 模块不能依赖 `core`, `ai`, `games`
- `core` 模块只能导入 `ai`, `ui.base`
- `ai` 模块不能导入 `core`, `games`
- `games` 模块只能导入 `core`, `ai`

### 1.2 数据流规范

```
用户输入 → UI → GameEngine → AI → 响应 → UI → 用户
                ↓
              Logger (记录所有事件)
```

---

## 二、核心模块规范

### 2.1 GameEngine 模块

**文件**: `core/game_engine.py`

#### 2.1.1 类定义

```python
class GameEngine:
    """
    游戏引擎 - 控制游戏完整流程
    
    Attributes:
        ui: UI 接口实例
        config: 配置字典
        state: GameState 实例
        agents: dict[int, AIAgent] - 玩家 ID 到 AI 代理的映射
        president_id: int | None - 警长 ID
        witch_heal_used: bool - 女巫解药是否已用
        witch_poison_used: bool - 女巫毒药是否已用
    """
```

#### 2.1.2 方法规范

##### `__init__(ui: UIBase, config: dict) -> None`
- **输入**: 
  - `ui`: 实现 `UIBase` 接口的实例
  - `config`: 系统配置字典
- **输出**: None
- **副作用**: 初始化所有属性为默认值
- **约束**: 不执行任何 I/O 操作

##### `setup(player_count, roles_config, personalities, human_player_id) -> None`
- **输入**:
  - `player_count`: int (6-15)
  - `roles_config`: list[dict] - 角色配置列表
  - `personalities`: list[str] - 人格名称列表
  - `human_player_id`: int | None - 人类玩家 ID
- **输出**: None
- **前置条件**: 
  - `6 <= player_count <= 15`
  - `roles_config` 中角色总数等于 `player_count`
- **后置条件**:
  - `self.state.players` 包含所有玩家
  - 每个玩家分配了角色和人格
  - 日志文件初始化完成
- **异常**: 
  - `ValueError` - 玩家数量超出范围
  - `ValueError` - 角色数量不匹配

##### `_run_night() -> list[int]`
- **输入**: None
- **输出**: `night_deaths` - 夜晚死亡玩家 ID 列表
- **前置条件**: 游戏处于夜晚阶段
- **后置条件**:
  - 狼人完成袭击
  - 预言家完成查验（如有）
  - 女巫完成用药（如有）
  - 记录 `night_actions_summary` 事件
- **日志事件**:
  - `night_start`
  - `night_death` (如有死亡)
  - `seer_check` (如有查验)
  - `night_actions_summary`

##### `_run_day() -> None`
- **输入**: None
- **输出**: None
- **前置条件**: 游戏处于白天阶段
- **后置条件**:
  - 完成警长竞选（第 1 天）
  - 完成 2 轮发言
  - 完成投票
  - 处理遗言和猎人技能
- **日志事件**:
  - `day_start`
  - `president_*` (第 1 天)
  - `inner_thought` (每轮发言)
  - `day_vote`
  - `player_eliminated` (如有人被放逐)

##### `_run_president_election() -> None`
- **输入**: None
- **输出**: None
- **前置条件**: 第 1 天白天，警长未确定
- **后置条件**:
  - `self.president_id` 设置为当选者或保持 None
  - 记录完整竞选过程
- **日志事件**:
  - `president_election_start`
  - `president_candidates`
  - `president_speech` (每个候选人)
  - `president_vote`
  - `president_elected` 或 `president_election_end`

##### `_run_discussion(rounds: int = 2) -> None`
- **输入**: 
  - `rounds`: int (默认 2) - 发言轮数
- **输出**: None
- **前置条件**: 有存活玩家
- **后置条件**:
  - 每个存活玩家完成指定轮数发言
  - 所有 AI 更新信任和怀疑列表
  - 记录所有内心独白
- **日志事件**:
  - `inner_thought` (每个 AI 每轮)

##### `_run_vote() -> None`
- **输入**: None
- **输出**: None
- **前置条件**: 完成讨论阶段
- **后置条件**:
  - 记录投票详情
  - 处理被放逐者（遗言、猎人技能）
  - 检查游戏是否结束
- **日志事件**:
  - `day_vote`
  - `last_words` (如有被放逐)
  - `hunter_skill` (如猎人发动技能)
  - `player_eliminated` (如有被放逐)

##### `_end_game() -> None`
- **输入**: None
- **输出**: None
- **前置条件**: 游戏结束条件达成
- **后置条件**:
  - 记录完整游戏复盘
  - 显示所有玩家身份
- **日志事件**:
  - `game_over`

---

### 2.2 AIAgent 模块

**文件**: `ai/agent.py`

#### 2.2.1 类定义

```python
class AIAgent:
    """
    AI 玩家代理 - 模拟玩家行为
    
    Attributes:
        player: Player 实例
        personality: Personality 实例
        llm: LLMClient 实例
        memory: list[dict] - 记忆列表（最多 100 条）
        trust_list: list[int] - 信任的玩家 ID
        suspect_list: list[int] - 怀疑的玩家 ID
        hidden_task: str | None - 隐藏任务
    """
```

#### 2.2.2 方法规范

##### `speak(context: dict, round_num: int) -> tuple[str, str]`
- **输入**:
  - `context`: dict - 包含以下键：
    - `day_number`: int
    - `night_deaths`: list[int]
    - `previous_speeches`: list[dict]
    - `alive_players`: list[int]
  - `round_num`: int - 发言轮数
- **输出**: `(speech, inner_thought)` - 发言内容和内心独白
- **约束**:
  - 发言长度在 `personality.min_length` 和 `personality.max_length` 之间
  - 必须分析至少 1-2 个具体玩家
  - 第 2 轮发言需回应之前的质疑或支持
- **副作用**: 
  - 添加发言到记忆
  - 更新信任和怀疑列表

##### `analyze_speech(speech: str, speaker_id: int) -> None`
- **输入**:
  - `speech`: str - 其他玩家的发言
  - `speaker_id`: int - 发言玩家 ID
- **输出**: None
- **约束**:
  - 不分析自己的发言
  - 根据关键词更新信任/怀疑列表
- **规则**:
  - 提到"怀疑我"或"狼" → 添加怀疑
  - 提到"信任我"或"金水" → 添加信任
  - 发言激进且短 (<30 字，含"必须出") → 添加怀疑
  - 发言详细且含"分析" (>80 字) → 添加信任
- **副作用**: 更新 `trust_list` 或 `suspect_list`

##### `vote(context: dict) -> int | None`
- **输入**:
  - `context`: dict - 包含 `alive_players`
- **输出**: 
  - 投票目标玩家 ID，或 None（弃票）
- **约束**:
  - 只能投给存活玩家
  - 可以弃票
- **决策依据**:
  - `suspect_list` 中的玩家优先级高
  - 参考之前的发言内容

##### `decide_night_action(context: dict) -> dict`
- **输入**:
  - `context`: dict - 包含 `alive_players`, `wolf_teammates` (狼人), `dead_player` (女巫)
- **输出**: 
  - 狼人：`{"target": int}`
  - 预言家：`{"target": int}`
  - 女巫：`{"action": "heal"|"poison"|"none", "target": int}`
- **约束**:
  - 目标必须是存活玩家
  - 女巫不能自救（首夜后）

---

### 2.3 GameState 模块

**文件**: `core/state.py`

#### 2.3.1 数据结构

```python
@dataclass
class Player:
    id: int
    name: str
    role: Role | None
    personality: str | None
    is_alive: bool = True
    is_human: bool = False
    is_bot: bool = True
```

```python
@dataclass
class GameState:
    player_count: int = 9
    players: dict[int, Player]
    phase: Phase
    day_number: int = 0
    night_number: int = 0
    president_id: int | None = None
    game_over: bool = False
    winner: str | None = None
    history: list[dict] = []
```

#### 2.3.2 方法规范

##### `check_game_over() -> bool`
- **输入**: None
- **输出**: `bool` - 游戏是否结束
- **规则**:
  - 狼人全部死亡 → 好人胜利
  - 狼人数量 >= 好人数量 → 狼人胜利
- **副作用**: 设置 `game_over` 和 `winner`

##### `get_alive_players() -> list[Player]`
- **输入**: None
- **输出**: 存活玩家列表
- **约束**: 不修改状态

---

### 2.4 UI 模块

**文件**: `ui/base.py`, `ui/cli.py`

#### 2.4.1 接口规范

```python
class UIBase(ABC):
    @abstractmethod
    def display_message(speaker: str, message: str) -> None:
        """显示玩家发言"""
        pass
    
    @abstractmethod
    def display_inner_thought(speaker: str, thought: str) -> None:
        """显示内心独白（可选）"""
        pass
    
    @abstractmethod
    def get_player_input(prompt: str) -> str:
        """获取玩家输入"""
        pass
    
    @abstractmethod
    def notify_game_event(event_type: str, data: dict) -> None:
        """通知游戏事件"""
        pass
    
    @abstractmethod
    def display_system_message(message: str) -> None:
        """显示系统消息"""
        pass
```

#### 2.4.2 CLI 实现约束

- 不使用 emoji（Windows 编码兼容）
- 内心独白默认不显示（写入日志）
- 所有输入有默认值处理（防止空输入崩溃）

---

## 三、日志规范

### 3.1 日志文件结构

```json
{
  "state": { /* 最终游戏状态 */ },
  "history": [
    {"type": "event_name", "data": {...}},
    ...
  ]
}
```

### 3.2 事件类型规范

| 事件类型 | 触发时机 | 必要字段 |
|---------|---------|---------|
| `game_setup` | 游戏初始化 | `player_count`, `roles`, `human_player_id` |
| `game_start` | 游戏开始 | `player_count` |
| `night_start` | 夜晚开始 | `night`, `alive_players` |
| `night_death` | 玩家死亡 | `player_id`, `role`, `cause` |
| `seer_check` | 预言家查验 | `target`, `result` |
| `night_actions_summary` | 夜晚行动汇总 | `wolf_action`, `seer_action`, `witch_action`, `night_deaths` |
| `day_start` | 白天开始 | `day`, `alive_players` |
| `president_election_start` | 警长竞选开始 | `day` |
| `president_candidates` | 候选人公布 | `candidates`, `candidate_names` |
| `president_speech` | 竞选发言 | `player_id`, `speech`, `inner_thought` |
| `president_vote` | 警长投票 | `vote_counts`, `vote_details`, `voters` |
| `president_elected` | 警长当选 | `president_id`, `votes`, `total_voters` |
| `president_election_end` | 竞选结束 | `reason`, `tied_candidates` (如平票) |
| `inner_thought` | AI 内心独白 | `player_id`, `thought`, `round` |
| `day_vote` | 白天投票 | `vote_counts`, `vote_details`, `alive_players` |
| `last_words` | 遗言 | `player_id`, `words` |
| `hunter_skill` | 猎人技能 | `hunter_id`, `target` |
| `player_eliminated` | 玩家被放逐 | `player_id`, `role`, `votes` |
| `game_over` | 游戏结束 | `winner`, `total_days`, `final_players`, `death_log` |

### 3.3 日志完整性要求

**必须记录的流程**:
1. 警长竞选：候选人 → 发言 → 投票 → 结果
2. 每轮发言：所有存活玩家的内心独白
3. 投票：每个玩家的投票选择
4. 夜晚行动：狼人目标、预言家查验、女巫用药
5. 游戏结束：完整复盘

---

## 四、配置规范

### 4.1 system.json 规范

```json
{
  "llm": {
    "provider": "string (required)",
    "api_key": "string (required)",
    "model": "string (required)",
    "base_url": "string (required)",
    "temperature": "number (0-1, default 0.7)",
    "timeout": "number (seconds, default 180)",
    "retry_count": "number (default 5)",
    "retry_delay": "number (seconds, default 3)"
  },
  "game": {
    "default_player_count": "number (default 9)",
    "max_player_count": "number (default 15)",
    "speech_timeout": "number (seconds, default 60)",
    "ai_speech_delay": "number (seconds, default 0.5)"
  },
  "log": {
    "save_dir": "string (default 'logs')",
    "save_inner_thoughts": "boolean (default true)",
    "verbose": "boolean (default false)"
  }
}
```

### 4.2 游戏配置规范

```json
{
  "name": "string",
  "player_count": "number",
  "roles": [
    {"role": "string", "count": "number"}
  ],
  "personalities": ["string"],
  "game_rules": {
    "discussion_rounds": "number (default 2)",
    "has_president_election": "boolean (default true)",
    "has_last_words": "boolean (default true)",
    "hunter_can_skill": "boolean (default true)"
  }
}
```

### 4.3 人格配置规范

```json
{
  "personality_key": {
    "name": "string",
    "description": "string",
    "traits": ["string"],
    "speech_style": {
      "min_length": "number",
      "max_length": "number",
      "tone": "string"
    },
    "behavior": {
      "always_truthful": "boolean",
      "aggressive_level": "number (0-1)",
      "trust_easily": "boolean"
    }
  }
}
```

---

## 五、AI 发言质量规范

### 5.1 发言内容要求

**必须包含**:
- [ ] 分析至少 1-2 个具体玩家（支持或质疑，说明理由）
- [ ] 明确立场（不模棱两可）
- [ ] 符合人格特点（话多/话少/激进/低调）

**禁止内容**:
- [ ] 纯废话（如"我是好人，大家加油"）
- [ ] 暴露真实身份（狼人不能说自己是狼）
- [ ] 自相矛盾（与之前发言冲突）

### 5.2 发言长度约束

| 人格 | 最小长度 | 最大长度 |
|------|---------|---------|
| 高冷 | 10 | 40 |
| 佛系 | 15 | 50 |
| 真诚 | 30 | 80 |
| 激进 | 30 | 100 |
| 笑面虎 | 35 | 100 |
| 爱撒谎 | 40 | 120 |
| 啰嗦 | 60 | 200 |

### 5.3 第 2 轮发言特殊要求

- [ ] 回应之前其他玩家的质疑
- [ ] 回应之前其他玩家的支持
- [ ] 根据新信息调整立场（如有人死亡、有人跳身份）

---

## 六、测试规范

### 6.1 单元测试要求

**必须测试的场景**:
1. `GameEngine.setup()` - 玩家数量边界值（6, 9, 15）
2. `AIAgent.analyze_speech()` - 信任/怀疑列表更新逻辑
3. `GameState.check_game_over()` - 各种胜负条件
4. `LLMClient.chat()` - 网络错误重试机制

### 6.2 集成测试要求

**必须测试的流程**:
1. 完整游戏流程（从开始到结束）
2. 警长竞选流程（有人当选、平票、无人参选）
3. 投票流程（有人被放逐、平票、弃票）
4. 猎人技能发动
5. 女巫用药（救人、毒人）

### 6.3 日志验证要求

**验证点**:
- [ ] 警长竞选有完整记录（候选人、发言、投票）
- [ ] 每轮发言有内心独白
- [ ] 投票有详细信息（谁投给谁）
- [ ] 夜晚行动有汇总
- [ ] 游戏结束有复盘

---

## 七、扩展规范

### 7.1 新游戏扩展

**步骤**:
1. 在 `games/` 下创建新目录（如 `games/jubensha/`）
2. 实现游戏特定规则（继承 `GameEngine` 或新建）
3. 定义角色和阶段
4. 更新配置文件
5. 添加测试用例

**约束**:
- 不能修改现有狼人杀代码
- 必须实现 UI 接口
- 必须记录日志

### 7.2 新 UI 扩展

**步骤**:
1. 继承 `UIBase` 类
2. 实现所有抽象方法
3. 在 `main.py` 中切换 UI 实例

**示例**:
```python
class WebUI(UIBase):
    def display_message(self, speaker, message):
        # WebSocket 推送消息
        pass
    # ... 实现其他方法
```

---

## 八、版本控制规范

### 8.1 Git 提交规范

**提交消息格式**:
```
<type>: <description>

[optional body]

[optional footer]
```

**type 类型**:
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构（不修复 bug 或添加功能）
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

**示例**:
```
feat: 添加警长竞选日志记录

- 记录候选人列表
- 记录竞选发言和内心独白
- 记录投票详情

Closes #12
```

### 8.2 版本发布规范

**版本号格式**: `MAJOR.MINOR.PATCH`

- `MAJOR`: 不兼容的 API 变更
- `MINOR`: 向后兼容的功能添加
- `PATCH`: 向后兼容的 bug 修复

---

## 附录 A：快速参考

### A.1 开发新功能的 SDD 流程

1. **写规范**：在本文档中添加方法规范
2. **生成代码**：让 AI 根据规范生成代码
3. **写测试**：根据规范中的约束写测试用例
4. **验证**：运行测试，确保符合规范
5. **迭代**：修改规范或代码，直到通过测试

### A.2 常见错误及避免方法

| 错误 | 原因 | 避免方法 |
|------|------|---------|
| AI 发言太短 | prompt 未明确要求 | 在规范中明确长度约束 |
| 日志不完整 | 忘记添加日志事件 | 在方法规范中列出所有日志事件 |
| 网络请求崩溃 | 未处理异常 | 在规范中要求重试机制 |
| Windows 乱码 | 使用 emoji | 在规范中禁止 emoji |

---

**文档版本**: 1.0  
**最后更新**: 2026-03-05  
**维护者**: BotBattle Team
