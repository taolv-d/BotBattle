"""
游戏复盘服务

通用模块，支持多种游戏的复盘分析和漏洞检测
"""
import json
import os
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
import logging

from .llm_service import LLMService
from .logger_service import LoggerService


logger = logging.getLogger(__name__)


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
    output_dir: str = "reviews"   # 报告输出目录


@dataclass
class ReviewReport:
    """复盘报告"""
    game_id: str
    game_type: str
    winner: str
    reason: str
    duration: str = ""
    key_events: List[Dict] = field(default_factory=list)
    player_analysis: Optional[Dict] = None
    loopholes: Optional[List[Dict]] = None  # 逻辑漏洞
    highlights: Optional[List[str]] = None  # 精彩时刻
    summary: str = ""
    raw_report: str = ""  # LLM 原始输出
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)

    def to_markdown(self) -> str:
        """转换为 Markdown 格式"""
        md = f"# 游戏复盘报告\n\n"
        md += f"**游戏 ID**: {self.game_id}\n"
        md += f"**游戏类型**: {self.game_type}\n"
        md += f"**获胜方**: {self.winner}\n"
        md += f"**胜利原因**: {self.reason}\n"
        if self.duration:
            md += f"**游戏时长**: {self.duration}\n"
        md += f"**生成时间**: {self.created_at}\n\n"

        if self.summary:
            md += f"---\n\n## 总结\n\n{self.summary}\n\n"

        if self.key_events:
            md += f"---\n\n## 关键事件\n\n"
            for i, event in enumerate(self.key_events, 1):
                md += f"{i}. {event.get('event', event)}\n"
            md += "\n"

        if self.highlights:
            md += f"---\n\n## 精彩时刻\n\n"
            for highlight in self.highlights:
                md += f"> {highlight}\n\n"

        if self.loopholes:
            md += f"---\n\n## 逻辑漏洞检测\n\n"
            md += f"共发现 {len(self.loopholes)} 个漏洞\n\n"
            for i, loophole in enumerate(self.loopholes, 1):
                md += f"### 漏洞 {i}\n\n"
                md += f"- **类型**: {loophole.get('type', '未知')}\n"
                md += f"- **涉及玩家**: {loophole.get('player', '未知')}\n"
                md += f"- **内容**: {loophole.get('content', '')}\n"
                md += f"- **分析**: {loophole.get('analysis', '')}\n"
                md += f"- **严重程度**: {loophole.get('severity', '未知')}\n\n"

        if self.raw_report and self.raw_report != self.summary:
            md += f"---\n\n## 详细分析\n\n{self.raw_report}\n"

        return md


class GameReviewService:
    """游戏复盘服务"""

    # 复盘报告 Prompt 模板
    REVIEW_PROMPT_TEMPLATE = """你是一位专业的游戏复盘分析师。请根据以下游戏日志，生成一份复盘报告。

## 游戏信息
- 游戏类型：{game_type}
- 游戏 ID: {game_id}
- 获胜方：{winner}
- 胜利原因：{reason}
- 游戏天数：{day_number}天

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

{highlights_section}

### 4. 总结
- 整体评价
- 改进建议

请用中文回答，保持专业但易懂的风格。
"""

    # 漏洞检测 Prompt 模板
    LOOPHOLE_PROMPT_TEMPLATE = """你是一位专业的游戏逻辑审查员。请分析以下游戏对话，检测是否存在逻辑漏洞。

## 游戏类型
{game_type}

## 游戏信息
- 游戏 ID: {game_id}
- 获胜方：{winner}

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
"""

    def __init__(self, config: ReviewConfig = None, llm_service: LLMService = None):
        """
        初始化游戏复盘服务

        Args:
            config: 复盘配置
            llm_service: LLM 服务实例
        """
        self.config = config or ReviewConfig()
        self.llm_service = llm_service
        self.logger = logging.getLogger(__name__)

        # 创建输出目录
        os.makedirs(self.config.output_dir, exist_ok=True)

    def set_llm_service(self, llm_service: LLMService):
        """设置 LLM 服务"""
        self.llm_service = llm_service

    def _format_log_entries(self, log_entries: List[Dict], max_entries: int = 500) -> str:
        """
        格式化日志条目为文本

        Args:
            log_entries: 日志条目列表
            max_entries: 最大条目数

        Returns:
            格式化后的日志文本
        """
        if not log_entries:
            return "无日志记录"

        # 限制条目数
        entries = log_entries[-max_entries:] if len(log_entries) > max_entries else log_entries

        formatted = []
        for entry in entries:
            timestamp = entry.get("timestamp", "")
            event_type = entry.get("event_type", "")
            data = entry.get("data", {})

            # 只记录关键事件
            if event_type in ["speak", "night_action", "vote", "death", "game_over"]:
                formatted.append(f"[{timestamp}] {event_type}: {data}")

        return "\n".join(formatted) if formatted else "无关键事件记录"

    async def generate_review(
        self,
        game_id: str,
        game_type: str,
        log_entries: List[Dict],
        game_result: Dict[str, Any]
    ) -> ReviewReport:
        """
        生成复盘报告

        Args:
            game_id: 游戏 ID
            game_type: 游戏类型（werewolf/threekingdoms）
            log_entries: 日志条目列表
            game_result: 游戏结果字典，包含 winner, reason, day_number 等

        Returns:
            ReviewReport: 复盘报告
        """
        if not self.config.enabled:
            self.logger.info("复盘功能未启用，跳过报告生成")
            return None

        if not self.llm_service:
            self.logger.warning("LLM 服务未配置，使用默认报告")
            return self._generate_default_report(game_id, game_type, game_result)

        try:
            # 格式化日志
            log_content = self._format_log_entries(
                log_entries,
                self.config.max_log_entries
            )

            # 构建 Prompt
            highlights_section = ""
            if self.config.highlight_moments:
                highlights_section = "### 4. 精彩时刻\n- 摘录 2-3 个精彩发言\n"

            prompt = self.REVIEW_PROMPT_TEMPLATE.format(
                game_type=game_type,
                game_id=game_id,
                winner=game_result.get("winner", "未知"),
                reason=game_result.get("reason", "未知"),
                day_number=game_result.get("day_number", 0),
                log_content=log_content,
                highlights_section=highlights_section
            )

            # 调用 LLM
            self.logger.info(f"正在生成复盘报告（游戏 ID: {game_id}）...")
            raw_report = await self.llm_service.generate_response(prompt)

            # 创建报告对象
            report = ReviewReport(
                game_id=game_id,
                game_type=game_type,
                winner=game_result.get("winner", "未知"),
                reason=game_result.get("reason", "未知"),
                raw_report=raw_report,
                summary=raw_report[:500] + "..." if len(raw_report) > 500 else raw_report
            )

            # 如果启用漏洞检测，额外调用
            if self.config.detect_loopholes:
                loopholes = await self.detect_loopholes(game_type, log_entries, game_result)
                report.loopholes = loopholes

            # 保存报告
            self._save_report(report)

            self.logger.info(f"复盘报告已生成：{self._get_report_filename(game_id)}")
            return report

        except Exception as e:
            self.logger.error(f"生成复盘报告失败：{e}")
            return self._generate_default_report(game_id, game_type, game_result)

    async def detect_loopholes(
        self,
        game_type: str,
        log_entries: List[Dict],
        game_result: Dict[str, Any] = None
    ) -> List[Dict]:
        """
        检测对话中的逻辑漏洞

        Args:
            game_type: 游戏类型
            log_entries: 日志条目列表
            game_result: 游戏结果（可选）

        Returns:
            list[dict]: 漏洞列表
        """
        if not self.llm_service:
            self.logger.warning("LLM 服务未配置，无法检测漏洞")
            return []

        try:
            # 格式化日志（只保留对话相关）
            dialogue_entries = [
                e for e in log_entries
                if e.get("event_type") in ["speak", "pk_speech", "president_speech"]
            ]
            log_content = self._format_log_entries(dialogue_entries, self.config.max_log_entries)

            # 构建 Prompt
            prompt = self.LOOPHOLE_PROMPT_TEMPLATE.format(
                game_type=game_type,
                game_id=game_result.get("game_id", "unknown") if game_result else "unknown",
                winner=game_result.get("winner", "未知") if game_result else "未知",
                log_content=log_content
            )

            # 调用 LLM
            self.logger.info("正在检测逻辑漏洞...")
            raw_result = await self.llm_service.generate_response(prompt)

            # 解析结果（简单解析，实际可能需要更复杂的解析逻辑）
            loopholes = self._parse_loophole_result(raw_result)

            self.logger.info(f"检测到 {len(loopholes)} 个逻辑漏洞")
            return loopholes

        except Exception as e:
            self.logger.error(f"检测逻辑漏洞失败：{e}")
            return []

    def _parse_loophole_result(self, raw_result: str) -> List[Dict]:
        """
        解析漏洞检测结果

        Args:
            raw_result: LLM 原始输出

        Returns:
            漏洞列表
        """
        loopholes = []

        # 简单解析：按行分割，查找漏洞标记
        lines = raw_result.split("\n")
        current_loophole = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_loophole:
                    loopholes.append(current_loophole)
                    current_loophole = {}
                continue

            # 解析漏洞字段
            if "漏洞类型" in line or "【漏洞类型】" in line:
                current_loophole["type"] = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif "涉及玩家" in line:
                current_loophole["player"] = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif "具体内容" in line:
                current_loophole["content"] = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif "问题分析" in line or "分析" in line:
                current_loophole["analysis"] = line.split(":", 1)[-1].strip() if ":" in line else ""
            elif "严重程度" in line:
                current_loophole["severity"] = line.split(":", 1)[-1].strip() if ":" in line else ""

        if current_loophole:
            loopholes.append(current_loophole)

        return loopholes

    def _generate_default_report(
        self,
        game_id: str,
        game_type: str,
        game_result: Dict[str, Any]
    ) -> ReviewReport:
        """生成默认报告（LLM 不可用时）"""
        return ReviewReport(
            game_id=game_id,
            game_type=game_type,
            winner=game_result.get("winner", "未知"),
            reason=game_result.get("reason", "未知"),
            summary=f"游戏已结束，获胜方为{game_result.get('winner', '未知')}，胜利原因是{game_result.get('reason', '未知')}。",
            raw_report="LLM 服务不可用，无法生成详细报告。"
        )

    def _save_report(self, report: ReviewReport):
        """保存报告到文件"""
        # Markdown 格式
        md_filename = self._get_report_filename(report.game_id, ".md")
        md_path = os.path.join(self.config.output_dir, md_filename)

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(report.to_markdown())

        # JSON 格式
        json_filename = self._get_report_filename(report.game_id, ".json")
        json_path = os.path.join(self.config.output_dir, json_filename)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, ensure_ascii=False, indent=2)

        self.logger.info(f"报告已保存：{md_path}, {json_path}")

    def _get_report_filename(self, game_id: str, extension: str = ".md") -> str:
        """生成报告文件名"""
        return f"review_{game_id}{extension}"

    def load_report(self, game_id: str) -> Optional[ReviewReport]:
        """加载已保存的报告"""
        json_filename = self._get_report_filename(game_id, ".json")
        json_path = os.path.join(self.config.output_dir, json_filename)

        if not os.path.exists(json_path):
            return None

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ReviewReport(**data)


# 便捷函数
def create_review_service(
    enabled: bool = True,
    mode: str = "detailed",
    detect_loopholes: bool = False,
    llm_service: LLMService = None
) -> GameReviewService:
    """
    创建复盘服务实例

    Args:
        enabled: 是否启用
        mode: 模式（summary/detailed/analysis）
        detect_loopholes: 是否检测漏洞
        llm_service: LLM 服务实例

    Returns:
        GameReviewService 实例
    """
    config = ReviewConfig(
        enabled=enabled,
        mode=ReviewMode(mode),
        detect_loopholes=detect_loopholes
    )

    service = GameReviewService(config=config)
    if llm_service:
        service.set_llm_service(llm_service)

    return service
