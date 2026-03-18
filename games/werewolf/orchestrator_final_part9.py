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