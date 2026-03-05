"""LLM 客户端 - 支持多种大模型 API"""
import json
import time
import requests
import logging
from typing import Optional

# 屏蔽 urllib3 的警告信息（避免显示端口相关警告）
logging.getLogger("urllib3").setLevel(logging.ERROR)
requests.packages.urllib3.disable_warnings()


class LLMClient:
    """大模型客户端"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: LLM 配置，包含 provider, api_key, model, base_url, temperature 等
        """
        self.provider = config.get("provider", "deepseek")
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "deepseek-chat")
        self.base_url = config.get("base_url", "https://api.deepseek.com/v1")
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 120)  # 默认 120 秒超时
        self.retry_count = config.get("retry_count", 2)  # 从配置读取重试次数
        self.retry_delay = config.get("retry_delay", 1)  # 从配置读取重试间隔
        self.speech_delay = config.get("speech_delay", 0.3)  # AI 发言间隔
    
    def chat(self, messages: list[dict], max_tokens: int = 200) -> tuple[str, str]:
        """
        发送对话请求（带重试机制）
        
        Args:
            messages: 消息列表，格式 [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]
            max_tokens: 最大 token 数
        
        Returns:
            (回复内容，原始响应)
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
        }
        
        url = f"{self.base_url}/chat/completions"
        
        # 重试机制
        last_error = None
        for attempt in range(self.retry_count):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"].strip()
                return content, data
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                print(f"[警告] 请求超时，{self.retry_delay}秒后重试 ({attempt+1}/{self.retry_count})...")
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误：{str(e)}"
                print(f"[警告] 网络连接失败，{self.retry_delay}秒后重试 ({attempt+1}/{self.retry_count})...")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    print("[错误] API Key 无效，请检查配置")
                    return f"[系统错误：API Key 无效]", ""
                elif e.response.status_code == 429:
                    last_error = "请求频率超限"
                    print(f"[警告] 请求频率超限，{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    last_error = f"HTTP 错误：{e.response.status_code}"
                    break
            except Exception as e:
                last_error = str(e)
                print(f"[警告] 请求失败：{str(e)}，{self.retry_delay}秒后重试 ({attempt+1}/{self.retry_count})...")
                time.sleep(self.retry_delay)
        
        # 所有重试失败
        print(f"[错误] LLM 请求最终失败：{last_error}")
        print(f"[提示] 请检查：1) 网络连接 2) API Key 是否有效 3) API 服务是否正常")
        return f"[系统错误：{last_error}]", ""
    
    def generate_with_inner_thought(self, system_prompt: str, user_prompt: str, 
                                     max_length: int = 100) -> tuple[str, str]:
        """
        生成回复和内心独白
        
        Args:
            system_prompt: 系统提示（包含人格设定）
            user_prompt: 用户提示（当前情境）
            max_length: 最大字数限制
        
        Returns:
            (发言内容，内心独白)
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # 要求 AI 以 JSON 格式返回，包含发言和内心独白
        instruction = f"""
请用以下 JSON 格式回复（不要添加其他内容）：
{{
    "speech": "你的发言内容，不超过{max_length}字",
    "inner_thought": "你的真实想法/内心独白"
}}
"""
        messages.append({"role": "user", "content": instruction})
        
        content, raw = self.chat(messages, max_tokens=250)
        
        # 解析 JSON 响应
        try:
            # 尝试提取 JSON
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = content[start:end]
                result = json.loads(json_str)
                speech = result.get("speech", content)[:max_length]
                inner_thought = result.get("inner_thought", "")
                return speech, inner_thought
            else:
                return content[:max_length], "[未生成内心独白]"
        except json.JSONDecodeError:
            # 解析失败，直接返回
            return content[:max_length], "[未生成内心独白]"
