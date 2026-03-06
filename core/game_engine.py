"""游戏引擎 - 增强版"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.state import GameState, Player, Phase, Role
from ui.base import UIBase
from ai.agent import AIAgent
from ai.names import NameGenerator


class GameEngine:
    """游戏引擎 - 增强版"""
    
    def __init__(self, ui: UIBase, config: dict):
        self.ui = ui
        self.config = config
        self.state = GameState()
        self.agents: dict[int, AIAgent] = {}
        self.human_player_id: Optional[int] = None
        self.log_file: Optional[str] = None

        # 游戏配置
        self.witch_heal_used = False  # 女巫解药是否已用
        self.witch_poison_used = False  # 女巫毒药是否已用
        self.president_id: Optional[int] = None  # 警长
        self.round_num = 0  # 发言轮次
        
        # 名字生成器
        self.name_generator = NameGenerator()
    
    def setup(self, player_count: int, roles_config: list[dict],
              personalities: list[str], human_player_id: Optional[int] = None) -> None:
        """设置游戏"""
        self.state.player_count = player_count
        self.human_player_id = human_player_id

        # 创建玩家
        all_roles = []
        for rc in roles_config:
            all_roles.extend([Role(rc["role"])] * rc["count"])

        import random
        random.shuffle(all_roles)
        random.shuffle(personalities)

        for i in range(1, player_count + 1):
            player = Player(
                id=i,
                name=f"{i}号玩家",
                role=all_roles[i-1] if i-1 < len(all_roles) else Role.VILLAGER,
                personality=personalities[(i-1) % len(personalities)],
                is_human=(i == human_player_id),
                is_bot=(i != human_player_id),
            )
            # 根据人格分配名人名字
            personality_key = player.personality or "passive"
            celebrity_name = self.name_generator.assign_name_to_player(i, personality_key)
            player.celebrity_name = celebrity_name
            
            self.state.players[i] = player

        # 设置 UI 的游戏状态（用于上帝视角显示身份）
        if hasattr(self.ui, "set_game_state"):
            self.ui.set_game_state(self.state, human_player_id)

        self._init_log()
        self.state.add_history("game_setup", {
            "player_count": player_count,
            "human_player_id": human_player_id,
            "roles": [r.value for r in all_roles],
            "celebrity_names": {str(k): v.celebrity_name for k, v in self.state.players.items()},
        })
    
    def _init_log(self) -> None:
        """初始化日志文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"logs/game_{timestamp}.json"
        Path("logs").mkdir(exist_ok=True)
    
    def _save_log(self) -> None:
        """保存日志"""
        if self.log_file:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump({
                    "state": json.loads(self.state.to_json()),
                    "history": self.state.history,
                }, f, ensure_ascii=False, indent=2)
    
    def _log_event(self, event_type: str, data: dict) -> None:
        """记录事件"""
        self.state.add_history(event_type, data)
        self._save_log()
    
    def start(self) -> None:
        """开始游戏"""
        self.ui.notify_game_event("game_start", {"players": self.state.player_count})
        self._log_event("game_start", {"player_count": self.state.player_count})
        
        # 显示各玩家角色
        for player in self.state.players.values():
            if player.is_human:
                self.ui.display_system_message(f"你的角色是：{player.role.value}")
        
        # 第一夜
        self.state.night_number = 1
        self._run_night()
        
        # 游戏主循环
        while not self.state.game_over:
            self.state.day_number += 1
            self._run_day()
            
            if self.state.game_over:
                break
            
            self.state.night_number += 1
            self._run_night()
        
        self._end_game()
    
    def _run_night(self) -> None:
        """运行夜晚阶段"""
        self.ui.notify_game_event("night_start", {"night": self.state.night_number})
        self.state.phase = Phase.NIGHT
        self._log_event("night_start", {
            "night": self.state.night_number,
            "alive_players": [p.id for p in self.state.get_alive_players()],
        })

        night_deaths = []

        # 狼人行动
        self.ui.display_system_message("狼人请睁眼，选择袭击目标...")
        wolf_action = self._handle_werewolf_action()

        # 预言家行动
        self.ui.display_system_message("预言家请睁眼，选择查验目标...")
        seer_action = self._handle_seer_action()

        # 女巫行动
        self.ui.display_system_message("女巫请睁眼，选择是否使用药剂...")
        witch_action = self._handle_witch_action(wolf_action.get("target") if wolf_action else None)

        # 处理夜晚结果
        night_deaths = self._process_night_results(wolf_action, seer_action, witch_action)

        # 记录夜晚行动摘要
        self._log_event("night_actions_summary", {
            "wolf_action": wolf_action,
            "seer_action": seer_action,
            "witch_action": witch_action,
            "night_deaths": night_deaths,
        })

        return night_deaths
    
    def _handle_werewolf_action(self) -> dict:
        """处理狼人行动 - 狼人可以交流"""
        alive_villagers = [p.id for p in self.state.get_alive_players() if p.role != Role.WEREWOLF]

        if not alive_villagers:
            return {}

        # 收集所有狼人的选择
        werewolves = self.state.get_alive_werewolves()
        targets = []
        wolf_thoughts = []  # 记录狼人内心活动

        for wolf in werewolves:
            # 告诉狼人队友是谁
            teammate_ids = [w.id for w in werewolves if w.id != wolf.id]

            if wolf.is_human:
                target = self.ui.get_player_input(f"请选择袭击目标 {alive_villagers}: ")
                try:
                    targets.append(int(target))
                    wolf_thoughts.append(f"{wolf.id}号 (狼人) 选择了 {target}号")
                except ValueError:
                    targets.append(alive_villagers[0])
            else:
                agent = self.agents[wolf.id]
                context = {
                    "alive_players": alive_villagers,
                    "wolf_teammates": teammate_ids,
                    "my_id": wolf.id,  # 添加自己的号码
                }
                action, inner_thought = agent.decide_night_action(context)
                # 修复 P0-2: 验证 AI 返回的目标是否存活且不是狼人
                target = action.get("target")
                if target is None or target not in alive_villagers:
                    # AI 返回了无效目标（可能是死亡玩家或狼人），从存活村民中随机选择
                    import random
                    target = random.choice(alive_villagers) if alive_villagers else None
                    inner_thought = f"AI 返回了无效目标，已重新选择 {target}号"
                targets.append(target)

                # 记录内心活动
                wolf_thoughts.append(f"{wolf.id}号 ({wolf.celebrity_name}) 的内心：{inner_thought}")

        # 显示狼人内心活动（上帝视角）
        self.ui.display_system_message("=== 狼人行动（上帝视角） ===")
        for thought in wolf_thoughts:
            # 调试输出：显示内心活动
            if thought:
                self.ui.display_inner_thought("狼人", thought)
            else:
                # 如果内心活动为空，显示默认提示
                self.ui.display_system_message("  [狼人内心] （思考中...）")

        if targets:
            target = max(set(targets), key=targets.count)
            self.ui.display_system_message(f"狼人选择了袭击 {target}号玩家")
            return {"target": target}
        return {}
    
    def _handle_seer_action(self) -> dict:
        """处理预言家行动"""
        seers = [p for p in self.state.get_alive_players() if p.role == Role.SEER]
        if not seers:
            return {}

        seer = seers[0]
        # 修复 P0-1: 确保只从存活玩家中选择查验目标
        alive_others = [p.id for p in self.state.get_alive_players() if p.id != seer.id]
        inner_thought = ""
        
        # 修复 Bug 2: 获取已查验玩家列表
        checked_players = getattr(self.state, 'seer_checked_players', [])

        if seer.is_human:
            target = self.ui.get_player_input(f"请选择查验目标 {alive_others}: ")
            try:
                target_id = int(target)
                if target_id in alive_others:
                    inner_thought = f"{seer.id}号 (预言家) 选择了查验 {target_id}号"
                    # 记录已查验玩家
                    if target_id not in checked_players:
                        checked_players.append(target_id)
                        self.state.seer_checked_players = checked_players
                    return {"target": target_id, "thought": inner_thought}
            except ValueError:
                pass
        else:
            agent = self.agents[seer.id]
            context = {
                "alive_players": alive_others,
                "my_id": seer.id,  # 添加自己的号码
                "checked_players": checked_players,  # 传递已查验玩家列表
            }
            action, inner_thought = agent.decide_night_action(context)
            # 修复 P0-1: 验证 AI 返回的目标是否存活，如果不存活则重新选择
            target = action.get("target")
            if target is None or target not in alive_others:
                # AI 返回了无效目标（可能是死亡玩家），从存活玩家中随机选择
                import random
                target = random.choice(alive_others) if alive_others else None
                inner_thought = f"AI 返回了无效目标，已重新选择 {target}号"
            
            # 修复 Bug 2: 如果 AI 返回了已查验的玩家，重新选择
            if target in checked_players:
                import random
                valid_targets = [p for p in alive_others if p not in checked_players]
                if valid_targets:
                    target = random.choice(valid_targets)
                    inner_thought = f"AI 返回了已查验玩家，已重新选择 {target}号"
            
            # 记录已查验玩家
            if target and target not in checked_players:
                checked_players.append(target)
                self.state.seer_checked_players = checked_players

            # 确保内心活动不为空
            if not inner_thought:
                inner_thought = "选择查验目标，希望能找到狼人"
            inner_thought = f"{seer.id}号 ({seer.celebrity_name}) 的内心：{inner_thought}"
            return {"target": target, "thought": inner_thought}

        return {"target": alive_others[0] if alive_others else None, "thought": ""}
    
    def _handle_witch_action(self, dead_player_id: Optional[int]) -> dict:
        """处理女巫行动"""
        witches = [p for p in self.state.get_alive_players() if p.role == Role.WITCH]
        if not witches:
            return {}

        witch = witches[0]
        alive_players = [p.id for p in self.state.get_alive_players()]
        action = {}
        inner_thought = ""

        if witch.is_human:
            if dead_player_id and not self.witch_heal_used:
                choice = self.ui.get_player_input(f"{dead_player_id}号死亡，是否使用解药？(y/n): ")
                if choice.lower() == 'y':
                    action = {"action": "heal", "target": dead_player_id}
                    self.witch_heal_used = True
                    inner_thought = f"{witch.id}号 (女巫) 的内心：使用了救药救了{dead_player_id}号"

            if not self.witch_poison_used and not action:
                choice = self.ui.get_player_input(f"是否使用毒药？(y/n): ")
                if choice.lower() == 'y':
                    target = self.ui.get_player_input(f"选择毒杀目标 {alive_players}: ")
                    try:
                        action = {"action": "poison", "target": int(target)}
                        self.witch_poison_used = True
                        inner_thought = f"{witch.id}号 (女巫) 的内心：使用了毒药毒杀{target}号"
                    except ValueError:
                        pass
        else:
            agent = self.agents[witch.id]
            context = {
                "alive_players": alive_players,
                "dead_player": dead_player_id,
                "my_id": witch.id,  # 添加自己的号码
                "heal_used": self.witch_heal_used,  # 告知 AI 解药是否已用
                "poison_used": self.witch_poison_used,  # 告知 AI 毒药是否已用
            }
            action, inner_thought_raw = agent.decide_night_action(context)
            
            # 调试日志：打印 AI 返回的 action
            print(f"[DEBUG] 女巫 AI 返回 action: {action}")
            print(f"[DEBUG] 女巫 AI 返回 inner_thought: {inner_thought_raw}")

            # 确保内心活动不为空
            if not inner_thought_raw:
                inner_thought_raw = "决定是否使用药剂"

            # 修复：验证 action 格式，确保有 action 和 target 字段
            action_type = action.get("action") if action else None
            
            if action_type == "heal":
                # 修复：检查解药是否已用
                if self.witch_heal_used:
                    self.ui.display_system_message("女巫试图使用解药，但解药已用过")
                    action = {"action": "none"}
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}（但解药已用）"
                else:
                    self.witch_heal_used = True
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}"
            elif action_type == "poison":
                # 修复：检查毒药是否已用
                if self.witch_poison_used:
                    self.ui.display_system_message("女巫试图使用毒药，但毒药已用过")
                    action = {"action": "none"}
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}（但毒药已用）"
                else:
                    self.witch_poison_used = True
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}"
            else:
                # 修复：如果 AI 没有主动用药，添加默认行为
                # 第一夜且有人死亡（通常是狼刀目标），自动使用解药自救
                if dead_player_id and not self.witch_heal_used and self.state.night_number == 1:
                    action = {"action": "heal", "target": dead_player_id}
                    self.witch_heal_used = True
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：第一夜自救，使用解药救了{dead_player_id}号"
                    print(f"[DEBUG] 女巫默认行为：第一夜自救")
                # 后续夜晚，如果毒药未用，有一定概率使用毒药
                elif not self.witch_poison_used and alive_players and len(alive_players) > 3:
                    import random
                    # 30% 概率使用毒药
                    if random.random() < 0.3:
                        # 选择一个可疑目标（简单策略：随机选择）
                        poison_target = random.choice(alive_players)
                        action = {"action": "poison", "target": poison_target}
                        self.witch_poison_used = True
                        inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：使用毒药毒杀{poison_target}号"
                        print(f"[DEBUG] 女巫默认行为：使用毒药毒杀{poison_target}号")
                else:
                    inner_thought = f"{witch.id}号 ({witch.celebrity_name}) 的内心：{inner_thought_raw}"

        # 显示女巫内心活动（上帝视角）
        if inner_thought:
            self.ui.display_system_message("=== 女巫行动（上帝视角） ===")
            self.ui.display_inner_thought("女巫", inner_thought)
        else:
            self.ui.display_system_message("=== 女巫行动（上帝视角） ===")
            self.ui.display_system_message("  [女巫内心] （思考中...）")

        return action
    
    def _process_night_results(self, wolf_action: dict, seer_action: dict,
                                witch_action: dict) -> list[int]:
        """处理夜晚结果"""
        night_deaths = []

        # 获取存活玩家列表（用于猎人技能）
        alive_villagers = [p.id for p in self.state.players.values() if p.is_alive and p.role != Role.WEREWOLF]

        # 显示预言家内心活动和查验结果（上帝视角）
        if seer_action.get("target"):
            target_id = seer_action["target"]
            target = self.state.players.get(target_id)
            if target:
                self.state.seer_check_target = target_id
                self.state.seer_check_result = target.role

                # 显示内心活动
                thought = seer_action.get("thought", "")
                self.ui.display_system_message("=== 预言家行动（上帝视角） ===")
                if thought:
                    self.ui.display_inner_thought("预言家", thought)
                else:
                    self.ui.display_system_message("  [预言家内心] （思考中...）")

                # 显示查验结果
                role_name = target.role.value if target.role else "未知"
                self.ui.display_system_message(f"预言家查验了 {target_id}号，结果是：{role_name}")

                self._log_event("seer_check", {
                    "target": target_id,
                    "result": target.role.value,
                })

        # 处理狼人袭击
        killed_by_wolf = None
        if wolf_action.get("target"):
            target_id = wolf_action["target"]
            target = self.state.players.get(target_id)
            if target and target.is_alive:
                killed_by_wolf = target_id

        # 处理女巫行动
        saved = False
        poisoned = None

        if witch_action.get("action") == "heal" and witch_action.get("target") == killed_by_wolf:
            saved = True
            self.ui.display_system_message("女巫使用了解药")

        if witch_action.get("action") == "poison" and witch_action.get("target"):
            poisoned = witch_action["target"]
            self.ui.display_system_message("女巫使用了毒药")

        # 应用死亡
        if killed_by_wolf and not saved:
            target = self.state.players[killed_by_wolf]
            target.is_alive = False
            target.death_cause = "wolf"  # 记录死亡原因：狼刀
            night_deaths.append(killed_by_wolf)
            self.ui.display_system_message(f"{target.name} 在夜晚死亡")
            
            # 猎人技能 - 被狼刀死亡可以开枪
            if target.role == Role.HUNTER:
                self.ui.display_system_message(f"{target.name} 是猎人，被狼刀死亡，可以发动技能！")
                self._handle_hunter_skill(target, alive_villagers)
            
            self._log_event("night_death", {"player_id": killed_by_wolf, "role": target.role.value, "cause": "wolf"})

        if poisoned:
            target = self.state.players[poisoned]
            if target.is_alive:
                target.is_alive = False
                target.death_cause = "poison"  # 记录死亡原因：毒药
                night_deaths.append(poisoned)
                self.ui.display_system_message(f"{target.name} 被毒杀")
                
                # 猎人技能 - 被毒死不能开枪
                if target.role == Role.HUNTER:
                    self.ui.display_system_message(f"{target.name} 是猎人，但被毒杀，不能发动技能")
                
                self._log_event("night_death", {"player_id": poisoned, "role": target.role.value, "cause": "poison"})

        # 检查游戏是否结束
        self.state.check_game_over()

        return night_deaths
    
    def _handle_hunter_skill(self, hunter: Player, alive_players: list[int]) -> None:
        """
        处理猎人技能发动

        Args:
            hunter: 猎人玩家对象
            alive_players: 存活玩家 ID 列表（不包括猎人自己）
        """
        # 调试日志：猎人技能发动开始
        print(f"[DEBUG] 猎人技能发动：猎人={hunter.id}号，存活玩家={alive_players}")
        
        if hunter.is_human:
            target = self.ui.get_player_input(f"选择带走一人 { [p for p in alive_players if p != hunter.id] }: ")
            try:
                target_id = int(target)
                if target_id in [p for p in alive_players if p != hunter.id]:
                    target_player = self.state.players[target_id]
                    target_player.is_alive = False
                    target_player.death_cause = "hunter"  # 记录死亡原因：猎人带走
                    self.ui.display_system_message(f"{target_player.name} 被猎人带走了！")
                    self._log_event("hunter_skill", {"hunter_id": hunter.id, "target": target_id})
                    print(f"[DEBUG] 猎人技能执行成功：带走了{target_id}号")
            except ValueError:
                print(f"[DEBUG] 猎人技能：人类玩家输入无效")
                pass
        else:
            agent = self.agents[hunter.id]
            context = {"alive_players": [p for p in alive_players if p != hunter.id]}
            target = agent.hunter_skill(context)
            print(f"[DEBUG] 猎人 AI 返回目标：{target}")
            
            # 修复：如果 AI 返回 null 或无效目标，随机选择一个存活玩家
            if target is None or target not in alive_players or target == hunter.id:
                import random
                valid_targets = [p for p in alive_players if p != hunter.id]
                if valid_targets:
                    target = random.choice(valid_targets)
                    print(f"[DEBUG] 猎人 AI 返回无效目标，随机选择：{target}")
            
            if target is not None:
                target_player = self.state.players[target]
                target_player.is_alive = False
                target_player.death_cause = "hunter"  # 记录死亡原因：猎人带走
                self.ui.display_system_message(f"{target_player.name} 被猎人带走了！")
                self._log_event("hunter_skill", {"hunter_id": hunter.id, "target": target})
                print(f"[DEBUG] 猎人技能执行成功：带走了{target}号")
            else:
                print(f"[DEBUG] 猎人技能：没有可用目标")

    def _run_day(self) -> None:
        """运行白天阶段 - 完整流程"""
        self.ui.notify_game_event("day_start", {"day": self.state.day_number})
        self.state.phase = Phase.DAY_DISCUSS
        self._log_event("day_start", {
            "day": self.state.day_number,
            "alive_players": [p.id for p in self.state.get_alive_players()],
            "night_deaths": [],  # 夜晚死亡已在之前公布
        })
        
        # 公布昨晚情况
        night_deaths = []  # 实际死亡在夜晚已公布，这里只是逻辑传递

        # 遗言环节（有人死亡时）
        if self.state.day_number == 1:
            # 第一天，没有人死亡（因为第一夜还没到）
            pass
        # 有死亡，但遗言在死亡时已发表（在放逐环节处理）

        # 警长竞选（第一天）
        if self.state.day_number == 1 and not self.president_id:
            self._run_president_election()
        
        # 多轮讨论（至少 2 轮）
        self._run_discussion(rounds=2)
        
        if self.state.game_over:
            return
        
        # 投票前辩论
        self._run_pre_vote_debate()
        
        # 投票阶段
        self._run_vote()
    
    def _run_president_election(self) -> None:
        """警长竞选环节"""
        self.ui.display_system_message("=== 警长竞选 ===")
        self._log_event("president_election_start", {"day": 1})

        alive_players = self.state.get_alive_players()
        candidates = []

        # AI 决定是否参选
        for player in alive_players:
            if player.is_human:
                choice = self.ui.get_player_input("是否竞选警长？(y/n): ")
                if choice.lower() == 'y':
                    candidates.append(player.id)
            else:
                # 修复 Bug 3: 提高 AI 参选概率（70%），确保有足够候选人
                import random
                if random.random() > 0.3:  # 70% 概率参选
                    candidates.append(player.id)

        # 修复 Bug 3: 如果无人参选，强制随机选择 2-3 名 AI 参选
        if not candidates:
            import random
            forced_candidates = random.sample([p.id for p in alive_players], min(3, len(alive_players)))
            candidates = forced_candidates
            self.ui.display_system_message(f"无人自愿竞选，以下玩家被强制参选：{', '.join([f'{p}号' for p in candidates])}")

        # 记录参选玩家
        self._log_event("president_candidates", {
            "candidates": candidates,
            "candidate_names": [self.state.players[pid].name for pid in candidates]
        })

        if not candidates:
            self.ui.display_system_message("无人竞选警长")
            self._log_event("president_election_end", {"reason": "no_candidates"})
            return

        self.ui.display_system_message(f"竞选警长的玩家：{', '.join([f'{p}号' for p in candidates])}")

        # 竞选发言
        speeches = []
        for pid in sorted(candidates):
            player = self.state.players[pid]
            if player.is_human:
                speech = self.ui.get_player_input("请发表竞选宣言：")
            else:
                agent = self.agents[pid]
                context = {
                    "day_number": 1,
                    "seer_check_target": None,  # 第 1 天没有查验
                    "seer_check_result": None,
                    "previous_speeches": [],
                    "alive_players": [p.id for p in alive_players],
                }
                speech, inner_thought = agent.speak(context, round_num=1)

                # 记录竞选发言的内心独白
                self._log_event("president_speech", {
                    "player_id": pid,
                    "speech": speech,
                    "inner_thought": inner_thought,
                })

            self.ui.display_message(player.name, f"[警长竞选] {speech}")
            speeches.append({"speaker": player.name, "player_id": pid, "content": speech})

        # 投票
        self.ui.display_system_message("=== 警长投票（上帝视角） ===")
        vote_counts = {}
        vote_details = {}
        vote_thoughts = {}

        for voter in alive_players:
            if voter.id not in candidates:
                if voter.is_human:
                    vote = self.ui.get_player_input(f"请投票给警长 {candidates}: ")
                    try:
                        vote_target = int(vote)
                        if vote_target in candidates:
                            vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                            vote_details[voter.id] = vote_target
                            vote_thoughts[voter.id] = f"{voter.id}号 (人类) 投票给 {vote_target}号"
                    except ValueError:
                        pass
                else:
                    # AI 投票
                    agent = self.agents[voter.id]
                    context = {
                        "alive_players": candidates,
                        "my_id": voter.id,
                    }
                    vote, inner_thought = agent.vote(context)
                    # 修复 Bug 3: 如果 AI 弃权，随机投票给一个候选人
                    if vote is None or vote not in candidates:
                        import random
                        vote = random.choice(candidates)
                        inner_thought = f"随机投票给 {vote}号"
                    
                    vote_counts[vote] = vote_counts.get(vote, 0) + 1
                    vote_details[voter.id] = vote
                    vote_thoughts[voter.id] = f"{voter.id}号 ({voter.celebrity_name}-{voter.role.value}) 投票给 {vote}号：{inner_thought}"

        # 显示警长投票内心活动
        self.ui.display_system_message("--- 警长投票详情（上帝视角） ---")
        for voter_id in sorted(vote_thoughts.keys()):
            thought = vote_thoughts[voter_id]
            self.ui.display_inner_thought(f"{voter_id}号", thought)

        # 记录投票详情
        self._log_event("president_vote", {
            "vote_counts": vote_counts,
            "vote_details": vote_details,
            "vote_thoughts": vote_thoughts,
            "voters": [voter.id for voter in alive_players if voter.id not in candidates]
        })

        if vote_counts:
            max_votes = max(vote_counts.values())
            winners = [k for k, v in vote_counts.items() if v == max_votes]

            if len(winners) == 1:
                self.president_id = winners[0]
                self.ui.display_system_message(f"{winners[0]}号 当选警长！")
                self._log_event("president_elected", {
                    "president_id": winners[0],
                    "votes": max_votes,
                    "total_voters": sum(vote_counts.values())
                })
            else:
                self.ui.display_system_message("平票，无人当选警长")
                self._log_event("president_election_end", {
                    "reason": "tie",
                    "tied_candidates": winners
                })
        else:
            self.ui.display_system_message("无人投票，无人当选警长")
            self._log_event("president_election_end", {"reason": "no_votes"})
    
    def _run_discussion(self, rounds: int = 2) -> None:
        """运行讨论阶段 - 多轮"""
        for round_num in range(1, rounds + 1):
            self.ui.display_system_message(f"=== 第{round_num}轮发言 ===")
            self.round_num = round_num

            alive_players = self.state.get_alive_players()
            speeches = []

            # 获取 AI 发言延迟
            ai_delay = self.config.get("game", {}).get("ai_speech_delay", 0.3)

            # 按顺序发言
            for player in sorted(alive_players, key=lambda p: p.id):
                if player.is_human:
                    speech = self.ui.get_player_input(f"请{player.name}发言：")
                    inner_thought = "[人类玩家的内心]"
                else:
                    agent = self.agents[player.id]
                    context = {
                        "day_number": self.state.day_number,
                        "night_deaths": [],  # 夜晚死亡已在之前公布
                        "seer_check_target": self.state.seer_check_target,  # 修复：传递查验目标
                        "seer_check_result": self.state.seer_check_result,  # 修复：传递查验结果
                        "previous_speeches": speeches,
                        "alive_players": [p.id for p in alive_players],
                    }
                    speech, inner_thought = agent.speak(context, round_num=round_num)

                    # 修复 Bug 1: 只有存活玩家才记录内心独白
                    if player.is_alive:
                        self._log_event("inner_thought", {
                            "player_id": player.id,
                            "thought": inner_thought,
                            "round": round_num,
                        })

                    if ai_delay > 0:
                        time.sleep(ai_delay)

                self.ui.display_message(player.name, speech)
                speeches.append({
                    "speaker": player.name,
                    "player_id": player.id,
                    "content": speech,
                })

                # 添加到 AI 记忆，并让每个 AI 分析是否要更新信任/怀疑列表
                for p in alive_players:
                    if not p.is_human and p.id in self.agents:
                        agent = self.agents[p.id]
                        agent.add_memory({
                            "type": "speech",
                            "player_id": player.id,
                            "content": speech,
                            "round": round_num,
                        })
                        # 分析发言，更新信任/怀疑列表
                        agent.analyze_speech(speech, player.id)
    
    def _run_pre_vote_debate(self) -> None:
        """投票前辩论"""
        self.ui.display_system_message("=== 投票前辩论 ===")
        
        alive_players = self.state.get_alive_players()
        
        # 每个玩家简短发言（总结立场）
        for player in sorted(alive_players, key=lambda p: p.id):
            if player.is_human:
                speech = self.ui.get_player_input(f"请{player.name}总结发言：")
            else:
                agent = self.agents[player.id]
                # 获取 AI 的总结发言
                context = {
                    "day_number": self.state.day_number,
                    "alive_players": [p.id for p in alive_players],
                    "suspect_list": agent.suspect_list,
                    "trust_list": agent.trust_list,
                }
                # 生成简短总结
                speech = self._generate_vote_summary(agent, context)
            
            self.ui.display_message(player.name, speech[:80])  # 限制显示长度
    
    def _generate_vote_summary(self, agent: AIAgent, context: dict) -> str:
        """生成投票前总结"""
        suspect_list = context.get("suspect_list", [])
        trust_list = context.get("trust_list", [])
        
        suspect_str = f"{', '.join([f'{p}号' for p in suspect_list])}" if suspect_list else "暂时没明确目标"
        trust_str = f"{', '.join([f'{p}号' for p in trust_list])}" if trust_list else "暂无"
        
        # 隐藏真实身份，只说"好人"
        role_str = "好人"
        
        return f"我是{role_str}，怀疑{suspect_str}，信任{trust_str}。"
    
    def _run_vote(self) -> None:
        """运行投票阶段 - 展示内心活动"""
        self.state.phase = Phase.DAY_VOTE
        self.ui.notify_game_event("vote_result", {})

        alive_players = self.state.get_alive_players()
        vote_counts = {}
        vote_details = {}
        vote_thoughts = {}  # 记录每个玩家的投票内心活动

        # 显示投票开始
        self.ui.display_system_message("=== 投票阶段（上帝视角） ===")

        # 收集投票
        for player in alive_players:
            if player.is_human:
                vote = self.ui.get_player_input(f"请{player.name}投票（输入玩家编号或 skip 弃票）: ")
                if vote.lower() == "skip":
                    vote_details[player.id] = None
                    vote_thoughts[player.id] = f"{player.id}号 (人类) 选择了弃权"
                    continue
                try:
                    vote_target = int(vote)
                    if vote_target in [p.id for p in alive_players]:
                        vote_counts[vote_target] = vote_counts.get(vote_target, 0) + 1
                        vote_details[player.id] = vote_target
                        vote_thoughts[player.id] = f"{player.id}号 (人类) 投票给 {vote_target}号"
                except ValueError:
                    vote_details[player.id] = None
                    vote_thoughts[player.id] = f"{player.id}号 (人类) 无效投票"
            else:
                agent = self.agents[player.id]
                context = {
                    "alive_players": [p.id for p in alive_players],
                    "my_id": player.id,  # 添加自己的号码
                    "previous_speeches": [],  # 可以传入完整发言历史
                }
                vote, inner_thought = agent.vote(context)
                
                if vote:
                    vote_counts[vote] = vote_counts.get(vote, 0) + 1
                    vote_details[player.id] = vote
                    vote_thoughts[player.id] = f"{player.id}号 ({player.celebrity_name}-{player.role.value}) 投票给 {vote}号：{inner_thought}"
                else:
                    vote_details[player.id] = None
                    vote_thoughts[player.id] = f"{player.id}号 ({player.celebrity_name}-{player.role.value})：{inner_thought}"

        self.state.vote_counts = vote_counts

        # 显示所有玩家的投票内心活动（上帝视角）
        self.ui.display_system_message("--- 投票详情（上帝视角） ---")
        for voter_id in sorted(vote_thoughts.keys()):
            thought = vote_thoughts[voter_id]
            self.ui.display_inner_thought(f"{voter_id}号", thought)

        # 记录投票详情
        self._log_event("day_vote", {
            "day": self.state.day_number,
            "vote_counts": vote_counts,
            "vote_details": vote_details,
            "vote_thoughts": vote_thoughts,  # 记录内心活动
            "alive_players": [p.id for p in alive_players],
        })

        # 公布结果
        if vote_counts:
            max_votes = max(vote_counts.values())
            top_candidates = [k for k, v in vote_counts.items() if v == max_votes]

            if len(top_candidates) == 1:
                eliminated_id = top_candidates[0]
                eliminated = self.state.players[eliminated_id]

                # 发表遗言
                self.ui.display_system_message(f"\n{eliminated.name} 被放逐，请留遗言：")
                if eliminated.is_human:
                    last_words = self.ui.get_player_input("请留遗言：")
                else:
                    agent = self.agents[eliminated_id]
                    context = {
                        "alive_players": [p.id for p in alive_players if p.id != eliminated_id],
                        "death_cause": "voted_out",  # 被投票出局
                    }
                    last_words = agent.make_last_words(context)

                self.ui.display_message(eliminated.name, f"[遗言] {last_words}")
                self._log_event("last_words", {"player_id": eliminated_id, "words": last_words})

                # 猎人技能 - 修复：只有被狼刀死亡才能开枪，被投票出局不能开枪
                # 这里是被投票出局，所以不能发动猎人技能
                if eliminated.role == Role.HUNTER:
                    self.ui.display_system_message(f"{eliminated.name} 是猎人，但被投票出局，不能发动技能")
                    # 记录猎人被放逐
                    self._log_event("hunter_eliminated", {
                        "hunter_id": eliminated_id,
                        "reason": "voted_out",
                        "note": "猎人被投票出局，不能发动技能"
                    })

                eliminated.is_alive = False
                # 记录死亡原因
                eliminated.death_cause = "voted_out"  # 被投票出局
                self.ui.display_message("系统", f"{eliminated.name} 被放逐了！")
                self.ui.notify_game_event("player_eliminated", {
                    "player_id": eliminated_id,
                    "role": eliminated.role.value if eliminated.role else "未知",
                })
                self._log_event("player_eliminated", {
                    "player_id": eliminated_id,
                    "role": eliminated.role.value,
                    "votes": max_votes,
                })
            else:
                self.ui.display_system_message("平票，无人被放逐")
        else:
            self.ui.display_system_message("无人投票，无人被放逐")
        
        self.state.check_game_over()
    
    def _end_game(self) -> None:
        """结束游戏"""
        self.ui.notify_game_event("game_over", {"winner": self.state.winner})
        
        # 记录游戏结束详情
        self._log_event("game_over", {
            "winner": self.state.winner,
            "winner_name": "狼人" if self.state.winner == "werewolf" else "好人阵营",
            "total_days": self.state.day_number,
            "total_nights": self.state.night_number,
            "final_players": {
                pid: {
                    "role": p.role.value,
                    "is_alive": p.is_alive,
                    "personality": p.personality,
                }
                for pid, p in self.state.players.items()
            },
            "death_log": [
                h for h in self.state.history
                if h["type"] in ["night_death", "player_eliminated"]
            ],
        })
        
        self.ui.display_system_message("=== 游戏结束 ===")
        if self.state.winner == "werewolf":
            self.ui.display_system_message("[狼人获胜]")
        else:
            self.ui.display_system_message("[好人阵营获胜]")
        
        self.ui.display_system_message("=== 玩家身份 ===")
        for player in self.state.players.values():
            role_str = player.role.value if player.role else "未知"
            status = "存活" if player.is_alive else "死亡"
            self.ui.display_system_message(f"{player.name}: {role_str} ({status})")
        
        self.ui.display_system_message(f"日志已保存至：{self.log_file}")
