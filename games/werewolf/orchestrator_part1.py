import asyncio
import random
from typing import Dict, Any, List, Optional
from .config import GameConfig, Role, DeathCause
from .state import GameState, Player
from .agents.wolf import WolfAgent
from .agents.villager import VillagerAgent
from .agents.seer import SeerAgent
from .agents.witch import WitchAgent
from .agents.hunter import HunterAgent
from .agents.guard import GuardAgent
from .group_chat import WerewolfGroupChat
from ..services.logger_service import LoggerService
from ..services.tts_interface import TTSInterface
from ..services.llm_service import LLMService


class WerewolfOrchestrator:
    """
    狼人杀游戏编排器
    
    负责整个游戏流程的管理和协调
    """
    
    def __init__(self, config: GameConfig, llm_config: Dict[str, Any], 
                 logger: LoggerService, tts: Optional[TTSInterface] = None):
        """
        初始化游戏编排器
        
        Args:
            config: 游戏配置
            llm_config: LLM 配置
            logger: 日志服务
            tts: TTS 接口（可选）
        """
        self.config = config
        self.llm_service = LLMService(llm_config)
        self.logger = logger
        self.tts = tts
        self.state = GameState()
        self.agents = {}
        self.group_chat = None
        self.speech_order = []
        self.self_explode_flag = False
        self.exploded_player_id = None
        
        # 初始化游戏
        self._init_game()
    
    def _init_game(self):
        """初始化游戏"""
        self.state.game_id = f"werewolf_{random.randint(1000, 9999)}"
        self.state.player_count = self.config.player_count
        
        # 创建玩家和 Agent
        self._create_players_and_agents()
        
        # 创建群聊
        agent_list = list(self.agents.values())
        self.group_chat = WerewolfGroupChat(agent_list, self.logger, [self.llm_service.model_config])
        
        # 记录游戏开始
        self.logger.info(f"游戏开始: {self.state.game_id}")
        self.logger.info(f"玩家配置: {[(p.id, p.role.value, p.name) for p in self.state.players.values()]}")
        
        # 进行警长竞选
        asyncio.run(self._run_president_election())
    
    def _create_players_and_agents(self):
        """创建玩家和对应的 Agent"""
        player_id = 1
        
        for role_info in self.config.roles:
            role_name = role_info["role"]
            count = role_info["count"]
            role_enum = Role(role_name)
            
            for i in range(count):
                # 分配人格
                personality = self.config.personalities[player_id - 1] if player_id <= len(self.config.personalities) else f"Personality_{player_id}"
                
                # 创建玩家
                player = Player(
                    id=player_id,
                    name=f"Player_{player_id}",
                    role=role_enum,
                    personality=personality
                )
                self.state.players[player_id] = player
                
                # 创建对应的角色 Agent
                agent = self._create_agent(player_id, role_enum, personality)
                self.agents[player_id] = agent
                
                player_id += 1
    
    def _create_agent(self, player_id: int, role: Role, personality: str):
        """创建角色 Agent"""
        if role == Role.WEREWOLF:
            return WolfAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        elif role == Role.VILLAGER:
            return VillagerAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        elif role == Role.SEER:
            return SeerAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        elif role == Role.WITCH:
            return WitchAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        elif role == Role.HUNTER:
            return HunterAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        elif role == Role.GUARD:
            return GuardAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
        else:
            # 默认创建村民 Agent
            return VillagerAgent(player_id, f"Player_{player_id}", personality, self.llm_service)
    
    async def run_game(self):
        """
        运行完整的游戏
        """
        self.logger.info("开始运行狼人杀游戏")
        
        # 检查游戏是否已经结束
        if self.state.is_game_over():
            self._end_game()
            return
        
        # 游戏主循环：白天-夜晚交替
        while not self.state.game_over:
            # 白天阶段
            await self._run_day()
            
            if self.state.game_over:
                break
            
            # 夜晚阶段
            await self._run_night()
            
            if self.state.game_over:
                break
        
        self._end_game()
    
    async def _run_day(self):
        """
        白天阶段（发言和投票）
        """
        self.state.day_number += 1
        self.logger.info(f"第 {self.state.day_number} 天开始")
        
        # 初始化发言顺序
        self._init_speech_order()
        
        # 检查是否发生自爆
        self.self_explode_flag = False
        self.exploded_player_id = None
        
        # 白天发言（支持随时自爆）
        await self._run_day_speech()
        
        # 如果发生了自爆，跳过投票，直接进入夜晚
        if self.self_explode_flag:
            self.logger.info(f"{self.exploded_player_id}号 狼人自爆，跳过投票，直接进入夜晚")
            return
        
        # 投票环节
        eliminated = await self._run_vote()
        
        if eliminated:
            player = self.state.players[eliminated]
            player.has_last_words = True  # 被放逐有遗言
            
            # 发表遗言
            speech = await self.agents[eliminated].make_last_words()
            self.logger.log_event("last_words", {
                "player_id": eliminated,
                "content": speech
            })
            
            # 检查遗言中是否指定警长继承者
            if player.role == Role.GUARD and player.president_inherit_id:
                self._handle_president_inheritance(player.president_inherit_id)
        
        # 检查游戏是否结束
        if self.state.is_game_over():
            return
    
    async def _run_day_speech(self):
        """
        白天发言阶段（支持随时自爆）
        """
        self.logger.info("开始白天发言")
        
        for player_id in self.speech_order:
            if self.self_explode_flag:
                break
            
            # 检查玩家是否存活
            if not self.state.players[player_id].is_alive:
                continue
            
            # 检查自爆（只有狼人才能自爆）
            if self.state.players[player_id].role == Role.WEREWOLF:
                explode = await self._check_self_explode(player_id)
                if explode:
                    self.self_explode_flag = True
                    self.exploded_player_id = player_id
                    self._handle_self_explode(player_id)
                    return  # 直接结束白天发言，进入夜晚
            
            # 正常发言
            context = {
                "game_info": {
                    "day_number": self.state.day_number,
                    "alive_players": self.state.get_alive_players(),
                    "president_id": self.state.president_id
                },
                "day_phase": "discussion"
            }
            
            speech = await self.agents[player_id].speak(context)
            
            # 记录发言
            self.logger.log_event("speech", {
                "player_id": player_id,
                "content": speech,
                "day": self.state.day_number
            })
            
            # 如果有 TTS，播放发言
            if self.tts:
                self.tts.speak(f"{player_id}号玩家说：{speech}")
    
    async def _check_self_explode(self, player_id: int) -> bool:
        """
        检查狼人是否自爆
        
        Args:
            player_id: 玩家ID
            
        Returns:
            是否自爆
        """
        # 模拟自爆决策
        # 在实际实现中，这应该是通过 Agent 的决策来完成的
        # 这里简化处理，随机决定是否自爆
        import random
        # 有一定概率自爆，特别是在不利情况下
        alive_wolves = self.state.get_werewolves()
        alive_players = self.state.get_alive_players()
        
        # 如果狼人处于劣势，增加自爆概率
        wolf_ratio = len(alive_wolves) / len(alive_players) if alive_players else 0
        explode_chance = 0.1 if wolf_ratio > 0.3 else 0.3  # 狼人比例低时自爆概率更高
        
        return random.random() < explode_chance
    
    def _handle_self_explode(self, player_id: int):
        """
        处理狼人自爆
        
        Args:
            player_id: 自爆玩家ID
        """
        player = self.state.players[player_id]
        player.is_alive = False
        player.death_cause = DeathCause.SELF_EXPLODE
        player.has_last_words = False  # 自爆没有遗言
        
        # 如果警长自爆，警徽流失
        if player_id == self.state.president_id:
            self.state.president_id = None
            self.logger.info(f"警长自爆，警徽流失（不能指定继承者）")
        
        self.logger.info(f"{player_id}号 狼人自爆，直接进入夜晚")
    
    def _init_speech_order(self):
        """
        初始化发言顺序

        规则：
        - 有警长且警长存活：警长决定左置位或右置位
        - 警长死亡或无警长：按ID顺序
        """
        alive = self.state.get_alive_players()
        alive.sort()  # 按ID排序
        
        # 检查警长是否存活
        if self.state.president_id:
            president = self.state.players.get(self.state.president_id)
            if not president or not president.is_alive:
                # 警长死亡，清除警长
                self.state.president_id = None
        
        if self.state.president_id and self.state.president_id in alive:
            # 警长决定顺序
            president_idx = alive.index(self.state.president_id)
            try:
                direction = self.agents[self.state.president_id].choose_direction()
            except:
                direction = "left"  # 默认左置位

            if direction == "left":
                # 左置位：从警长开始，向左（ID递增方向）发言
                self.speech_order = alive[president_idx:] + alive[:president_idx]
            else:
                # 右置位：从警长开始，向右（ID递减方向）发言
                right_part = alive[president_idx:] + alive[:president_idx]
                self.speech_order = list(reversed(right_part))
        else:
            # 无警长或警长不在存活列表中，按ID顺序
            self.speech_order = alive
    
    async def _run_vote(self) -> Optional[int]:
        """
        投票流程（含平票处理）

        平票处理：
        1. 第一轮平票 → PK 发言（按玩家 ID 顺序），再次投票
        2. 再次平票 → 无人被放逐，进入夜晚
        3. 平票后没有遗言环节
        """
        self.logger.info("开始投票环节")
        
        # 第一轮投票
        votes = await self._collect_votes()
        vote_count = self._count_votes(votes)
        
        if not vote_count:
            self.logger.info("无人投票")
            return None

        max_votes = max(vote_count.values())
        candidates = [p for p, c in vote_count.items() if c == max_votes]

        if len(candidates) == 1:
            eliminated = candidates[0]
            self.logger.info(f"{eliminated}号玩家被投票出局")
            
            # 更新玩家状态
            player = self.state.players[eliminated]
            player.is_alive = False
            player.death_cause = DeathCause.VOTE_OUT
            
            # 如果被投票的是警长，处理警长死亡
            if eliminated == self.state.president_id:
                self._handle_president_death(eliminated)
            
            return eliminated

        # 平票处理
        self.logger.info(f"投票平票：{candidates}")

        # PK 发言（按玩家 ID 排序）
        candidates.sort()  # 按 ID 排序
        for candidate_id in candidates:
            speech = await self.agents[candidate_id].pk_speech()
            self.logger.log_event("pk_speech", {
                "player_id": candidate_id,
                "content": speech
            })

        # 再次投票
        votes_round2 = await self._collect_votes()
        vote_count2 = self._count_votes(votes_round2)

        if not vote_count2:
            self.logger.info("再次平票，无人被放逐")
            return None

        max_votes2 = max(vote_count2.values())
        candidates2 = [p for p, c in vote_count2.items() if c == max_votes2]

        if len(candidates2) == 1:
            eliminated = candidates2[0]
            self.logger.info(f"PK后，{eliminated}号玩家被投票出局")
            
            # 更新玩家状态
            player = self.state.players[eliminated]
            player.is_alive = False
            player.death_cause = DeathCause.VOTE_OUT
            
            # 如果被投票的是警长，处理警长死亡
            if eliminated == self.state.president_id:
                self._handle_president_death(eliminated)
            
            return eliminated
        else:
            self.logger.info("再次平票，无人被放逐")
            return None
    
    async def _collect_votes(self) -> Dict[int, int]:
        """
        收集投票
        
        Returns:
            投票字典 {投票者ID: 被投票者ID}
        """
        votes = {}
        alive_players = self.state.get_alive_players()
        
        for voter_id in alive_players:
            voter = self.state.players[voter_id]
            if not voter.is_alive:
                continue
            
            # 获取候选人（排除自己）
            candidates = [p_id for p_id in alive_players if p_id != voter_id]
            
            context = {
                "alive_players": alive_players,
                "candidates": candidates,
                "previous_votes": votes.copy(),
                "my_id": voter_id
            }
            
            target = await self.agents[voter_id].vote(context)
            
            if target and target in candidates:
                votes[voter_id] = target
                self.logger.log_vote(voter_id, target)
            else:
                # 无效投票视为弃票
                votes[voter_id] = None
        
        return votes
    
    def _count_votes(self, votes: Dict[int, int]) -> Dict[int, float]:
        """
        计票（考虑警长权重）

        警长投票计 1.5 票

        注意：
        - 警长竞选时没有警长，所以没有权重
        - 白天投票时已有警长，所以有权重
        - 警长死亡后，清除警长 ID，后续投票没有权重
        - 如果警长在投票过程中死亡，投票无效
        """
        vote_count = {}
        for voter, candidate in votes.items():
            if candidate:
                # 检查警长是否存活
                if voter == self.state.president_id:
                    president = self.state.players.get(voter)
                    if president and president.is_alive:
                        # 警长投票计 1.5 票
                        weight = 1.5
                    else:
                        # 警长死亡，无权重的普通票
                        weight = 1.0
                else:
                    weight = 1.0

                vote_count[candidate] = vote_count.get(candidate, 0) + weight
        return vote_count