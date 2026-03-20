# 游戏复盘服务设计文档

**版本**: v1.0
**日期**: 2026-03-20
**状态**: 待实现

---

## 一、设计目标

### 1.1 核心目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| 通用性 | 可作为 common 模块，被狼人杀、三国杀等游戏复用 | P0 |
| 双模式 | 复盘模式（生成报告）+ 分析模式（检测漏洞） | P0 |
| 可配置 | 支持配置启用、LLM 选择、报告详细程度 | P1 |
| 异步处理 | 不阻塞游戏主流程 | P1 |

### 1.2 使用场景

1. **游戏复盘**：游戏结束后自动生成总结报告
2. **测试分析**：检测对话中的逻辑漏洞
3. **质量评估**：评估 AI 玩家的推理能力

---

## 二、架构设计

### 2.1 模块结构

```
services/
└── game_review_service.py    # 通用游戏复盘服务
```

### 2.2 类设计

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ReviewMode(Enum):
    """复盘模式"""
    SUMMARY = "summary"           # 简要总结
    DETAILED = "detailed"         # 详细报告
    ANALYSIS = "analysis"         # 深度分析（含漏洞检测）


@dataclass
class ReviewConfig:
    """复盘配置"""
    enabled: bool = True
    mode: ReviewMode = ReviewMode.DETAILED
    llm_model: str = "deepseek"   # 使用的 LLM 模型
    detect_loopholes: bool = False  # 是否检测逻辑漏洞
    highlight_moments: bool = True  # 是否摘录精彩时刻
    max_log_entries: int = 500    # 最大日志条数


@dataclass
class ReviewReport:
    """复盘报告"""
    game_id: str
    game_type: str
    winner: str
    reason: str
    duration: str
    key_events: list[dict]
    player_analysis: Optional[dict]
    loopholes: Optional[list[dict]]  # 逻辑漏洞
    highlights: Optional[list[str]]  # 精彩时刻
    summary: str
    raw_report: str  # LLM 原始输出


class GameReviewService:
    """游戏复盘服务"""

    def __init__(self, config: ReviewConfig = None):
        self.config = config or ReviewConfig()
        self.llm_service = None  # 注入 LLM 服务

    async def generate_review(
        self,
        game_id: str,
        game_type: str,
        log_entries: list[dict],
        game_result: dict
    ) -> ReviewReport:
        """
        生成复盘报告

        参数:
            game_id: 游戏 ID
            game_type: 游戏类型（werewolf/threekingdoms）
            log_entries: 日志条目列表
            game_result: 游戏结果

        返回:
            ReviewReport: 复盘报告
        """
        pass

    async def detect_loopholes(
        self,
        game_type: str,
        log_entries: list[dict]
    ) -> list[dict]:
        """
        检测对话中的逻辑漏洞

        参数:
            game_type: 游戏类型
            log_entries: 日志条目

        返回:
            list[dict]: 漏洞列表
        """
        pass
```

---

## 三、Prompt 设计

### 3.1 复盘报告 Prompt

```
你是一位专业的游戏复盘分析师。请根据以下游戏日志，生成一份复盘报告。

## 游戏信息
- 游戏类型：{game_type}
- 游戏 ID: {game_id}
- 获胜方：{winner}
- 胜利原因：{reason}

## 游戏日志
{log_content}

## 报告要求
请按照以下结构生成报告：

### 1. 游戏概览
- 简述游戏过程
- 关键转折点

### 2. 关键事件时间线
- 列出 5-10 个关键事件

### 3. 玩家表现分析
- 表现突出的玩家
- 关键决策分析

### 4. 精彩时刻
- 摘录 2-3 个精彩发言

### 5. 总结
- 整体评价
- 改进建议

请用中文回答，保持专业但易懂的风格。
```

### 3.2 漏洞检测 Prompt

```
你是一位专业的游戏逻辑审查员。请分析以下游戏对话，检测是否存在逻辑漏洞。

## 游戏类型
{game_type}

## 对话日志
{log_content}

## 审查重点
1. 身份矛盾：玩家发言与已知身份不符
2. 信息泄露：玩家透露了不应知道的信息
3. 逻辑矛盾：同一玩家前后发言矛盾
4. 技能滥用：技能使用不符合规则
5. 时间线错误：事件顺序不合理

## 输出格式
对于每个发现的漏洞，请按以下格式输出：
- 【漏洞类型】: <类型>
- 涉及玩家：<玩家 ID>
- 具体内容：<引用相关发言>
- 问题分析：<说明为什么是漏洞>
- 严重程度：<轻微/中等/严重>

如果没有发现明显漏洞，请说明"未发现明显逻辑漏洞"。

请用中文回答。
```

---

## 四、集成方式

### 4.1 狼人杀游戏集成

```python
# games/werewolf/orchestrator.py

class WerewolfOrchestrator:
    def __init__(self, config: GameConfig):
        self.review_service = GameReviewService()
        # ... 其他初始化

    async def run_game(self):
        """运行游戏"""
        try:
            # ... 游戏主流程
            await self._game_loop()
        finally:
            # 游戏结束，生成复盘报告
            await self._generate_review()

    async def _generate_review(self):
        """生成复盘报告"""
        if not self.review_service.config.enabled:
            return

        # 获取游戏日志
        log_entries = self.logger.get_recent_entries(
            limit=self.review_service.config.max_log_entries
        )

        # 生成报告
        report = await self.review_service.generate_review(
            game_id=self.state.game_id,
            game_type="werewolf",
            log_entries=log_entries,
            game_result={
                "winner": self.state.winner,
                "reason": self.state.reason,
                "day_number": self.state.day_number
            }
        )

        # 保存报告
        self._save_review_report(report)

        # 如果检测到漏洞，记录警告
        if report.loopholes:
            self.logger.warning(f"检测到 {len(report.loopholes)} 个逻辑漏洞")
```

### 4.2 测试分析集成

```python
# tests/test_game_review.py

async def test_loophole_detection():
    """测试漏洞检测功能"""
    service = GameReviewService(ReviewConfig(
        mode=ReviewMode.ANALYSIS,
        detect_loopholes=True
    ))

    # 加载测试日志
    log_entries = load_test_log("werewolf_test_001.json")

    # 检测漏洞
    loopholes = await service.detect_loopholes(
        game_type="werewolf",
        log_entries=log_entries
    )

    # 验证
    assert len(loopholes) > 0, "应该检测到漏洞"
    print(f"检测到 {len(loopholes)} 个漏洞:")
    for l in loopholes:
        print(f"  - {l['type']}: {l['description']}")
```

---

## 五、输出示例

### 5.1 复盘报告示例

```markdown
# 狼人杀游戏复盘报告

**游戏 ID**: 20260320_153344
**游戏类型**: 狼人杀（标准 9 人局）
**获胜方**: 好人阵营
**胜利原因**: 狼人全灭
**游戏时长**: 28 分钟

---

## 一、游戏概览

本局游戏为标准的 9 人局，配置为 3 狼、3 村民、3 神职（预言家、女巫、猎人）。
游戏进入第 5 天结束，好人阵营通过逻辑推理成功找出所有狼人。

关键转折点：第 3 天预言家查验出 7 号狼人身份，随后好人阵营集中投票放逐。

---

## 二、关键事件时间线

| 时间 | 事件 | 影响 |
|------|------|------|
| 第 1 夜 | 狼人刀 3 号，女巫救 | 平安夜 |
| 第 1 天 | 5 号当选警长 | 好人掌握主动权 |
| 第 2 夜 | 狼人刀 2 号，预言家验 7 号=狼 | 关键信息 |
| 第 2 天 | 投票放逐 7 号 | 狼人减员 |
| 第 3 夜 | 狼人刀 5 号（警长） | 警徽流失 |
| 第 3 天 | 投票放逐 1 号 | 狼人再减员 |
| 第 4 夜 | 狼人刀 9 号（女巫） | 女巫出局 |
| 第 5 天 | 投票放逐 4 号 | 狼人全灭，游戏结束 |

---

## 三、玩家表现分析

### 表现突出

**5 号（预言家）**：
- 成功查验 3 个玩家，准确找出 2 个狼人
- 警长竞选发言清晰，获得好人信任
- 临终指定 8 号为警长继承者

**8 号（猎人）**：
- 隐藏身份成功，狼人未察觉
- 被毒杀后开枪带走 6 号（确认狼人）

### 关键决策

- 第 2 天 5 号跳明预言家身份，获得好人信任
- 第 3 天 8 号猎人关键时刻表明身份

---

## 四、精彩时刻

> **5 号**："我是预言家，昨晚验了 7 号，查杀！今天全票出 7，不出 7 我吃毒。"

> **8 号**："我是猎人，今天走我了我就带 6 号。6 号发言一直划水，还跟着狼人冲票。"

---

## 五、总结

本局游戏好人阵营表现优异，预言家开局拿到警徽后，通过准确的查验和清晰的发言，
带领好人逐步找出狼人。女巫用药果断，猎人隐藏到位。狼人阵营未能有效伪装，
第 2 天即被找出，最终落败。

**改进建议**：
- 狼人阵营应更好地隐藏身份，避免过早暴露
- 村民玩家应更积极参与推理
```

### 5.2 漏洞检测报告示例

```markdown
# 逻辑漏洞检测报告

**游戏 ID**: 20260320_153344
**检测模式**: 深度分析
**发现漏洞**: 2 个

---

## 漏洞 1

- **漏洞类型**: 信息泄露
- **涉及玩家**: 3 号
- **具体内容**: "昨晚 7 号是狼人，我是预言家验的"
- **问题分析**: 3 号声称自己是预言家，但实际身份是村民。
  且预言家查验结果只有预言家自己知道，3 号不应该知道 7 号是狼人。
  这可能是 AI 产生了身份混淆。
- **严重程度**: 严重

## 漏洞 2

- **漏洞类型**: 逻辑矛盾
- **涉及玩家**: 6 号
- **具体内容**: 
  - 第 1 天："我是好人，一直跟着警长投票"
  - 第 2 天："我不相信警长，警长可能是狼人"
- **问题分析**: 6 号前后发言矛盾，没有合理解释为何改变立场。
  这可能是狼人阵营试图混淆视听，但逻辑不够严密。
- **严重程度**: 中等

---

## 总结

检测到 2 个逻辑漏洞，其中 1 个严重，1 个中等。
建议检查 AI 的身份认知模块和发言一致性验证。
```

---

## 六、实现计划

### 6.1 任务分解

| 任务 | 预计工时 | 优先级 |
|------|----------|--------|
| 实现 GameReviewService 基础框架 | 2h | P0 |
| 实现复盘报告生成 | 3h | P0 |
| 实现漏洞检测功能 | 4h | P1 |
| 集成到狼人杀游戏 | 2h | P0 |
| 编写测试用例 | 2h | P1 |
| 编写文档 | 1h | P2 |

### 6.2 依赖项

- `services/llm_service.py`: LLM 调用
- `services/logger_service.py`: 日志获取
- `games/werewolf/orchestrator.py`: 游戏集成

---

## 七、配置示例

```json
{
  "review": {
    "enabled": true,
    "mode": "detailed",
    "llm_model": "deepseek",
    "detect_loopholes": false,
    "highlight_moments": true,
    "max_log_entries": 500,
    "output_dir": "reviews"
  }
}
```

---

## 八、注意事项

1. **性能考虑**：复盘报告生成可能耗时较长，建议使用异步处理
2. **日志格式**：确保日志包含足够信息（时间戳、玩家 ID、事件类型、内容）
3. **隐私保护**：复盘报告不包含敏感信息
4. **可关闭性**：生产环境应支持关闭复盘功能

---

**文档版本**: v1.0
**最后更新**: 2026-03-20
