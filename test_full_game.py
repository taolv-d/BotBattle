"""完整狼人杀游戏测试 - 上帝模式"""
import sys
import os
import json
import traceback
from pathlib import Path

# 修复 Windows 编码问题
if sys.platform == 'win32':
    os.system('chcp 65001 >nul')
    sys.stdout.reconfigure(encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigManager
from ui.cli import CLI
from core.game_engine import GameEngine
from ai.agent import AIAgent
from ai.personality import PersonalityManager
from ai.llm_client import LLMClient


class TestReporter:
    """测试报告生成器"""
    
    def __init__(self):
        self.events = []
        self.errors = []
        self.warnings = []
        
    def log_event(self, event_type: str, data: dict):
        self.events.append({"type": event_type, "data": data})
        
    def log_error(self, error: str, context: dict = None):
        self.errors.append({"error": error, "context": context or {}})
        
    def log_warning(self, warning: str):
        self.warnings.append(warning)
        
    def generate_report(self) -> str:
        report = []
        report.append("=" * 60)
        report.append("🎮 狼人杀游戏测试报告")
        report.append("=" * 60)
        
        report.append(f"\n📊 总事件数：{len(self.events)}")
        report.append(f"⚠️  警告数：{len(self.warnings)}")
        report.append(f"❌ 错误数：{len(self.errors)}")
        
        if self.errors:
            report.append("\n" + "=" * 60)
            report.append("❌ 错误详情")
            report.append("=" * 60)
            for i, err in enumerate(self.errors, 1):
                report.append(f"\n[错误 {i}]")
                report.append(f"错误信息：{err['error']}")
                if err.get('context'):
                    report.append(f"上下文：{json.dumps(err['context'], ensure_ascii=False, indent=2)}")
        
        if self.warnings:
            report.append("\n" + "=" * 60)
            report.append("⚠️  警告详情")
            report.append("=" * 60)
            for warning in self.warnings:
                report.append(f"  - {warning}")
        
        report.append("\n" + "=" * 60)
        report.append("📝 游戏流程摘要")
        report.append("=" * 60)
        
        # 按阶段整理事件
        phases = {}
        for event in self.events:
            phase = event['data'].get('phase', 'unknown')
            if phase not in phases:
                phases[phase] = []
            phases[phase].append(event)
        
        for phase, events in phases.items():
            report.append(f"\n【{phase}】 - 共 {len(events)} 个事件")
            for event in events[:5]:  # 每个阶段只显示前 5 个
                report.append(f"  • {event['type']}: {str(event['data'].get('summary', ''))[:80]}")
            if len(events) > 5:
                report.append(f"  ... 还有 {len(events) - 5} 个事件")
        
        return "\n".join(report)


def run_full_game_test():
    """运行完整游戏测试"""
    reporter = TestReporter()
    
    print("=" * 60)
    print("🚀 开始完整狼人杀游戏测试")
    print("=" * 60)
    
    try:
        # 1. 加载配置
        print("\n[1/6] 加载配置...")
        config_mgr = ConfigManager()
        config_mgr.load_all()
        reporter.log_event("config_loaded", {"phase": "init"})
        print("   ✓ 配置加载成功")
        
        # 2. 初始化 LLM
        print("\n[2/6] 初始化 LLM 客户端...")
        llm_config = config_mgr.get_llm_config()
        llm_client = LLMClient(llm_config)
        reporter.log_event("llm_initialized", {"phase": "init", "provider": llm_config.get('provider')})
        print(f"   ✓ LLM 已配置：{llm_config.get('provider')}")
        
        # 3. 初始化人格管理器
        print("\n[3/6] 初始化人格管理器...")
        personality_mgr = PersonalityManager()
        print(f"   ✓ 已加载 {len(personality_mgr.personalities)} 种人格")
        reporter.log_event("personalities_loaded", {"phase": "init", "count": len(personality_mgr.personalities)})
        
        # 4. 创建 UI (上帝模式)
        print("\n[4/6] 创建 UI (上帝模式)...")
        ui = CLI(show_inner_thoughts=True, god_view=True)
        reporter.log_event("ui_created", {"phase": "init", "mode": "god_view"})
        
        # 5. 创建游戏引擎
        print("\n[5/6] 创建游戏引擎...")
        engine = GameEngine(ui, config_mgr.system)
        
        # 获取游戏配置
        game_config = config_mgr.get_game_config()
        player_count = game_config.get("player_count", 9)
        roles_config = game_config.get("roles", [])
        personality_names = config_mgr.get_personality_names()
        
        # 设置游戏
        engine.setup(
            player_count=player_count,
            roles_config=roles_config,
            personalities=personality_names,
            human_player_id=None,  # 上帝模式，无人类玩家
        )
        reporter.log_event("game_setup", {
            "phase": "setup",
            "player_count": player_count,
            "roles": roles_config
        })
        print(f"   ✓ 游戏设置完成：{player_count}人局")
        
        # 6. 初始化 AI 代理
        print("\n[6/6] 初始化 AI 代理...")
        for player in engine.state.players.values():
            if player.is_bot:
                personality = personality_mgr.get(player.personality)
                if not personality:
                    personality = personality_mgr.get_random()
                agent = AIAgent(player, personality, llm_client)
                engine.agents[player.id] = agent
        reporter.log_event("agents_initialized", {"phase": "init", "count": len(engine.agents)})
        print(f"   ✓ 已创建 {len(engine.agents)} 个 AI 代理")
        
        # 开始游戏
        print("\n" + "=" * 60)
        print("🎮 开始游戏")
        print("=" * 60)
        
        # 显示玩家身份（上帝视角）
        print("\n【玩家身份】")
        for player in engine.state.players.values():
            role = player.role.value if player.role else "未知"
            personality = player.personality
            print(f"  {player.id}号：{role} - {personality}")
        
        reporter.log_event("game_start", {
            "phase": "game_start",
            "summary": f"游戏开始，{player_count}名玩家"
        })
        
        # 运行游戏
        engine.start()
        
        reporter.log_event("game_end", {
            "phase": "game_end",
            "winner": engine.state.winner,
            "summary": f"游戏结束，获胜方：{engine.state.winner}"
        })
        
        print("\n" + "=" * 60)
        print("✅ 游戏运行完成")
        print("=" * 60)
        
    except Exception as e:
        error_msg = f"{type(e).__name__}: {str(e)}"
        reporter.log_error(error_msg, {"traceback": traceback.format_exc()})
        print(f"\n❌ 游戏运行出错：{error_msg}")
        traceback.print_exc()
    
    # 生成报告
    print("\n")
    print(reporter.generate_report())
    
    # 保存报告
    report_path = Path(__file__).parent / "test_reports" / f"full_game_test_{Path(__file__).stem}.json"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            "events": reporter.events,
            "errors": reporter.errors,
            "warnings": reporter.warnings
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 详细报告已保存至：{report_path}")
    
    return len(reporter.errors) == 0


if __name__ == "__main__":
    success = run_full_game_test()
    sys.exit(0 if success else 1)
