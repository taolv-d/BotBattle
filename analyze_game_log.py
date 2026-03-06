"""分析狼人杀游戏日志，检测潜在 Bug"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def analyze_game_log(log_path: str) -> dict:
    """分析游戏日志，检测问题"""
    
    with open(log_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    state = data.get('state', {})
    history = data.get('history', [])
    
    issues = []
    warnings = []
    stats = {
        'total_days': state.get('day_number', 0),
        'total_nights': state.get('night_number', 0),
        'game_over': state.get('game_over', False),
        'winner': state.get('winner', 'unknown'),
        'player_count': state.get('player_count', 0),
        'events_count': len(history),
    }
    
    # 统计各身份玩家
    players = state.get('players', {})
    roles_count = {'werewolf': 0, 'villager': 0, 'seer': 0, 'witch': 0, 'hunter': 0}
    for p in players.values():
        role = p.get('role', 'unknown')
        if role in roles_count:
            roles_count[role] += 1
    
    stats['roles_distribution'] = roles_count
    
    # 检测问题
    
    # 1. 检查是否有玩家被重复查验
    seer_checks = [e for e in history if e.get('type') == 'seer_check']
    checked_targets = [e['data'].get('target') for e in seer_checks]
    if len(checked_targets) != len(set(checked_targets)):
        warnings.append(f"预言家重复查验了同一玩家：{checked_targets}")
    
    # 2. 检查是否有玩家死后还发言
    dead_players = set()
    speech_events = [e for e in history if e.get('type') in ['president_speech', 'inner_thought']]
    for event in history:
        if event.get('type') in ['player_eliminated', 'night_death']:
            dead_players.add(event['data'].get('player_id'))
    
    for event in speech_events:
        player_id = event['data'].get('player_id')
        if player_id in dead_players:
            # 遗言是允许的
            if event.get('type') != 'last_words':
                issues.append(f"玩家 {player_id} 已死亡但仍然发言/有内心独白")
    
    # 3. 检查投票是否投给了死亡玩家
    vote_events = [e for e in history if e.get('type') == 'day_vote']
    for event in vote_events:
        alive_at_vote = event['data'].get('alive_players', [])
        vote_details = event['data'].get('vote_details', {})
        for voter, target in vote_details.items():
            if target and target not in alive_at_vote:
                warnings.append(f"玩家 {voter} 投票给了已死亡的玩家 {target}")
    
    # 4. 检查女巫是否使用超过一次解药/毒药
    witch_actions = [e for e in history if e.get('type') == 'night_actions_summary']
    heal_count = 0
    poison_count = 0
    for event in witch_actions:
        action = event['data'].get('witch_action', {})
        if action.get('action') == 'heal':
            heal_count += 1
        elif action.get('action') == 'poison':
            poison_count += 1
    
    if heal_count > 1:
        issues.append(f"女巫使用了解药 {heal_count} 次 (应该最多 1 次)")
    if poison_count > 1:
        issues.append(f"女巫使用了毒药 {poison_count} 次 (应该最多 1 次)")
    
    # 5. 检查预言家查验结果是否一致
    seer_results = {}
    for event in seer_checks:
        target = event['data'].get('target')
        result = event['data'].get('result')
        if target in seer_results and seer_results[target] != result:
            issues.append(f"预言家对玩家 {target} 的查验结果不一致：{seer_results[target]} vs {result}")
        seer_results[target] = result
    
    # 6. 检查是否有狼人自爆
    wolf_players = [pid for pid, p in players.items() if p.get('role') == 'werewolf']
    eliminated_players = [e['data'].get('player_id') for e in history if e.get('type') == 'player_eliminated']
    for pid in eliminated_players:
        if str(pid) in wolf_players:
            warnings.append(f"狼人 {pid} 号被放逐")
    
    # 7. 检查猎人是否正确发动技能
    hunter_events = [e for e in history if e.get('type') == 'hunter_skill']
    for event in hunter_events:
        hunter_id = event['data'].get('hunter_id')
        target = event['data'].get('target')
        if not target:
            warnings.append(f"猎人 {hunter_id} 号未发动技能")
        else:
            # 检查猎人是否被狼刀
            hunter_death = next((e for e in history 
                                if e.get('type') == 'night_death' and e['data'].get('player_id') == hunter_id), None)
            if hunter_death:
                pass  # 猎人是被狼刀的，可以发动技能
            else:
                warnings.append(f"猎人 {hunter_id} 号可能不是被狼刀死亡，技能发动可能有问题")
    
    # 8. 检查游戏结束条件
    game_over_events = [e for e in history if e.get('type') == 'game_over']
    if not game_over_events:
        warnings.append("游戏没有明确的结束事件")
    else:
        winner = game_over_events[0]['data'].get('winner')
        # 检查获胜条件是否正确
        alive_wolves = sum(1 for pid, p in players.items() if p.get('role') == 'werewolf' and p.get('is_alive'))
        alive_villagers = sum(1 for pid, p in players.items() if p.get('role') in ['villager', 'seer', 'witch', 'hunter'] and p.get('is_alive'))
        
        if winner == 'werewolf' and alive_wolves < alive_villagers:
            issues.append(f"狼人获胜但存活狼人 ({alive_wolves}) 少于存活好人 ({alive_villagers})")
        elif winner == 'village' and alive_wolves >= alive_villagers:
            issues.append(f"好人获胜但存活狼人 ({alive_wolves}) 不少于存活好人 ({alive_villagers})")
    
    # 9. 检查是否有玩家身份暴露错误
    last_words_events = [e for e in history if e.get('type') == 'last_words']
    for event in last_words_events:
        player_id = event['data'].get('player_id')
        words = event['data'].get('words', '')
        player_role = players.get(str(player_id), {}).get('role', 'unknown')
        
        # 检查遗言中是否透露了错误的身份
        if '我是村民' in words and player_role != 'villager':
            warnings.append(f"玩家 {player_id} 遗言声称是村民但实际是 {player_role}")
        if '我是狼人' in words and player_role != 'werewolf':
            warnings.append(f"玩家 {player_id} 遗言声称是狼人但实际是 {player_role}")
    
    # 10. 检查平票情况处理
    president_election_events = [e for e in history if e.get('type') == 'president_election_end']
    for event in president_election_events:
        reason = event['data'].get('reason', '')
        if reason == 'no_votes' or reason == 'tie':
            warnings.append(f"警长竞选失败：{reason}")
    
    stats['issues'] = issues
    stats['warnings'] = warnings
    
    return stats


def generate_report(stats: dict, log_path: str) -> str:
    """生成测试报告"""
    report = []
    report.append("=" * 60)
    report.append("🎮 狼人杀游戏测试报告")
    report.append("=" * 60)
    report.append(f"\n日志文件：{log_path}")
    report.append(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    report.append("\n📊 游戏统计")
    report.append("-" * 40)
    report.append(f"玩家数量：{stats['player_count']}人")
    report.append(f"游戏天数：{stats['total_days']}天")
    report.append(f"游戏夜数：{stats['total_nights']}夜")
    report.append(f"总事件数：{stats['events_count']}个")
    report.append(f"游戏结束：{'是' if stats['game_over'] else '否'}")
    report.append(f"获胜方：{stats['winner']}")
    
    report.append("\n🎭 身份分布")
    report.append("-" * 40)
    for role, count in stats['roles_distribution'].items():
        role_name = {'werewolf': '狼人', 'villager': '村民', 'seer': '预言家', 'witch': '女巫', 'hunter': '猎人'}.get(role, role)
        report.append(f"  {role_name}: {count}人")
    
    if stats['issues']:
        report.append("\n❌ 发现的问题")
        report.append("-" * 40)
        for i, issue in enumerate(stats['issues'], 1):
            report.append(f"  [{i}] {issue}")
    
    if stats['warnings']:
        report.append("\n⚠️  警告信息")
        report.append("-" * 40)
        for i, warning in enumerate(stats['warnings'], 1):
            report.append(f"  [{i}] {warning}")
    
    if not stats['issues'] and not stats['warnings']:
        report.append("\n✅ 未发现问题")
    
    report.append("\n" + "=" * 60)
    report.append(f"总结：{len(stats['issues'])} 个问题，{len(stats['warnings'])} 个警告")
    report.append("=" * 60)
    
    return "\n".join(report)


def main():
    """主函数"""
    # 查找最新的日志文件
    logs_dir = Path(__file__).parent / "logs"
    log_files = sorted(logs_dir.glob("game_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not log_files:
        print("❌ 未找到游戏日志文件")
        return 1
    
    # 分析所有日志
    all_stats = []
    for latest_log in log_files:
        print(f"\n{'=' * 60}")
        stats = analyze_game_log(str(latest_log))
        all_stats.append((str(latest_log), stats))
    
    # 生成报告
    for log_path, stats in all_stats:
        report = generate_report(stats, log_path)
        print(report)
    
    # 保存报告
    report_path = Path(__file__).parent / "test_reports" / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 报告已保存至：{report_path}")
    
    # 返回是否有问题
    return 0 if not stats['issues'] else 1


if __name__ == "__main__":
    sys.exit(main())
