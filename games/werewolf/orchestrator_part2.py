    
    async def _run_night(self) -> List[int]:
        """
        夜晚行动（正确顺序 + 深度信息隔离）

        顺序：守卫 → 狼人 → 女巫 → 预言家
        """
        self.state.night_number += 1
        self.logger.info(f"第 {self.state.night_number} 夜开始")

        # 1. 守卫行动
        guard_action = await self._run_guard_night()

        # 2. 狼人行动
        wolf_action = await self._run_wolf_night()

        # 3. 女巫行动（深度信息隔离）
        # 女巫只知道狼人是否刀了人，不知道守卫守护情况
        # 即使狼人空刀，女巫也不知道
        # 即使刀的是女巫自己，女巫也不知道具体是谁
        witch_action = await self._run_witch_night(wolf_action)

        # 4. 预言家行动
        seer_action = await self._run_seer_night()

        # 5. 计算死亡
        deaths = self._calculate_night_deaths(
            wolf_action, guard_action, witch_action
        )

        # 6. 设置遗言标志
        for player_id in deaths:
            player = self.state.players[player_id]
            player.has_last_words = self.state.get_last_words_flag(
                player.death_cause, self.state.night_number
            )
            
            # 检查死亡玩家是否为警长，需要处理警长继承
            if player_id == self.state.president_id:
                self._handle_president_death(player_id)

        # 7. 处理猎人死亡触发技能
        hunter_deaths = [pid for pid in deaths if self.state.players[pid].role == Role.HUNTER]
        for hunter_id in hunter_deaths:
            hunter_target = await self._run_hunter_skill(hunter_id, self.state.players[hunter_id].death_cause)
            if hunter_target:
                self.logger.info(f"猎人 {hunter_id} 号开枪击中 {hunter_target} 号")

        # 8. 检查游戏是否结束
        if self.state.is_game_over():
            return deaths

        # 9. 发表遗言（对于有遗言的死者）
        for player_id in deaths:
            player = self.state.players[player_id]
            if player.has_last_words:
                speech = await self.agents[player_id].make_last_words()
                self.logger.log_event("last_words", {
                    "player_id": player_id,
                    "content": speech
                })

        return deaths
    
    async def _run_guard_night(self) -> Dict[str, Any]:
        """
        守卫夜晚行动
        """
        guard_ids = [pid for pid in self.state.get_alive_players() 
                     if self.state.players[pid].role == Role.GUARD]
        
        if not guard_ids:
            return {"action": "none"}
        
        guard_id = guard_ids[0]  # 假设只有一个守卫
        guard = self.state.players[guard_id]
        
        context = {
            "alive_players": self.state.get_alive_players(),
            "my_id": guard_id,
            "guarded_players": guard.guarded_players,
            "last_night_guarded": guard.guarded_players[-1] if guard.guarded_players else None
        }
        
        action = await self.agents[guard_id].night_action(context)
        
        # 更新守卫守护记录（只保留上一夜的记录）
        if action.get("target"):
            guard.guarded_players = [action["target"]]
        
        self.logger.log_night_action(guard_id, "guard", action.get("target"))
        return action
    
    async def _run_wolf_night(self) -> Dict[str, Any]:
        """
        狼人夜晚行动
        """
        wolf_ids = self.state.get_werewolves()
        
        if not wolf_ids:
            return {"action": "none"}
        
        # 狼人协商攻击目标
        # 这里简化处理，取第一个狼人的选择
        wolf_id = wolf_ids[0]
        context = {
            "alive_players": self.state.get_alive_players(),
            "my_id": wolf_id,
            "wolf_teammates": [wid for wid in wolf_ids if wid != wolf_id]
        }
        
        action = await self.agents[wolf_id].night_action(context)
        
        self.logger.log_night_action(wolf_id, "attack", action.get("target"))
        return action
    
    async def _run_witch_night(self, wolf_action: Dict[str, Any]) -> Dict[str, Any]:
        """
        女巫夜晚行动（深度信息隔离）

        信息隔离原则：
        1. 女巫只知道"狼人是否刀了人"
        2. 不知道死因（被狼刀/自刀/其他）
        3. 不知道狼人是否空刀
        4. 不知道守卫守护情况
        5. 不知道 dead_player 是谁（即使刀的是自己）

        深度信息隔离：
        - has_death 只基于 wolf_target is not None
        - 不考虑守卫守护情况（否则泄露守卫信息）
        """
        witch_ids = [pid for pid in self.state.get_alive_players() 
                     if self.state.players[pid].role == Role.WITCH]
        
        if not witch_ids:
            return {"action": "none"}
        
        witch_id = witch_ids[0]  # 假设只有一个女巫
        witch = self.state.players[witch_id]

        # 狼人刀的目标
        wolf_target = wolf_action.get("target")

        # 深度信息隔离：has_death 只基于狼人是否刀了人
        # 不考虑守卫守护情况，否则泄露守卫信息
        has_death = wolf_target is not None

        context = {
            "has_death": has_death,  # 狼人是否刀了人（不考虑守卫）
            # 不传递 dead_player，即使刀的是女巫自己
            "heal_used": witch.heal_used,
            "poison_used": witch.poison_used,
            "is_first_night": self.state.night_number == 1,
            "alive_players": self.state.get_alive_players(),
            "my_id": witch_id,
            "can_dual_use": self.config.rules.get("witch_same_night_dual_use", False),
            "cannot_poison_first_night": self.config.rules.get("witch_cannot_poison_first_night", False),
            "rules": self.config.rules,
            "wolf_target": wolf_target  # 实际被刀目标，用于内部计算，但不告诉女巫
        }

        action = await self.agents[witch_id].night_action(context)

        # 验证和处理
        if action.get("action") == "heal":
            if witch.heal_used:
                action = {"action": "none"}
            elif not context["can_dual_use"] and action.get("poison_target"):
                action = {"action": "none"}
            else:
                witch.heal_used = True
                # 女巫自救：记录救的是狼人刀的目标
                # 如果狼人空刀，女巫自救无效（但女巫不知道）
                action["save_target"] = wolf_target if has_death else None
        elif action.get("action") == "poison":
            if witch.poison_used:
                action = {"action": "none"}
            elif not context["can_dual_use"] and action.get("heal_target"):
                action = {"action": "none"}
            elif context["cannot_poison_first_night"] and self.state.night_number == 1:
                action = {"action": "none"}  # 首夜不能用毒
            elif action.get("poison_target") not in context["alive_players"]:
                action = {"action": "none"}
            else:
                witch.poison_used = True
        elif action.get("action") == "dual":
            # 双药同夜使用
            if witch.heal_used or witch.poison_used or not context["can_dual_use"]:
                action = {"action": "none"}
            else:
                witch.heal_used = True
                witch.poison_used = True

        self.logger.log_night_action(witch_id, action.get("action"), action.get("target"))
        return action
    
    async def _run_seer_night(self) -> Dict[str, Any]:
        """
        预言家夜晚行动
        """
        seer_ids = [pid for pid in self.state.get_alive_players() 
                    if self.state.players[pid].role == Role.SEER]
        
        if not seer_ids:
            return {"action": "none"}
        
        seer_id = seer_ids[0]  # 假设只有一个预言家
        seer = self.state.players[seer_id]
        
        context = {
            "alive_players": self.state.get_alive_players(),
            "my_id": seer_id,
            "checked_players": seer.checked_players
        }
        
        action = await self.agents[seer_id].night_action(context)
        
        # 更新预言家查验记录
        if action.get("target"):
            seer.checked_players.append(action["target"])
        
        self.logger.log_night_action(seer_id, "check", action.get("target"))
        return action
    
    def _calculate_night_deaths(self, wolf_action, guard_action, witch_action):
        """
        计算夜晚死亡（同守同救处理）

        规则：
        1. 同守同救 → 死亡（两股魔力冲突）
        2. 被守护 → 不死
        3. 被救 → 不死
        4. 被刀且没守护没救 → 死亡
        5. 女巫自救 + 被守护 → 自救成功（不算同守同救）
        6. 狼人空刀 + 女巫自救 → 自救无效（但女巫不知道）

        特殊情况处理：
        - 女巫自救（使用解药救自己）+ 守卫守护女巫 → 不算同守同救
        - 因为女巫自救是解药效果，守卫守护是守护效果，两者不冲突
        - 女巫自救成功，无论是否被守护

        信息隔离：
        - 守卫和女巫不应该知道同守同救的结果
        """
        wolf_target = wolf_action.get("target")
        guard_target = guard_action.get("target")
        witch_save_target = witch_action.get("save_target")
        witch_poison_target = witch_action.get("poison_target")
        witch_id = next((pid for pid in self.state.get_alive_players() 
                         if self.state.players[pid].role == Role.WITCH), None)

        # 特殊情况：女巫自救 + 被守护
        # 女巫自救成功，无论是否被守护（不算同守同救）
        if wolf_target == witch_id and witch_save_target == witch_id:
            self.logger.info(f"女巫自救成功")
            # 检查是否有毒药目标
            deaths = []
            if witch_poison_target:
                player = self.state.players[witch_poison_target]
                player.is_alive = False
                player.death_cause = DeathCause.POISON
                deaths.append(witch_poison_target)
            return deaths

        # 同守同救 → 死亡（两股魔力冲突）
        # 注意：女巫自救 + 守卫守护女巫 → 不算同守同救
        if guard_target and witch_save_target and guard_target == witch_save_target and guard_target != witch_id:
            self.logger.info(f"同守同救：{guard_target}号 死亡（两股魔力冲突）")
            player = self.state.players[guard_target]
            player.is_alive = False
            player.death_cause = DeathCause.SAME_NIGHT_SAVE_CONFLICT
            # 不通知守卫和女巫（信息隔离）
            deaths = [guard_target]
            # 检查是否有毒药目标
            if witch_poison_target:
                player2 = self.state.players[witch_poison_target]
                player2.is_alive = False
                player2.death_cause = DeathCause.POISON
                deaths.append(witch_poison_target)
            return deaths

        # 被守护 → 不死
        if wolf_target == guard_target:
            # 检查是否有毒药目标
            deaths = []
            if witch_poison_target:
                player = self.state.players[witch_poison_target]
                player.is_alive = False
                player.death_cause = DeathCause.POISON
                deaths.append(witch_poison_target)
            return deaths

        # 被救 → 不死
        if wolf_target == witch_save_target:
            # 检查是否有毒药目标
            deaths = []
            if witch_poison_target:
                player = self.state.players[witch_poison_target]
                player.is_alive = False
                player.death_cause = DeathCause.POISON
                deaths.append(witch_poison_target)
            return deaths

        # 被刀 → 死亡
        if wolf_target:
            player = self.state.players[wolf_target]
            player.is_alive = False
            player.death_cause = DeathCause.WOLF_ATTACK
            deaths = [wolf_target]
            # 检查是否有毒药目标
            if witch_poison_target:
                player2 = self.state.players[witch_poison_target]
                player2.is_alive = False
                player2.death_cause = DeathCause.POISON
                deaths.append(witch_poison_target)
            return deaths

        # 女巫毒杀 → 死亡（独立于狼刀）
        if witch_poison_target:
            player = self.state.players[witch_poison_target]
            player.is_alive = False
            player.death_cause = DeathCause.POISON
            return [witch_poison_target]

        return []
    
    async def _run_hunter_skill(self, hunter_id: int, death_cause: DeathCause) -> Optional[int]:
        """
        猎人技能发动

        规则：
        - 被狼刀 → 可以开枪
        - 被投票 → 可以开枪
        - 被毒杀 → 取决于配置
        - 自爆 → 不能开枪
        - 决斗死亡 → 不能开枪
        - 同守同救 → 取决于配置（默认不能开枪）

        注意：配置项 hunter_can_shoot_if_same_save_conflict 与
        hunter_can_shoot_if_poisoned 逻辑独立，不存在冲突
        """
        hunter = self.state.players[hunter_id]

        # 判断是否可以开枪
        can_shoot = False
        reason = ""

        if death_cause == DeathCause.WOLF_ATTACK:
            can_shoot = True
            reason = "被狼刀死亡，可以开枪"
        elif death_cause == DeathCause.VOTE_OUT:
            can_shoot = True
            reason = "被投票放逐，可以开枪"
        elif death_cause == DeathCause.POISON:
            # 取决于配置
            if self.config.rules.get("hunter_can_shoot_if_poisoned", False):
                can_shoot = True
                reason = "被毒杀，但配置允许开枪"
            else:
                reason = "被毒杀，不能开枪"
        elif death_cause == DeathCause.SELF_EXPLODE:
            reason = "自爆，不能开枪"
        elif death_cause == DeathCause.DUEL:
            reason = "决斗死亡，不能开枪"
        elif death_cause == DeathCause.SAME_NIGHT_SAVE_CONFLICT:
            # 取决于配置（默认不能开枪）
            # 注意：此配置与 hunter_can_shoot_if_poisoned 逻辑独立
            # 同守同救是"意外死亡"，毒杀是"被女巫毒杀"，两者性质不同
            if self.config.rules.get("hunter_can_shoot_if_same_save_conflict", False):
                can_shoot = True
                reason = "同守同救，但配置允许开枪"
            else:
                reason = "同守同救，不能开枪"
        elif death_cause == DeathCause.HUNTER_SHOT:
            reason = "被猎人开枪，不能开枪"
        else:
            reason = f"未知死亡原因 {death_cause}，不能开枪"

        self.logger.info(f"猎人 {hunter_id}号：{reason}")

        if not can_shoot:
            return None

        # 猎人技能逻辑
        alive = [p.id for p in self.state.players.values()
                 if p.is_alive and p.id != hunter_id]

        if not alive:
            return None

        context = {
            "alive_players": alive,
            "death_cause": str(death_cause),
            "my_id": hunter_id
        }

        target = await self.agents[hunter_id].hunter_skill(context)

        # 验证
        if target and target not in alive:
            import random
            target = random.choice(alive) if alive else None

        if target:
            target_player = self.state.players[target]
            target_player.is_alive = False
            target_player.death_cause = DeathCause.HUNTER_SHOT

            # 检查游戏是否结束（猎人技能执行后立即检查）
            if self.state.is_game_over():
                self._end_game()

        return target
    
    async def _run_president_election(self):
        """
        警长竞选流程

        注意：警长竞选时还没有警长，所以没有权重
        """
        self.logger.info("开始警长竞选")

        candidates = []
        for player_id in self.state.get_alive_players():
            if self.agents[player_id].decide_to_run_president():
                candidates.append(player_id)

        if not candidates:
            self.logger.info("无人参选警长")
            return

        # 竞选发言
        for candidate_id in candidates:
            speech = await self.agents[candidate_id].president_speech()
            self.logger.log_event("president_candidate_speech", {
                "player_id": candidate_id,
                "content": speech
            })

        # 投票（此时没有警长，没有权重）
        votes = {}
        for voter_id in self.state.get_alive_players():
            # 获取候选人（竞选阶段的候选人）
            context = {
                "alive_players": self.state.get_alive_players(),
                "candidates": candidates,
                "previous_votes": votes.copy(),
                "my_id": voter_id
            }
            
            vote = await self.agents[voter_id].vote_for_president(candidates)
            votes[voter_id] = vote

        # 计票（没有权重）
        vote_count = {}
        for voter, candidate in votes.items():
            if candidate:
                vote_count[candidate] = vote_count.get(candidate, 0) + 1

        if vote_count:
            max_votes = max(vote_count.values())
            winners = [c for c, v in vote_count.items() if v == max_votes]

            if len(winners) == 1:
                self.state.president_id = winners[0]
                self.logger.info(f"{winners[0]}号 当选警长")
            else:
                # 平票处理：重新竞选或无人当选
                await self._handle_president_tie(winners)
        else:
            self.logger.info("无人投票，无人当选警长")
    
    async def _handle_president_tie(self, winners: List[int]):
        """
        警长竞选平票处理

        规则：
        1. 平票玩家 PK 发言
        2. 再次投票
        3. 再次平票 → 无人当选警长（警徽流失）
        """
        self.logger.info(f"警长竞选平票：{winners}")

        # PK 发言（按玩家 ID 排序）
        winners.sort()
        for candidate_id in winners:
            speech = await self.agents[candidate_id].pk_speech()
            self.logger.log_event("president_pk_speech", {
                "player_id": candidate_id,
                "content": speech
            })

        # 再次投票
        votes = {}
        for voter_id in self.state.get_alive_players():
            vote = await self.agents[voter_id].vote_for_president(winners)
            votes[voter_id] = vote

        # 计票
        vote_count = {}
        for voter, candidate in votes.items():
            if candidate:
                vote_count[candidate] = vote_count.get(candidate, 0) + 1

        if vote_count:
            max_votes = max(vote_count.values())
            winners2 = [c for c, v in vote_count.items() if v == max_votes]

            if len(winners2) == 1:
                self.state.president_id = winners2[0]
                self.logger.info(f"{winners2[0]}号 当选警长（平票后）")
            else:
                self.logger.info("再次平票，无人当选警长，警徽流失")
        else:
            self.logger.info("无人投票，无人当选警长，警徽流失")
    
    def _handle_president_death(self, president_id: int):
        """
        处理警长死亡

        规则：
        1. 警长死亡后，可以选择继承者
        2. 如果没有继承者，警徽流失（重新竞选或没有警长）
        3. 警长可以在遗言中指定继承者
        4. 警长自爆 → 没有遗言 → 不能指定继承者 → 警徽流失

        警长继承机制实现细节：
        - 警长遗言发表后，调用 make_last_words() 方法
        - 如果是警长，遗言后可以指定继承者：president.president_inherit_id = inherit_id
        - 继承者必须是存活玩家
        - 如果没有指定继承者或继承者已死亡，警徽流失
        """
        president = self.state.players.get(president_id)
        if president and not president.is_alive:
            # 检查是否有继承者
            inherit_id = president.president_inherit_id
            if inherit_id and self.state.players.get(inherit_id) and self.state.players[inherit_id].is_alive:
                # 有继承者
                self.state.president_id = inherit_id
                self.logger.info(f"警长继承：{inherit_id}号")
            else:
                # 没有继承者，警徽流失
                self.state.president_id = None
                self.logger.info("警长死亡，警徽流失")
    
    def _handle_president_inheritance(self, inherit_id: int):
        """
        处理警长继承

        Args:
            inherit_id: 继承者ID
        """
        if inherit_id and self.state.players.get(inherit_id) and self.state.players[inherit_id].is_alive:
            self.state.president_id = inherit_id
            self.logger.info(f"警长遗言指定继承：{inherit_id}号")
        else:
            self.state.president_id = None
            self.logger.info("警长遗言指定的继承者无效，警徽流失")
    
    def _end_game(self):
        """
        结束游戏
        """
        self.state.game_over = True
        self.logger.info(f"游戏结束！获胜方：{self.state.winner}，原因：{self.state.reason}")
        
        # 记录游戏结果
        result_details = {
            "winner": self.state.winner,
            "reason": self.state.reason,
            "day_number": self.state.day_number,
            "night_number": self.state.night_number,
            "remaining_players": self.state.get_alive_players(),
            "final_roles": {pid: player.role.value for pid, player in self.state.players.items()}
        }
        
        self.logger.log_result(f"Game Over - {self.state.winner} win", result_details)
        
        # 如果有 TTS，播报结果
        if self.tts:
            self.tts.speak(f"游戏结束！{self.state.winner}阵营获得胜利！")