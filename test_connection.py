#!/usr/bin/env python3
"""测试LLM连接"""

import sys
import os
sys.path.append(os.getcwd())

from config_loader import ConfigManager
from ai.llm_client import LLMClient

def test_connection():
    """测试LLM连接"""
    # 创建配置管理器并加载配置
    config_manager = ConfigManager()
    config_manager.load_system()
    
    # 获取LLM配置
    llm_config = config_manager.get_llm_config()
    
    print("当前LLM配置:")
    for key, value in llm_config.items():
        if key == "api_key":
            print(f"  {key}: ***隐藏API密钥***")
        else:
            print(f"  {key}: {value}")
    
    # 创建LLM客户端
    client = LLMClient(llm_config)
    
    # 测试连接
    try:
        print("\n正在测试连接...")
        response = client.chat([
            {'role': 'user', 'content': '你好，请返回"连接测试成功"'}
        ])
        print('连接测试结果:')
        print(response)
        print('\n连接测试完成，没有出现异常。')
        return True
    except Exception as e:
        print(f'连接测试失败: {str(e)}')
        return False

if __name__ == "__main__":
    test_connection()