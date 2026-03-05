"""项目初始化脚本"""
import os
import shutil
from pathlib import Path


def init_config():
    """初始化配置文件"""
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    system_json = config_dir / "system.json"
    system_example = config_dir / "system.example.json"
    
    if not system_json.exists():
        if system_example.exists():
            # 复制示例文件
            shutil.copy(system_example, system_json)
            print(f"[OK] 已创建配置文件：{system_json}")
            print(f"[提示] 请编辑该文件，填入你的 API Key")
        else:
            # 创建默认配置
            default_config = """{
  "llm": {
    "provider": "deepseek",
    "api_key": "YOUR_API_KEY",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",
    "temperature": 0.7,
    "timeout": 180,
    "retry_count": 5,
    "retry_delay": 3
  },
  "game": {
    "default_player_count": 9,
    "max_player_count": 15,
    "speech_timeout": 60,
    "ai_speech_delay": 0.5
  },
  "log": {
    "save_dir": "logs",
    "save_inner_thoughts": true,
    "verbose": false
  }
}
"""
            with open(system_json, "w", encoding="utf-8") as f:
                f.write(default_config)
            print(f"[OK] 已创建默认配置文件：{system_json}")
            print(f"[提示] 请编辑该文件，填入你的 API Key")
    else:
        print(f"[OK] 配置文件已存在：{system_json}")
    
    # 创建 logs 目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    print(f"[OK] 已创建日志目录：{logs_dir}")


def main():
    """主函数"""
    print("=" * 50)
    print("BotBattle - 项目初始化")
    print("=" * 50)
    print()
    
    init_config()
    
    print()
    print("=" * 50)
    print("初始化完成！")
    print("=" * 50)
    print()
    print("下一步：")
    print("1. 编辑 config/system.json 文件")
    print("2. 填入你的 API Key")
    print("3. 运行 python test_api.py 测试连接")
    print("4. 运行 python main.py 开始游戏")
    print()


if __name__ == "__main__":
    main()
