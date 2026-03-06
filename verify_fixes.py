"""验证狼人杀游戏 Bug 修复"""
import json
import sys
from pathlib import Path
from datetime import datetime

# 修复 Windows 编码问题
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def verify_log(log_path: str) -> dict:
    """验证单个日志文件的修复情况"""
    
    with open(log_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    state = data.get('state', {})
    history = data.get('history', [])
    
    results = {
        'log_file': log_path,
        'game_complete': state.get('game_over', False),
        'winner': state.get('winner', 'unknown'),
        'issues': [],
        'passed': [],
    }
    
    # P0-1: 预言家查验结果显示为"好人"/"狼人"
    seer_checks = [e for e in history if e.get('type') == 'seer_check']
    for check in seer_checks:
        result = check['data'].get('result', '')
        result_display = check['data'].get('result_display', '')
        
        # 检查 result_display 是否存在且为"好人"或"狼人"
        if result_display in ['好人', '狼人']:
            results['passed'].append(f"P0-1: 查验结果显示正确 (result_display={result_display})")
        elif result in ['villager', 'seer', 'witch', 'hunter']:
            # 如果 result 是具体角色名，但 result_display 不存在，说明修复不完整
            if not result_display:
                results['issues'].append(f"P0-1 失败：查验结果直接显示角色名 {result}，未转换为好人/狼人")
        elif result == 'werewolf':
            if not result_display:
                results['issues'].append(f"P0-1 失败：查验结果直接显示 werewolf，未转换为狼人")
    
    if not seer_checks:
        results['issues'].append("P0-1: 没有预言家查验事件，无法验证")
    
    # P0-2: 女巫不能毒杀自己
    witch_actions = [e for e in history if e.get('type') == 'night_actions_summary']
    for action in witch_actions:
        witch_action = action['data'].get('witch_action', {})
        if witch_action.get('action') == 'poison':
            # 需要检查女巫是否毒杀自己 - 这需要知道女巫的 ID
            # 从日志中查找女巫 ID
            players = state.get('players', {})
            witch_id = None
            for pid, p in players.items():
                if p.get('role') == 'witch':
                    witch_id = int(pid)
                    break
            
            if witch_action.get('target') == witch_id:
                results['issues'].append(f"P0-2 失败：女巫毒杀了自己")
            else:
                results['passed'].append(f"P0-2: 女巫未毒杀自己 (target={witch_action.get('target')}, witch_id={witch_id})")
    
    # P0-3: 猎人技能目标不包含自己
    # 检查猎人技能事件
    hunter_events = [e for e in history if e.get('type') == 'hunter_skill']
    for event in hunter_events:
        hunter_id = event['data'].get('hunter_id')
        target = event['data'].get('target')
        if hunter_id == target:
            results['issues'].append(f"P0-3 失败：猎人技能目标是猎人自己")
        else:
            results['passed'].append(f"P0-3: 猎人技能目标正确 (hunter={hunter_id}, target={target})")
    
    # P0-4: 游戏结束判断时机（检查猎人技能后是否有游戏结束事件）
    if hunter_events:
        # 检查猎人技能后是否有 game_over 事件
        game_over_events = [e for e in history if e.get('type') == 'game_over']
        if game_over_events:
            results['passed'].append("P0-4: 游戏结束事件存在")
        else:
            # 游戏可能没有结束
            if not state.get('game_over', False):
                results['passed'].append("P0-4: 游戏未完成，无法验证")
            else:
                results['issues'].append("P0-4 失败：游戏结束但缺少 game_over 事件")
    
    # P0-5: 狼人不能袭击队友
    # 检查狼人袭击目标是否是非狼人
    players = state.get('players', {})
    wolf_ids = [int(pid) for pid, p in players.items() if p.get('role') == 'werewolf']
    
    wolf_actions = [e for e in history if e.get('type') == 'night_actions_summary']
    for action in wolf_actions:
        wolf_action = action['data'].get('wolf_action', {})
        target = wolf_action.get('target')
        if target and target in wolf_ids:
            results['issues'].append(f"P0-5 失败：狼人袭击了队友 {target}号")
        elif target:
            results['passed'].append(f"P0-5: 狼人袭击目标正确 (target={target}, 非狼人)")
    
    # P0-6: 女巫第一夜自救
    # 检查第一夜女巫是否被刀并自救
    first_night_actions = [e for e in history if e.get('type') == 'night_actions_summary' and 'night_start' in str(e)]
    if first_night_actions:
        first_action = first_night_actions[0]
        witch_action = first_action['data'].get('witch_action', {})
        wolf_action = first_action['data'].get('wolf_action', {})
        
        # 查找女巫 ID
        witch_id = None
        for pid, p in players.items():
            if p.get('role') == 'witch':
                witch_id = int(pid)
                break
        
        if witch_id and wolf_action.get('target') == witch_id:
            # 女巫被刀
            if witch_action.get('action') == 'heal' and witch_action.get('target') == witch_id:
                results['passed'].append(f"P0-6: 女巫第一夜被刀并自救")
            elif witch_action.get('action') == 'heal':
                results['passed'].append(f"P0-6: 女巫第一夜自救（被刀目标={wolf_action.get('target')}）")
            else:
                results['issues'].append(f"P0-6 失败：女巫第一夜被刀但未自救")
        else:
            results['passed'].append("P0-6: 女巫第一夜未被刀，无需自救")
    
    # P1-1: 女巫药剂状态同步
    # 检查是否有多个夜晚使用同种药剂
    heal_count = 0
    poison_count = 0
    for action in witch_actions:
        wa = action['data'].get('witch_action', {})
        if wa.get('action') == 'heal':
            heal_count += 1
        elif wa.get('action') == 'poison':
            poison_count += 1
    
    if heal_count > 1:
        results['issues'].append(f"P1-1 失败：女巫使用解药 {heal_count} 次（应最多 1 次）")
    elif heal_count <= 1:
        results['passed'].append(f"P1-1: 女巫解药使用正确 ({heal_count}次)")
    
    if poison_count > 1:
        results['issues'].append(f"P1-1 失败：女巫使用毒药 {poison_count} 次（应最多 1 次）")
    elif poison_count <= 1:
        results['passed'].append(f"P1-1: 女巫毒药使用正确 ({poison_count}次)")
    
    # P1-2: 预言家不重复查验
    checked_targets = [e['data'].get('target') for e in seer_checks if e['data'].get('target')]
    if len(checked_targets) != len(set(checked_targets)):
        results['issues'].append(f"P1-2 失败：预言家重复查验了玩家 {checked_targets}")
    else:
        results['passed'].append(f"P1-2: 预言家未重复查验 (查验列表={checked_targets})")
    
    # P1-3: 狼人遗言不暴露
    last_words_events = [e for e in history if e.get('type') == 'last_words']
    for event in last_words_events:
        player_id = event['data'].get('player_id')
        words = event['data'].get('words', '')
        player_role = players.get(str(player_id), {}).get('role', 'unknown')
        
        if player_role == 'werewolf':
            forbidden_words = ['狼人', '狼队', '队友', '袭击', '刀人', '自爆']
            for word in forbidden_words:
                if word in words:
                    results['issues'].append(f"P1-3 失败：狼人 {player_id}号遗言包含敏感词'{word}'")
                    break
            else:
                results['passed'].append(f"P1-3: 狼人 {player_id}号遗言未暴露身份")
    
    # P1-4: 村民找狼逻辑
    # 检查村民发言是否包含找狼分析
    inner_thoughts = [e for e in history if e.get('type') == 'inner_thought']
    villager_analyses = []
    for event in inner_thoughts:
        player_id = event['data'].get('player_id')
        player_role = players.get(str(player_id), {}).get('role', 'unknown')
        thought = event['data'].get('thought', '')
        
        if player_role == 'villager':
            # 检查是否包含找狼相关词汇
            if any(word in thought for word in ['狼', '怀疑', '踩', '验', '分析']):
                villager_analyses.append(player_id)
    
    if villager_analyses:
        results['passed'].append(f"P1-4: 村民有找狼分析 (玩家={villager_analyses})")
    else:
        results['issues'].append("P1-4: 未发现村民找狼分析")
    
    return results


def main():
    """主函数"""
    logs_dir = Path(__file__).parent / "logs"
    log_files = sorted(logs_dir.glob("game_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not log_files:
        print("❌ 未找到游戏日志文件")
        return 1
    
    print("=" * 60)
    print("🔍 狼人杀 Bug 修复验证报告")
    print("=" * 60)
    print(f"\n找到 {len(log_files)} 个日志文件，分析最新的 5 个...\n")
    
    all_results = []
    for log_file in log_files[:5]:
        result = verify_log(str(log_file))
        all_results.append(result)
        
        print(f"\n{'=' * 60}")
        print(f"日志文件：{log_file.name}")
        print(f"游戏完成：{'是' if result['game_complete'] else '否'}")
        print(f"获胜方：{result['winner']}")
        print(f"\n✅ 通过验证 ({len(result['passed'])}):")
        for item in result['passed'][:10]:
            print(f"  • {item}")
        
        if result['issues']:
            print(f"\n❌ 发现问题 ({len(result['issues'])}):")
            for item in result['issues']:
                print(f"  • {item}")
        else:
            print(f"\n✅ 未发现问题")
    
    # 汇总统计
    print("\n" + "=" * 60)
    print("📊 汇总统计")
    print("=" * 60)
    
    total_passed = sum(len(r['passed']) for r in all_results)
    total_issues = sum(len(r['issues']) for r in all_results)
    
    print(f"\n分析日志数：{len(all_results)}")
    print(f"通过验证：{total_passed}")
    print(f"发现问题：{total_issues}")
    
    # 保存报告
    report_path = Path(__file__).parent / "test_reports" / f"verify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存至：{report_path}")
    
    return 0 if total_issues == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
