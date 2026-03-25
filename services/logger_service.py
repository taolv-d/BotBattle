import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Dict
from collections import deque


class LoggerService:
    """
    日志服务类

    提供结构化日志记录功能，支持日志轮转
    每次运行生成独立的日志文件（使用时间戳区分）
    """

    def __init__(self, log_dir: str = "logs", log_level: int = logging.INFO, game_id: Optional[str] = None,
                 max_memory_entries: int = 1000):
        """
        初始化日志服务

        Args:
            log_dir: 日志目录路径
            log_level: 日志级别
            game_id: 游戏 ID（可选），用于日志文件名。如果不提供，将使用时间戳
            max_memory_entries: 内存中保留的最大日志条目数（用于复盘）
        """
        self.log_dir = log_dir
        self.log_level = log_level
        self.logger = None
        self.game_id = game_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._memory_log = deque(maxlen=max_memory_entries)  # 内存日志缓存
        self._setup_logger()

    def _setup_logger(self):
        """设置日志记录器"""
        # 创建日志目录
        os.makedirs(self.log_dir, exist_ok=True)

        # 创建 logger
        self.logger = logging.getLogger("werewolf_game")
        self.logger.setLevel(self.log_level)

        # 清除已有的处理器，并显式关闭文件句柄
        for handler in list(self.logger.handlers):
            try:
                handler.close()
            finally:
                self.logger.removeHandler(handler)

        # 创建格式器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 创建文件处理器（带轮转）- 每次运行生成独立文件
        # 文件名格式：werewolf_game_YYYYMMDD_HHMMSS.log
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"werewolf_game_{timestamp}.log"
        log_file = os.path.join(self.log_dir, log_filename)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=10,  # 保留 10 个历史日志文件
            encoding='utf-8'  # 指定 UTF-8 编码以支持中文
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 记录日志文件信息
        self.logger.info(f"日志文件：{log_file}")

    def close(self):
        """关闭所有日志处理器，释放文件句柄。"""
        if not self.logger:
            return

        for handler in list(self.logger.handlers):
            try:
                handler.close()
            finally:
                self.logger.removeHandler(handler)

    def info(self, message: str):
        """记录信息日志"""
        self.logger.info(message)

    def warning(self, message: str):
        """记录警告日志"""
        self.logger.warning(message)

    def error(self, message: str):
        """记录错误日志"""
        self.logger.error(message)

    def debug(self, message: str):
        """记录调试日志"""
        self.logger.debug(message)

    def log_event(self, event_type: str, data: dict):
        """
        记录游戏事件

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        event_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self._memory_log.append(event_data)  # 添加到内存缓存
        self.logger.info(f"GAME_EVENT: {event_data}")

    def get_recent_entries(self, limit: int = 500) -> List[Dict]:
        """
        获取最近的日志条目

        Args:
            limit: 最大返回条目数

        Returns:
            日志条目列表
        """
        entries = list(self._memory_log)
        if len(entries) > limit:
            entries = entries[-limit:]
        return entries

    def log_agent_interaction(self, agent_id: str, prompt: str, response: str, context: Optional[dict] = None):
        """
        记录 Agent 交互详情

        Args:
            agent_id: Agent ID
            prompt: 发送给 Agent 的提示词
            response: Agent 的回复
            context: 上下文信息（可选）
        """
        interaction_data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": agent_id,
            "interaction_type": "agent_interaction",
            "prompt": prompt,
            "response": response,
            "context": context or {}
        }
        self._memory_log.append(interaction_data)  # 添加到内存缓存
        self.logger.info(f"AGENT_INTERACTION: {interaction_data}")

    def log_game_state(self, state_info: dict):
        """
        记录游戏状态

        Args:
            state_info: 游戏状态信息
        """
        state_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "game_state_snapshot",
            "state": state_info
        }
        self._memory_log.append(state_data)  # 添加到内存缓存
        self.logger.info(f"GAME_STATE: {state_data}")

    def log_night_actions(self, actions: dict):
        """
        记录夜晚行动

        Args:
            actions: 夜晚行动字典
        """
        night_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "night_actions",
            "actions": actions
        }
        self._memory_log.append(night_data)  # 添加到内存缓存
        self.logger.info(f"NIGHT_ACTIONS: {night_data}")

    def log_night_action(self, player_id: int, action: str, target: Optional[int] = None):
        """
        记录夜晚行动

        Args:
            player_id: 玩家 ID
            action: 行动类型
            target: 目标玩家 ID
        """
        data = {
            "player_id": player_id,
            "action": action,
            "target": target
        }
        self._memory_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "night_action",
            "data": data
        })  # 添加到内存缓存
        self.log_event("night_action", data)

    def log_vote(self, voter_id: int, target_id: int):
        """
        记录投票行为

        Args:
            voter_id: 投票者 ID
            target_id: 被投票者 ID
        """
        data = {
            "voter_id": voter_id,
            "target_id": target_id
        }
        self._memory_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "vote",
            "data": data
        })  # 添加到内存缓存
        self.log_event("vote", data)

    def log_result(self, result: str, details: dict):
        """
        记录游戏结果

        Args:
            result: 结果描述
            details: 详细信息
        """
        data = {
            "result": result,
            "details": details
        }
        self._memory_log.append({
            "timestamp": datetime.now().isoformat(),
            "event_type": "game_result",
            "data": data
        })  # 添加到内存缓存
        self.log_event("game_result", data)

    def log_day_phases(self, phase: str, details: dict):
        """
        记录白天阶段详情

        Args:
            phase: 阶段名称
            details: 详情
        """
        phase_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": f"day_{phase}",
            "details": details
        }
        self.logger.info(f"DAY_PHASE: {phase_data}")
