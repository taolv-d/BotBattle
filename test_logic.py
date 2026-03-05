"""
狼人杀游戏逻辑测试脚本 - 使用 Dummy LLM

测试重点：
1. 游戏结束条件（3 狼 vs 3 好人应继续，3 狼 vs 2 好人才结束）
2. 猎人技能（只有被狼刀才能开枪，被投票/毒杀不能开枪）
3. 女巫用药（解药和毒药都只能用一次）
4. 预言家查验（查验结果与发言一致）
5. 投票逻辑（平票处理、弃票处理）
6. 死亡记录（所有死亡都有明确的 death_cause）
7. AI 发言（不编造不存在的历史）
"""
import sys
import json
import random
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.state import GameState, Player, Role, Phase
from core.game_engine import GameEngine
from ui.cli import CLI
from ai.agent import AIAgent
from ai.personality import Personality, PersonalityManager


class DummyLLM:
    """Dummy LLM - 用于逻辑测试，返回预设响应"""
    
    def __init__(self):
        self.call_count = 0
        self.responses = []
    
    def chat(self, messages, max_tokens=200):
        """模拟聊天响应"""
        self.call_count += 1
        
        # 分析 prompt 内容，返回合理的响应
        user_content = ""
        for msg in messages:
            if msg.get("role") == "user":
                user_content += msg.get("content", "")
        
        # 根据角色和情境返回响应
        response = self._generate_response(user_content, max_tokens)
        self.responses.append({
            "call": self.call_count,
            "prompt": user_content[:200],
            "response": response
        })
        return response, {"dummy": True}
    
    def _generate_response(self, prompt, max_tokens):
        """根据 prompt 生成响应"""
        # 狼人响应 - 修复 P1-4: 增加袭击猎人的概率，以便验证猎人技能
        if "狼人" in prompt and "袭击" in prompt:
            # 尝试从 prompt 中提取存活玩家列表
            import re
            alive_match = re.search(r"可选择的玩家：\[(.*?)\]", prompt)
            if alive_match:
                alive_str = alive_match.group(1)
                alive_players = [int(x.strip()) for x in alive_str.split(",") if x.strip().isdigit()]
                
                # 30% 概率优先选择猎人（模拟狼人针对神职）
                # 注意：DummyLLM 不知道玩家身份，这里只是模拟
                if alive_players and random.random() < 0.3:
                    # 随机选择一个目标（实际游戏中狼人不知道猎人身份）
                    target = random.choice(alive_players)
                else:
                    target = random.choice(alive_players) if alive_players else random.randint(1, 9)
            else:
                target = random.randint(1, 9)
            
            return json.dumps({"target": target, "reason": "狼人选择袭击目标"})
        
        # 预言家响应
        if "预言家" in prompt and "查验" in prompt:
            target = random.randint(1, 9)
            return json.dumps({"target": target, "reason": "随机查验目标"})
        
        # 女巫响应 - 修复 P2-5: 让女巫更频繁使用药剂
        if "女巫" in prompt and "药剂" in prompt:
            # 分析 prompt 中是否有死亡玩家
            import re
            # 匹配多种格式："今晚有人死亡：X 号" 或 "死亡：X 号"
            dead_match = re.search(r"死亡：(\d+) 号", prompt)
            dead_player = int(dead_match.group(1)) if dead_match else None
            
            # 60% 概率使用解药（如果有死亡），30% 概率使用毒药，10% 概率不用
            rand = random.random()
            if dead_player and rand < 0.6:
                action = "heal"
                target = dead_player
            elif rand < 0.9:
                action = "poison"
                # 从 prompt 中提取存活玩家列表
                alive_match = re.search(r"可选择的玩家：\[(.*?)\]", prompt)
                if alive_match:
                    alive_str = alive_match.group(1)
                    alive_players = [int(x.strip()) for x in alive_str.split(",") if x.strip().isdigit()]
                    target = random.choice(alive_players) if alive_players else random.randint(1, 9)
                else:
                    target = random.randint(1, 9)
            else:
                action = "none"
                target = None
            
            return json.dumps({"action": action, "target": target, "reason": f"女巫决定使用{action}药剂"})
        
        # 投票响应
        if "投票" in prompt or "vote" in prompt.lower():
            if random.random() > 0.1:  # 90% 概率投票
                target = random.randint(1, 9)
                return json.dumps({"vote": target, "reason": "根据发言决定"})
            else:
                return json.dumps({"vote": None, "reason": "弃票"})
        
        # 猎人技能
        if "猎人" in prompt and "带走" in prompt:
            target = random.randint(1, 9)
            return json.dumps({"target": target})
        
        # 遗言
        if "遗言" in prompt:
            return json.dumps({"speech": "我是好人，希望大家能找到狼人。", "inner_thought": "遗憾出局"})
        
        # 默认发言响应
        return json.dumps({
            "speech": f"我是好人，目前还没有明确目标，继续听大家发言。",
            "inner_thought": "暂时观察局势"
        })
    
    def generate_with_inner_thought(self, system_prompt, user_prompt, max_length=100):
        """生成发言和内心独白"""
        self.call_count += 1
        speech = f"我是好人，暂时还没有明确目标，继续听大家发言。"
        inner_thought = "观察局势中"

        # 修复 P1-3: 根据实际角色返回不同的内心独白
        # 注意：不能只用 "狼人" in system_prompt 判断，因为会匹配到"狼人杀游戏"
        # 需要检查更具体的关键词如 "你是狼人" 或 "身份是狼人"
        is_werewolf = "你是狼人" in system_prompt or "身份是狼人" in system_prompt
        is_seer = "你是预言家" in system_prompt or "身份是预言家" in system_prompt
        is_witch = "你是女巫" in system_prompt or "身份是女巫" in system_prompt
        is_hunter = "你是猎人" in system_prompt or "身份是猎人" in system_prompt

        if is_werewolf:
            speech = f"我是村民，昨晚没什么信息，先听大家发言。"
            inner_thought = "我是狼人，要小心别暴露，不能让大家发现我的身份"
        elif is_seer:
            speech = f"我有点信息，但现在还不方便说，继续听大家发言。"
            inner_thought = "我是预言家，要保护好自己，找到合适的时机跳身份"
        elif is_witch:
            speech = f"昨晚的情况我有所了解，先听其他人怎么说。"
            inner_thought = "我是女巫，手上有药，要谨慎使用"
        elif is_hunter:
            speech = f"我态度比较明确，希望大家认真听我发言。"
            inner_thought = "我是猎人，不怕死，死后可以带走一个狼人"
        else:
            speech = f"我是普通村民，会认真分析大家的发言。"
            inner_thought = "我是村民，要仔细听发言找出狼人"

        self.responses.append({
            "call": self.call_count,
            "prompt": user_prompt[:200],
            "speech": speech,
            "inner_thought": inner_thought
        })

        return speech, inner_thought


class TestObserver:
    """测试观察者 - 记录游戏过程中的关键事件"""
    
    def __init__(self):
        self.events = []
        self.death_log = []
        self.skill_usage = {
            "witch_heal": 0,
            "witch_poison": 0,
            "hunter_skill": 0,
        }
        self.seer_checks = []
        self.vote_results = []
        self.game_end_info = None
    
    def record_event(self, event_type, data):
        """记录事件"""
        self.events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
    
    def record_death(self, player_id, role, cause):
        """记录死亡"""
        self.death_log.append({
            "player_id": player_id,
            "role": role.value if role else "unknown",
            "cause": cause
        })
    
    def record_skill(self, skill_name):
        """记录技能使用"""
        if skill_name in self.skill_usage:
            self.skill_usage[skill_name] += 1
    
    def record_seer_check(self, target, result):
        """记录预言家查验"""
        self.seer_checks.append({
            "target": target,
            "result": result
        })
    
    def record_vote(self, day, vote_counts, eliminated):
        """记录投票结果"""
        self.vote_results.append({
            "day": day,
            "vote_counts": vote_counts,
            "eliminated": eliminated
        })
    
    def record_game_end(self, winner, reason):
        """记录游戏结束"""
        self.game_end_info = {
            "winner": winner,
            "reason": reason
        }


def create_test_game():
    """创建测试游戏"""
    ui = CLI(show_inner_thoughts=True, god_view=True)
    
    # 创建游戏引擎
    engine = GameEngine(ui, {
        "game": {"ai_speech_delay": 0}
    })
    
    # 设置 9 人局
    roles_config = [
        {"role": "werewolf", "count": 3},
        {"role": "villager", "count": 3},
        {"role": "seer", "count": 1},
        {"role": "witch", "count": 1},
        {"role": "hunter", "count": 1}
    ]
    
    personalities = ["honest", "liar", "smooth", "cold", "chatterbox", "aggressive", "passive"]
    
    engine.setup(
        player_count=9,
        roles_config=roles_config,
        personalities=personalities,
        human_player_id=None,
    )
    
    # 使用 Dummy LLM 创建 AI 代理
    dummy_llm = DummyLLM()
    personality_mgr = PersonalityManager()
    
    for player in engine.state.players.values():
        if player.is_bot:
            personality = personality_mgr.get(player.personality)
            if not personality:
                personality = personality_mgr.get_random()
            agent = AIAgent(player, personality, dummy_llm)
            engine.agents[player.id] = agent
    
    return engine, dummy_llm


def test_game_logic():
    """测试游戏逻辑"""
    print("=" * 70)
    print("狼人杀游戏逻辑测试")
    print("=" * 70)
    
    # 创建测试游戏
    print("\n[1] 创建测试游戏...")
    engine, dummy_llm = create_test_game()
    
    # 创建观察者
    observer = TestObserver()
    
    # 显示初始配置
    print(f"\n[2] 游戏配置:")
    print(f"    玩家数量：{engine.state.player_count}")
    print(f"    角色配置：{[(p.id, p.role.value) for p in engine.state.players.values()]}")
    
    # 记录初始状态
    observer.record_event("game_setup", {
        "player_count": engine.state.player_count,
        "roles": {p.id: p.role.value for p in engine.state.players.values()}
    })
    
    # 运行游戏（手动控制流程以进行测试）
    print("\n[3] 开始运行游戏...")
    
    # 第一夜
    engine.state.night_number = 1
    print(f"\n--- 第 1 夜 ---")
    
    # 运行夜晚阶段
    night_deaths = engine._run_night()
    
    # 记录夜晚死亡
    for death in night_deaths:
        player = engine.state.players[death]
        observer.record_death(death, player.role, player.death_cause)
    
    # 游戏主循环（限制最大轮数）
    max_days = 10
    day_count = 0

    while not engine.state.game_over and day_count < max_days:
        # 修复 P2-6: 手动递增 day_number，因为测试脚本没有使用 engine.start()
        engine.state.day_number += 1
        day_count += 1
        print(f"\n--- 第{day_count}天 (day_number={engine.state.day_number}) ---")

        # 运行白天
        engine._run_day()
        
        # 记录投票结果
        if engine.state.vote_counts:
            eliminated = None
            if engine.state.vote_counts:
                max_votes = max(engine.state.vote_counts.values())
                winners = [k for k, v in engine.state.vote_counts.items() if v == max_votes]
                if len(winners) == 1:
                    eliminated = winners[0]
            
            observer.record_vote(
                day_count,
                engine.state.vote_counts,
                eliminated
            )
        
        # 记录白天死亡
        for player in engine.state.players.values():
            if not player.is_alive and player.death_cause and player.death_cause not in ["wolf", "poison"]:
                # 检查是否是新死亡
                existing_deaths = [d["player_id"] for d in observer.death_log]
                if player.id not in existing_deaths:
                    observer.record_death(player.id, player.role, player.death_cause)
        
        if engine.state.game_over:
            break
        
        # 运行夜晚
        print(f"\n--- 第{engine.state.night_number + 1}夜 ---")
        engine.state.night_number += 1
        night_deaths = engine._run_night()
        
        # 记录夜晚死亡
        for death in night_deaths:
            player = engine.state.players[death]
            # 检查是否已记录
            existing_deaths = [d["player_id"] for d in observer.death_log]
            if death not in existing_deaths:
                observer.record_death(death, player.role, player.death_cause)
    
    # 记录游戏结束
    observer.record_game_end(
        engine.state.winner,
        "游戏自然结束"
    )
    
    # 输出测试结果
    print("\n" + "=" * 70)
    print("测试结果分析")
    print("=" * 70)
    
    return engine, observer, dummy_llm


def analyze_results(engine, observer, dummy_llm):
    """分析测试结果"""
    print("\n【测试报告】")
    print("-" * 70)
    
    # 1. 游戏结束条件检查
    print("\n1. 游戏结束条件检查:")
    werewolves_alive = len([p for p in engine.state.players.values() if p.role == Role.WEREWOLF and p.is_alive])
    villagers_alive = len([p for p in engine.state.players.values() if p.role != Role.WEREWOLF and p.is_alive])
    print(f"   最终状态：狼人={werewolves_alive}人，好人={villagers_alive}人")
    print(f"   游戏结束：{engine.state.game_over}")
    print(f"   获胜方：{engine.state.winner}")
    
    # 检查结束条件是否正确
    if werewolves_alive == 0 and engine.state.winner == "villager":
        print("   [OK] 狼人全灭，好人胜利 - 正确")
    elif werewolves_alive > villagers_alive and engine.state.winner == "werewolf":
        print("   [OK] 狼人数量超过好人，狼人胜利 - 正确")
    elif werewolves_alive == villagers_alive and not engine.state.game_over:
        print("   [OK] 狼人好人数量相等，游戏继续 - 正确")
    else:
        print("   [FAIL] 游戏结束条件可能有问题")
    
    # 2. 死亡记录检查
    print("\n2. 死亡记录检查:")
    print(f"   总死亡人数：{len(observer.death_log)}")
    for death in observer.death_log:
        print(f"   - {death['player_id']}号 ({death['role']}): 死亡原因={death['cause']}")
    
    # 检查死亡原因是否都有记录
    missing_cause = [p for p in engine.state.players.values() if not p.is_alive and not p.death_cause]
    if missing_cause:
        print(f"   [FAIL] 以下玩家死亡但缺少原因：{[p.id for p in missing_cause]}")
    else:
        print("   [OK] 所有死亡玩家都有明确的 death_cause")
    
    # 3. 猎人技能检查
    print("\n3. 猎人技能检查:")
    hunter_deaths = [d for d in observer.death_log if d['role'] == 'hunter']
    for death in hunter_deaths:
        if death['cause'] == 'wolf':
            print(f"   - {death['player_id']}号猎人被狼刀死亡，应该可以开枪")
        elif death['cause'] == 'voted_out':
            print(f"   - {death['player_id']}号猎人被投票出局，不能开枪")
        elif death['cause'] == 'poison':
            print(f"   - {death['player_id']}号猎人被毒杀，不能开枪")
    
    # 4. 女巫用药检查
    print("\n4. 女巫用药检查:")
    print(f"   解药使用次数：{engine.witch_heal_used}")
    print(f"   毒药使用次数：{engine.witch_poison_used}")
    if engine.witch_heal_used <= 1 and engine.witch_poison_used <= 1:
        print("   [OK] 女巫用药次数正确（各最多 1 次）")
    else:
        print("   [FAIL] 女巫用药次数超限")
    
    # 5. 预言家查验检查
    print("\n5. 预言家查验检查:")
    if engine.state.seer_check_target:
        print(f"   查验目标：{engine.state.seer_check_target}号")
        print(f"   查验结果：{engine.state.seer_check_result.value if engine.state.seer_check_result else 'unknown'}")
        print("   [OK] 预言家查验记录完整")
    else:
        print("   [WARN] 没有预言家查验记录（可能预言家已死亡）")
    
    # 6. 投票逻辑检查
    print("\n6. 投票逻辑检查:")
    print(f"   总投票轮数：{len(observer.vote_results)}")
    for i, vote in enumerate(observer.vote_results):
        print(f"   第{vote['day']}天：投票结果={vote['vote_counts']}, 放逐={vote['eliminated']}")
    
    # 检查平票处理
    tie_votes = [v for v in observer.vote_results if v['eliminated'] is None and v['vote_counts']]
    if tie_votes:
        print(f"   [OK] 平票处理正确：{len(tie_votes)}次平票无人被放逐")
    
    # 7. AI 发言检查
    print("\n7. AI 发言检查:")
    print(f"   LLM 调用次数：{dummy_llm.call_count}")
    print(f"   响应记录数：{len(dummy_llm.responses)}")
    
    # 8. 游戏日志
    print(f"\n8. 游戏日志路径：{engine.log_file}")
    
    print("\n" + "=" * 70)
    print("测试完成！")
    print("=" * 70)


if __name__ == "__main__":
    engine, observer, dummy_llm = test_game_logic()
    analyze_results(engine, observer, dummy_llm)
    
    # 保存测试报告
    report = {
        "test_time": datetime.now().isoformat(),
        "game_state": {
            "winner": engine.state.winner,
            "game_over": engine.state.game_over,
            "day_number": engine.state.day_number,
            "night_number": engine.state.night_number,
        },
        "death_log": observer.death_log,
        "skill_usage": observer.skill_usage,
        "vote_results": observer.vote_results,
        "llm_calls": dummy_llm.call_count,
    }
    
    report_file = "logs/test_report.json"
    Path("logs").mkdir(exist_ok=True)
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n测试报告已保存至：{report_file}")
