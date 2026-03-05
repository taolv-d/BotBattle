"""测试 LLM API 连接"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config_loader import ConfigManager
from ai.llm_client import LLMClient


def test_api():
    """测试 API 连接"""
    print("=" * 50)
    print("🔍 测试 LLM API 连接")
    print("=" * 50)
    
    # 加载配置
    config_mgr = ConfigManager()
    try:
        config_mgr.load_system()
    except FileNotFoundError:
        print("\n[错误] 配置文件不存在：config/system.json")
        return False
    
    llm_config = config_mgr.get_llm_config()
    
    # 检查 API Key
    if not llm_config.get("api_key") or llm_config.get("api_key") == "YOUR_API_KEY":
        print("\n[错误] 未配置 API Key！")
        print("请编辑 config/system.json 文件，填入有效的 API Key")
        return False
    
    print(f"\n配置信息：")
    print(f"  提供商：{llm_config.get('provider', 'unknown')}")
    print(f"  模型：{llm_config.get('model', 'unknown')}")
    print(f"  地址：{llm_config.get('base_url', 'unknown')}")
    
    # 创建客户端并测试
    llm = LLMClient(llm_config)
    
    print("\n正在发送测试请求...")
    
    messages = [
        {"role": "user", "content": "你好，请用一句话介绍你自己。"}
    ]
    
    content, raw = llm.chat(messages, max_tokens=50)
    
    if "系统错误" in content:
        print(f"\n❌ 测试失败：{content}")
        print("\n可能的原因：")
        print("  1. 网络连接问题（可能需要代理）")
        print("  2. API Key 无效或额度不足")
        print("  3. API 服务暂时不可用")
        return False
    else:
        print(f"\n✅ 测试成功！")
        print(f"\nAI 回复：{content}")
        return True


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
