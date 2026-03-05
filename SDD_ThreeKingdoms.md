# BotBattle SDD 补充文档 - 三国杀扩展

**文档版本**: 1.0  
**创建日期**: 2026-03-05  
**适用范围**: 三国杀游戏模式扩展

---

## 一、三国杀核心规范

### 1.1 游戏模式对比

| 特性 | 狼人杀 | 三国杀 |
|------|--------|--------|
| **信息结构** | 完全隐藏身份 | 部分公开（武将）+ 部分隐藏（手牌、身份） |
| **游戏节奏** | 天/夜循环，集体行动 | 回合制，单人行动 + 多人响应 |
| **状态复杂度** | 存活/死亡 | 体力、手牌、装备、判定区、技能状态 |
| **交互方式** | 发言→投票 | 出牌→响应→结算 |
| **UI 需求** | 发言记录 + 投票结果 | 全局看板 + 手牌展示 + 思考过程 |

### 1.2 上帝视角需求

**信息可见性规则**:

| 信息项 | 上帝视角玩家 | 观察模式 | AI 玩家 |
|--------|-------------|---------|--------|
| 武将 | ✅ 全部可见 | ✅ 全部可见 | ✅ 全部可见 |
| 体力值 | ✅ 全部可见 | ✅ 全部可见 | ✅ 全部可见 |
| 手牌内容 | ✅ 全部可见 | ❌ 只看张数 | ⚠️ 只看自己的 |
| 手牌张数 | ✅ 全部可见 | ✅ 全部可见 | ✅ 全部可见 |
| 装备区 | ✅ 全部可见 | ✅ 全部可见 | ✅ 全部可见 |
| 判定区 | ✅ 全部可见 | ✅ 全部可见 | ✅ 全部可见 |
| 身份 | ✅ 全部可见 | ❌ 死亡后公开 | ⚠️ 只看自己的 |

**说明**:
- **上帝视角玩家**：亲自下场的玩家，可以看到所有信息（包括其他 AI 的手牌和身份）
- **观察模式**：纯观察者，身份在玩家死亡后公开
- **AI 玩家**：只知道自己的身份和手牌，其他信息通过观察获取

### 1.3 全局看板布局

**UI 布局规范**:
- 玩家布局：**线性布局**，当前回合玩家高亮
- 手牌展示：**简单模式**（只显示牌名）
- AI 思考：**可折叠/展开**，默认显示最新，可展开查看历史

---

## 二、数据结构规范

### 2.1 玩家状态

```python
@dataclass
class ThreeKingdomsPlayer:
    """三国杀玩家状态"""
    id: int
    name: str
    general: str              # 武将名
    hp: int                   # 当前体力
    max_hp: int               # 体力上限
    hand_cards: list[Card]    # 手牌列表
    equipped: Equipment       # 装备区
    judged: list[Card]        # 判定区
    role: str                 # 身份：主公/忠臣/反贼/内奸
    is_alive: bool = True
    skill_state: dict = None  # 技能状态
```

### 2.2 卡牌结构

```python
@dataclass
class Card:
    """卡牌基类"""
    name: str                 # 牌名
    suit: str                 # 花色 ♠♥♣♦
    number: int               # 点数 1-13
    card_type: str            # basic/trick/equipment

@dataclass
class BasicCard(Card):
    """基本牌"""
    subtype: str              # slash/dodge/peach/wine

@dataclass
class TrickCard(Card):
    """锦囊牌"""
    subtype: str              # 具体锦囊名
    is_delayed: bool          # 是否延时锦囊

@dataclass
class EquipmentCard(Card):
    """装备牌"""
    subtype: str              # weapon/armor/horse_minus/horse_plus
    attack_range: int = None  # 武器攻击范围
```

### 2.3 装备区结构

```python
@dataclass
class Equipment:
    """装备区"""
    weapon: Card | None = None       # 武器
    armor: Card | None = None        # 防具
    horse_minus: Card | None = None  # -1 马（进攻马）
    horse_plus: Card | None = None   # +1 马（防御马）
    
    def get_attack_range(self) -> int:
        """获取攻击范围（武器决定）"""
        if self.weapon:
            return self.weapon.attack_range
        return 1  # 默认攻击范围
```

---

## 五、游戏流程规范

### 5.1 回合流程

```
回合开始
  ↓
判定阶段 (乐不思蜀、兵粮寸断、闪电)
  ↓
摸牌阶段 (摸 2 张牌)
  ↓
出牌阶段 (无限次出牌，直到不出或不能出)
  ├→ 出杀 (限 1 次，除非有诸葛连弩)
  ├→ 出锦囊
  ├→ 装备武器/防具/马
  └→ 其他玩家响应
  ↓
弃牌阶段 (手牌数 > 体力值，则弃牌)
  ↓
回合结束
```

### 5.2 响应机制

```
玩家 A 出【杀】→ 目标 B
  ↓
B 是否需要出【闪】？
  ↓
B 的 AI 决策：
  - 评估手牌（有闪吗？）
  - 评估局势（血量健康吗？）
  - 评估关系（是敌人还是盟友？）
  - 决定是否出闪
```

### 5.3 濒死求桃流程（完整）

```
玩家 A 血量≤0 → 进入濒死状态
  ↓
逆时针询问每个存活玩家：
  - 是否使用【桃】？
  - AI 决策：评估关系、手牌、局势
  ↓
有人桃 → A 恢复 1 血 → 继续游戏
  ↓
无人桃 → A 死亡 → 亮身份 → 结算奖励
  - 杀死反贼：摸 3 张牌
  - 杀死忠臣：弃光手牌
```

### 5.4 胜负判定（简化规则）

| 身份 | 胜利条件 |
|------|---------|
| 主公 | 所有反贼和内奸死亡 |
| 忠臣 | 主公存活，所有反贼和内奸死亡 |
| 反贼 | 主公死亡 |
| 内奸 | 最后存活（包括主公） |

**游戏结束时机**: 即时判定
- 主公死亡 → 立即结束（反贼胜）
- 最后反贼/内奸死亡 → 立即结束（主忠胜）

### 5.5 牌堆管理

**规则**:
1. 使用固定牌堆（标准包所有牌）
2. 牌堆抽空时：
   - 将弃牌堆洗匀 → 形成新牌堆
   - 继续游戏
3. **不会平局**（弃牌堆循环使用）

```python
def draw_cards(player_id: int, count: int = 2) -> list[Card]:
    """
    摸牌
    
    规则:
    1. 优先从牌堆摸
    2. 牌堆为空时:
       - 将弃牌堆洗匀 → 新牌堆
       - 继续摸牌
    3. 记录日志：牌堆重置
    """
    drawn = []
    for _ in range(count):
        if len(deck) == 0:
            # 牌堆为空，重置
            if len(discard_pile) > 0:
                reset_deck()  # 弃牌堆洗入牌堆
                log_event("deck_reset", {"discard_count": len(discard_pile)})
            else:
                # 极端情况：牌堆和弃牌堆都为空
                # 理论上不会发生（至少手牌会在弃牌堆）
                break
        if len(deck) > 0:
            card = deck.pop()
            drawn.append(card)
            player.hand_cards.append(card)
    
    return drawn
```

### 3.1 类定义

```python
class ThreeKingdomsEngine:
    """
    三国杀游戏引擎
    
    继承自 GameEngine，扩展三国杀特有功能
    
    Attributes:
        deck: list[Card] - 牌堆
        discard_pile: list[Card] - 弃牌堆
        current_player_id: int - 当前回合玩家
        damage_source: int | None - 伤害来源
    """
```

### 3.2 回合流程方法

#### `run_turn(player_id: int) -> None`
- **输入**: `player_id` - 当前回合玩家 ID
- **输出**: None
- **前置条件**: 
  - 玩家存活
  - 游戏未结束
- **后置条件**: 
  - 完成完整回合流程
  - 切换到下一位玩家
- **流程**:
  1. `phase_draw()` - 摸牌阶段
  2. `phase_judge()` - 判定阶段
  3. `phase_play()` - 出牌阶段
  4. `phase_discard()` - 弃牌阶段
- **日志事件**:
  - `turn_start`
  - `phase_draw`
  - `phase_judge`
  - `phase_play`
  - `phase_discard`
  - `turn_end`

#### `phase_draw() -> list[Card]`
- **输入**: None
- **输出**: 摸到的牌列表
- **规则**: 
  - 默认摸 2 张
  - 某些武将技能可改变摸牌数
- **日志事件**: `cards_drawn`

#### `phase_judge() -> None`
- **输入**: None
- **输出**: None
- **处理**: 
  - 乐不思蜀
  - 兵粮寸断
  - 闪电
- **日志事件**: `judge_result`

#### `phase_play() -> None`
- **输入**: None
- **输出**: None
- **规则**:
  - 每回合限出 1 次【杀】（除非有诸葛连弩）
  - 可无限出锦囊
  - 可装备装备
- **约束**: 
  - 出牌必须符合规则（距离、目标等）
  - 需要处理其他玩家响应
- **日志事件**: `card_played`, `card_responded`

#### `phase_discard() -> list[Card]`
- **输入**: None
- **输出**: 弃掉的牌列表
- **规则**: 
  - 手牌数 > 体力值时，弃置多余牌
- **日志事件**: `cards_discarded`

---

### 3.3 响应机制

#### `request_response(action: dict, targets: list[int]) -> dict[int, dict]`
- **输入**:
  - `action`: dict - 行动详情（如"出杀"）
  - `targets`: list[int] - 需要响应的玩家 ID
- **输出**: `responses` - 每个玩家的响应
- **流程**:
  1. 按逆时针顺序询问每个目标玩家
  2. 每个玩家 AI 决策是否响应
  3. 收集所有响应
  4. 结算响应结果
- **日志事件**: `response_request`, `response_given`

**示例：出杀请求响应**
```python
# 玩家 A 对玩家 B 出杀
action = {
    "type": "slash",
    "source": 1,
    "target": 3,
}
# 需要 B 响应是否出闪
responses = request_response(action, targets=[3])
# 响应结果
responses = {
    3: {"respond": True, "card": "闪"}
}
```

---

## 四、AI 决策规范 - 三国杀

### 4.1 决策场景分类

| 场景 | 输入 | 输出 | 决策要点 |
|------|------|------|---------|
| **摸牌后出牌** | 手牌、局势 | 出什么牌 | 优先集火谁、保留什么牌 |
| **响应杀** | 是否有闪、血量 | 是否出闪 | 是否暴露手牌、血量健康度 |
| **响应锦囊** | 锦囊类型、局势 | 是否响应 | 如无懈可击是否使用 |
| **桃别人** | 关系、血量 | 是否桃 | 是盟友吗、值得救吗 |
| **弃牌** | 手牌价值 | 弃什么 | 保留关键牌、弃无用牌 |
| **技能发动** | 技能条件、局势 | 是否发动 | 时机是否合适 |
| **装备更换** | 新装备、当前装备 | 是否更换 | 是否提升 |
| **选将** | 3 个武将选项 | 选哪个 | 配合身份、强度 |

### 4.2 AI 思考过程记录

**记录粒度**: 完全记录所有决策，方便调试

```python
@dataclass
class AIThought:
    """AI 思考过程记录"""
    player_id: int
    timestamp: str
    phase: str              # draw/play/respond/discard/general_select
    situation: dict         # 当前局势
    options: list[str]      # 可选行动
    reasoning: str          # 推理过程
    final_decision: str     # 最终决定
    confidence: float       # 置信度 0-1
```

### 4.3 AI 记忆系统

**记忆范围**:
- **必须记忆**（始终保留）:
  - 自己出过的牌
  - 别人对自己出过的牌
  - 自己摸到的牌
  - 已死亡玩家及其身份

- **可选记忆**（可配置）:
  - 所有玩家出过的牌（记牌器）
  - 牌堆剩余牌数估算
  - 历史回合完整记录

**记忆结构**:
```python
@dataclass
class AIMemory:
    """AI 记忆"""
    my_played_cards: list[Card]       # 自己出过的牌
    cards_played_on_me: dict          # 别人对自己出的牌 {player_id: [cards]}
    my_drawn_cards: list[Card]        # 自己摸到的牌
    dead_players: list[dict]          # 已死亡玩家信息
    observed_cards: list[Card]        # 观察到的牌（可选）
    deck_estimate: int                # 牌堆估算（可选）
```

```python
@dataclass
class AIThought:
    """AI 思考过程记录"""
    player_id: int
    timestamp: str
    phase: str              # draw/play/respond/discard
    situation: dict         # 当前局势
    options: list[str]      # 可选行动
    reasoning: str          # 推理过程
    final_decision: str     # 最终决定
    confidence: float       # 置信度 0-1
```

**示例：出杀决策的思考过程**
```json
{
  "player_id": 3,
  "timestamp": "2026-03-05T20:30:15",
  "phase": "play",
  "situation": {
    "my_hp": 3,
    "my_hand": ["杀", "闪", "桃", "过河拆桥"],
    "target_player": 1,
    "target_hp": 2,
    "target_role": "反贼",
    "my_role": "主公"
  },
  "options": [
    "出杀攻击 1 号",
    "过河拆桥拆 1 号装备",
    "保留手牌防御"
  ],
  "reasoning": "1 号是反贼，血量只有 2，我手上有杀，应该优先集火。如果这轮能杀死反贼，可以摸 3 张牌，建立优势。手上还有闪和桃，防御足够。",
  "final_decision": "出杀攻击 1 号",
  "confidence": 0.85
}
```

---

## 五、UI 规范 - 全局看板

### 5.1 UI 接口扩展

```python
class ThreeKingdomsUI(UIBase):
    """三国杀 UI 接口"""
    
    @abstractmethod
    def update_game_board(self, players: list[PlayerState], 
                          deck_count: int, discard_count: int) -> None:
        """更新全局看板"""
        pass
    
    @abstractmethod
    def show_player_details(self, player_id: int, 
                           details: PlayerDetails) -> None:
        """显示玩家详情（手牌、装备等）"""
        pass
    
    @abstractmethod
    def show_ai_thought(self, thought: AIThought) -> None:
        """显示 AI 思考过程"""
        pass
    
    @abstractmethod
    def show_card_played(self, player_id: int, card: Card) -> None:
        """显示玩家出牌"""
        pass
    
    @abstractmethod
    def show_damage_result(self, source: int, target: int, 
                          damage: int, remaining_hp: int) -> None:
        """显示伤害结算"""
        pass
```

### 5.2 全局看板布局规范

```
┌─────────────────────────────────────────────────────────────┐
│  【游戏状态】回合：3 号 (关羽)  |  牌堆：45  |  弃牌：18  |  存活：5  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                    ┌─────────────┐         │
│  │ 1 号 - 曹操  │                    │ 2 号 - 刘备  │         │
│  │ [内奸]     │                    │ [忠臣]     │         │
│  │ HP: ●●○○○  │                    │ HP: ●●●○○  │         │
│  │ 手牌：5 张   │                    │ 手牌：4 张   │         │
│  │ [杀闪桃酒拆]│                    │ [杀闪闪桃]  │         │
│  │ 装备：青龙刀 │                    │ 装备：无     │         │
│  │ 判定：无     │                    │ 判定：乐不思蜀│        │
│  └─────────────┘                    └─────────────┘         │
│                                                              │
│              ┌─────────────────────────┐                     │
│              │   3 号 - 关羽 [主公]    │  ← 当前回合          │
│              │   HP: ●●●●○ (3/4)      │                     │
│              │   手牌：[杀] [闪] [桃] [酒]  │                  │
│              │   装备：方天画戟 八卦阵   │                  │
│              │   判定：无              │                     │
│              │   技能：未出杀          │                     │
│              └─────────────────────────┘                     │
│                                                              │
│  ┌─────────────┐                    ┌─────────────┐         │
│  │ 4 号 - 司马懿 │                    │ 5 号 - 华佗  │         │
│  │ [反贼]     │                    │ [反贼]     │         │
│  │ HP: ●●●○○  │                    │ HP: ●●○○○  │         │
│  │ 手牌：3 张   │                    │ 手牌：4 张   │         │
│  │ [...]      │                    │ [...]      │         │
│  │ 装备：...   │                    │ 装备：...   │         │
│  │ 判定：...   │                    │ 判定：...   │         │
│  └─────────────┘                    └─────────────┘         │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  【AI 思考过程】                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ [3 号 - 关羽] 20:30:15                                │  │
│  │ 当前阶段：出牌阶段                                    │  │
│  │ 手牌分析：有杀可以进攻，有闪桃防御足够                │  │
│  │ 局势判断：1 号反贼血量低，应该优先集火                │  │
│  │ 决策：出杀攻击 1 号，争取打死摸牌                      │  │
│  │ 置信度：85%                                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  [历史思考记录...（可滚动查看）]                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 六、日志规范 - 三国杀扩展

### 6.1 新增事件类型

| 事件类型 | 触发时机 | 必要字段 |
|---------|---------|---------|
| `game_setup_3k` | 三国杀游戏初始化 | `player_count`, `generals`, `roles` |
| `turn_start` | 回合开始 | `player_id`, `general`, `hp` |
| `phase_draw` | 摸牌阶段 | `player_id`, `drawn_cards` |
| `phase_judge` | 判定阶段 | `player_id`, `judge_card`, `result` |
| `card_played` | 出牌 | `player_id`, `card`, `target` |
| `card_responded` | 响应 | `player_id`, `response_card`, `success` |
| `damage_dealt` | 伤害 | `source`, `target`, `damage`, `remaining_hp` |
| `player_died` | 玩家死亡 | `player_id`, `killer`, `role_reveal` |
| `phase_discard` | 弃牌阶段 | `player_id`, `discarded_cards` |
| `turn_end` | 回合结束 | `player_id` |
| `ai_thought` | AI 思考 | `player_id`, `phase`, `reasoning`, `decision` |

### 6.2 日志示例

```json
{
  "type": "card_played",
  "data": {
    "player_id": 3,
    "card": {"name": "杀", "suit": "♠", "number": 8},
    "target": 1,
    "timestamp": "2026-03-05T20:30:15"
  }
}
```

```json
{
  "type": "ai_thought",
  "data": {
    "player_id": 3,
    "phase": "play",
    "situation": {
      "my_hp": 3,
      "my_hand": ["杀", "闪", "桃"],
      "target": 1,
      "target_hp": 2
    },
    "reasoning": "1 号反贼血量低，应该优先集火",
    "final_decision": "出杀攻击 1 号",
    "confidence": 0.85
  }
}
```

---

## 七、配置规范 - 三国杀扩展

### 7.1 游戏配置

```json
{
  "name": "三国杀标准局",
  "player_count": 5,
  "mode": "3k",
  "roles": [
    {"role": "主公", "count": 1},
    {"role": "忠臣", "count": 1},
    {"role": "反贼", "count": 2},
    {"role": "内奸", "count": 1}
  ],
  "general_select_mode": "random_3_pick_1",
  "identity_reveal_on_death": true,
  "game_rules": {
    "initial_hand": 4,
    "draw_count": 2,
    "has_equipment": true,
    "has_delayed_trick": true,
    "distance_calculation": "full",
    "dying_request_peach": true,
    "victory_condition": "simplified"
  }
}
```

**配置项说明**:
- `general_select_mode`: 武将选择方式
  - `"random_3_pick_1"`: 每人随机 3 个选 1 个
  - `"fixed"`: 固定武将
- `identity_reveal_on_death`: 死亡时是否公开身份
- `distance_calculation`: 距离计算规则
  - `"full"`: 完整规则
  - `"simplified"`: 简化规则
- `dying_request_peach`: 是否启用濒死求桃流程
- `victory_condition`: 胜负判定规则
  - `"simplified"`: 简化规则

### 7.2 武将技能配置

```json
{
  "关羽": {
    "faction": "shu",
    "hp": 4,
    "skills": [
      {
        "name": "武圣",
        "description": "可以将红色牌当杀使用",
        "trigger": "play",
        "frequency": "unlimited"
      }
    ]
  },
  "曹操": {
    "faction": "wei",
    "hp": 4,
    "skills": [
      {
        "name": "奸雄",
        "description": "受到伤害后，可以获得造成伤害的牌",
        "trigger": "damage_received",
        "frequency": "once_per_turn"
      }
    ]
  }
}
```

---

## 八、测试规范 - 三国杀扩展

### 8.1 单元测试要求

**必须测试的场景**:
1. 摸牌阶段：摸 2 张牌
2. 出杀响应：有闪是否出闪
3. 乐不思蜀判定：是否跳过出牌阶段
4. 装备区逻辑：武器替换、马的效果
5. 伤害结算：体力流失、死亡判定

### 8.2 集成测试要求

**必须测试的流程**:
1. 完整回合流程（摸牌→出牌→弃牌）
2. 多人响应（南蛮入侵、万箭齐发）
3. 延时锦囊结算
4. 身份胜负判定

---

## 九、开发优先级

### Phase 1 - 核心框架
- [ ] ThreeKingdomsEngine 基础类
- [ ] 卡牌数据结构
- [ ] 玩家状态管理
- [ ] 基础出牌流程

### Phase 2 - 响应机制
- [ ] 杀闪响应
- [ ] 锦囊响应
- [ ] AI 决策基础

### Phase 3 - UI 看板
- [ ] 全局看板 CLI 实现
- [ ] AI 思考过程展示
- [ ] 日志记录

### Phase 4 - 完整功能
- [ ] 所有武将技能
- [ ] 所有卡牌效果
- [ ] 完整胜负判定

---

**附录**:
- [三国杀规则详解](https://www.sanguosha.com/rules)
- [武将技能大全](https://wiki.sanguosha.com/)
- [卡牌列表](https://wiki.sanguosha.com/cards)
