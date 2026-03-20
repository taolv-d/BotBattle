from typing import Dict, Any, Optional, List
import json
import logging
import traceback

# 配置日志
logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务类

    提供大语言模型交互服务的抽象接口
    """

    # 默认响应（当 LLM 调用失败时返回）
    DEFAULT_RESPONSE = "抱歉，我暂时无法回应。"
    DEFAULT_STRUCTURED_OUTPUT = {}

    def __init__(self, model_config: Dict[str, Any]):
        """
        初始化 LLM 服务

        Args:
            model_config: 模型配置
        """
        self.model_config = model_config
        self.provider = model_config.get("provider", "mock")
        self.model_params = model_config.get("params", {})

        # 根据配置初始化对应的 LLM 提供商
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "deepseek":
            self._init_deepseek()
        elif self.provider == "anthropic":
            self._init_anthropic()
        elif self.provider == "ollama":
            self._init_ollama()
        elif self.provider == "dashscope":
            self._init_dashscope()
        else:
            # 默认使用模拟实现
            self.provider_instance = MockLLM()

    def _init_openai(self):
        """初始化 OpenAI 服务"""
        try:
            import openai
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("OpenAI API key is required")

            openai.api_key = api_key
            self.provider_instance = OpenAILLM(self.model_config)
        except ImportError:
            logger.warning("openai package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            logger.error(f"Error initializing OpenAI: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()

    def _init_deepseek(self):
        """初始化 DeepSeek 服务（使用 requests 直接调用 API）"""
        try:
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("DeepSeek API key is required")
            
            self.provider_instance = DeepSeekLLM(self.model_config)
            logger.info(f"DeepSeek LLM 已初始化：{self.model_config.get('model', 'deepseek-chat')}")
        except Exception as e:
            logger.error(f"Error initializing DeepSeek: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()

    def _init_anthropic(self):
        """初始化 Anthropic 服务"""
        try:
            import anthropic
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("Anthropic API key is required")

            client = anthropic.Anthropic(api_key=api_key)
            self.provider_instance = AnthropicLLM(client, self.model_config)
        except ImportError:
            logger.warning("anthropic package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            logger.error(f"Error initializing Anthropic: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()

    def _init_ollama(self):
        """初始化 Ollama 服务"""
        try:
            import ollama
            self.provider_instance = OllamaLLM(ollama, self.model_config)
        except ImportError:
            logger.warning("ollama package not installed. Using mock implementation.")
            self.provider_instance = MockLLM()
        except Exception as e:
            logger.error(f"Error initializing Ollama: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()

    def _init_dashscope(self):
        """初始化阿里云百炼（DashScope）服务"""
        try:
            api_key = self.model_config.get("api_key")
            if not api_key:
                raise ValueError("DashScope API key is required")

            self.provider_instance = DashScopeLLM(self.model_config)
            logger.info(f"DashScope LLM 已初始化：{self.model_config.get('model', 'qwen-plus')}")
        except Exception as e:
            logger.error(f"Error initializing DashScope: {e}. Using mock implementation.")
            self.provider_instance = MockLLM()

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        生成响应

        Args:
            prompt: 输入提示
            context: 上下文信息

        Returns:
            生成的响应文本
        """
        try:
            return await self.provider_instance.generate_response(prompt, context)
        except Exception as e:
            # 记录错误日志
            logger.error(f"LLM generate_response failed: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            logger.debug(f"Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"Prompt: {prompt}")
            # 返回默认响应
            return self.DEFAULT_RESPONSE

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        生成结构化输出

        Args:
            prompt: 输入提示
            schema: 输出模式
            context: 上下文信息

        Returns:
            结构化输出字典
        """
        try:
            return await self.provider_instance.generate_structured_output(prompt, schema, context)
        except Exception as e:
            # 记录错误日志
            logger.error(f"LLM generate_structured_output failed: {e}")
            logger.debug(f"Traceback: {traceback.format_exc()}")
            logger.debug(f"Prompt: {prompt[:200]}..." if len(prompt) > 200 else f"Prompt: {prompt}")
            # 返回默认结构化输出
            return self.DEFAULT_STRUCTURED_OUTPUT


class BaseLLMProvider:
    """LLM 提供商基类"""

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        raise NotImplementedError

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                       context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        raise NotImplementedError


class MockLLM(BaseLLMProvider):
    """模拟 LLM 实现（用于测试）"""

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """模拟生成响应"""
        # 根据提示内容返回模拟响应
        if "夜晚行动" in prompt or "night" in prompt.lower():
            return '{"action": "skip", "target": null}'
        elif "发言" in prompt or "speech" in prompt.lower():
            return "这是一个模拟发言。"
        elif "投票" in prompt or "vote" in prompt.lower():
            return '{"target": 1}'
        else:
            return "这是来自模拟LLM的响应。"

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """模拟生成结构化输出"""
        # 返回符合模式的模拟数据
        if "target" in schema.get("properties", {}):
            return {"target": 1}
        elif "action" in schema.get("properties", {}):
            return {"action": "skip"}
        else:
            return {}


class OpenAILLM(BaseLLMProvider):
    """OpenAI LLM 实现"""

    def __init__(self, config: Dict[str, Any]):
        self.client = None  # 由外部传入
        self.model = config.get("model", "gpt-3.5-turbo")
        self.temperature = config.get("temperature", 0.7)

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()

            # 在线程池中运行同步调用
            response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature
            ))

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI generate_response error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()

            # 使用函数调用获取结构化输出
            response = await loop.run_in_executor(None, lambda: self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                functions=[{
                    "name": "extract_info",
                    "description": "Extract structured information",
                    "parameters": schema
                }],
                function_call={"name": "extract_info"},
                temperature=self.temperature
            ))

            # 解析函数参数
            function_call = response.choices[0].message.function_call
            if function_call:
                return json.loads(function_call.arguments)
            else:
                return {}
        except Exception as e:
            logger.error(f"OpenAI generate_structured_output error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理


class AnthropicLLM(BaseLLMProvider):
    """Anthropic LLM 实现"""

    def __init__(self, client, config: Dict[str, Any]):
        self.client = client
        self.model = config.get("model", "claude-3-haiku-20240307")
        self.temperature = config.get("temperature", 0.7)

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()

            # 在线程池中运行同步调用
            response = await loop.run_in_executor(None, lambda: self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}]
            ))

            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic generate_response error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        # Anthropic 没有原生的函数调用，需要手动解析JSON
        import asyncio
        import json
        
        try:
            loop = asyncio.get_event_loop()

            formatted_prompt = f"{prompt}\n\n请严格按照以下JSON格式返回结果：\n{json.dumps(schema)}"

            response = await loop.run_in_executor(None, lambda: self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.1,  # 低温度确保格式准确
                messages=[{"role": "user", "content": formatted_prompt}]
            ))

            # 尝试从响应中提取JSON
            content = response.content[0].text
            # 查找JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Anthropic JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"Anthropic generate_structured_output error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理


class OllamaLLM(BaseLLMProvider):
    """Ollama LLM 实现"""

    def __init__(self, ollama_client, config: Dict[str, Any]):
        self.ollama = ollama_client
        self.model = config.get("model", "llama2")
        self.options = config.get("options", {})

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        
        try:
            loop = asyncio.get_event_loop()

            # 在线程池中运行同步调用
            response = await loop.run_in_executor(None, lambda: self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options=self.options
            ))

            return response['message']['content']
        except Exception as e:
            logger.error(f"Ollama generate_response error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        import json
        
        try:
            loop = asyncio.get_event_loop()

            formatted_prompt = f"{prompt}\n\n请严格按照以下JSON格式返回结果：\n{json.dumps(schema)}"

            response = await loop.run_in_executor(None, lambda: self.ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": formatted_prompt}],
                options={**self.options, "temperature": 0.1}  # 低温度确保格式准确
            ))

            # 尝试从响应中提取JSON
            content = response['message']['content']
            # 查找JSON部分
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = content[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return {}
        except json.JSONDecodeError as e:
            logger.error(f"Ollama JSON decode error: {e}")
            raise
        except Exception as e:
            logger.error(f"Ollama generate_structured_output error: {e}")
            raise  # 重新抛出异常，由 LLMService 处理


class DeepSeekLLM(BaseLLMProvider):
    """
    DeepSeek LLM 实现（使用 requests 直接调用 API）
    
    DeepSeek 使用 OpenAI 兼容的 API 格式
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "deepseek-chat")
        self.base_url = config.get("base_url", "https://api.deepseek.com/v1")
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 120)
        self.retry_count = config.get("retry_count", 2)
        self.retry_delay = config.get("retry_delay", 1)

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        import requests
        import time

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": 500,
        }

        url = f"{self.base_url}/chat/completions"

        # 重试机制
        last_error = None
        for attempt in range(self.retry_count):
            try:
                # 在线程池中运行同步请求
                loop = asyncio.get_event_loop()
                
                def make_request():
                    response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json()

                data = await loop.run_in_executor(None, make_request)
                content = data["choices"][0]["message"]["content"].strip()
                return content

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"DeepSeek 请求超时，{self.retry_delay}秒后重试 ({attempt+1}/{self.retry_count})...")
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误：{str(e)}"
                logger.warning(f"DeepSeek 网络连接失败，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("DeepSeek API Key 无效")
                    raise ValueError("API Key 无效")
                elif e.response.status_code == 429:
                    last_error = "请求频率超限"
                    logger.warning(f"DeepSeek 请求频率超限，{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    last_error = f"HTTP 错误：{e.response.status_code}"
                    logger.error(f"DeepSeek HTTP 错误：{last_error}")
                    raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"DeepSeek 请求失败：{str(e)}，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)

        # 所有重试失败
        logger.error(f"DeepSeek 请求最终失败：{last_error}")
        raise Exception(f"DeepSeek 请求失败：{last_error}")

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        import requests
        import time

        # 构建要求 JSON 格式输出的提示
        # 明确告诉 LLM 返回符合 schema 的数据，而不是 schema 本身
        formatted_prompt = f"""{prompt}

请严格按照以下 JSON Schema 生成数据（只返回 JSON 数据对象，不要返回 Schema 定义）：
Schema: {json.dumps(schema, ensure_ascii=False)}

示例：如果 Schema 是 {{"type": "object", "properties": {{"action": {{"type": "string"}}}}}}
你应该返回：{{"action": "具体动作"}}
而不是：{{"type": "object", "properties": {{"action": {{"type": "string"}}}}}}

直接返回 JSON 数据，不要添加任何解释："""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": formatted_prompt}],
            "temperature": 0.1,  # 低温度确保格式准确
            "max_tokens": 500,
        }

        url = f"{self.base_url}/chat/completions"

        # 重试机制
        last_error = None
        for attempt in range(self.retry_count):
            try:
                loop = asyncio.get_event_loop()
                
                def make_request():
                    response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json()

                data = await loop.run_in_executor(None, make_request)
                content = data["choices"][0]["message"]["content"].strip()
                
                # 尝试从响应中提取 JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = content[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    logger.warning(f"DeepSeek 未返回有效 JSON: {content[:200]}")
                    return {}

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"DeepSeek 请求超时，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误：{str(e)}"
                logger.warning(f"DeepSeek 网络连接失败...")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("DeepSeek API Key 无效")
                    raise ValueError("API Key 无效")
                elif e.response.status_code == 429:
                    last_error = "请求频率超限"
                    logger.warning(f"DeepSeek 请求频率超限...")
                    time.sleep(self.retry_delay)
                else:
                    last_error = f"HTTP 错误：{e.response.status_code}"
                    logger.error(f"DeepSeek HTTP 错误：{last_error}")
                    raise
            except json.JSONDecodeError as e:
                logger.error(f"DeepSeek JSON 解析错误：{e}")
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"DeepSeek 请求失败：{str(e)}...")
                time.sleep(self.retry_delay)

        # 所有重试失败
        logger.error(f"DeepSeek 请求最终失败：{last_error}")
        raise Exception(f"DeepSeek 请求失败：{last_error}")


class DashScopeLLM(BaseLLMProvider):
    """
    阿里云百炼（DashScope）LLM 实现

    支持通义千问等模型
    API 文档：https://help.aliyun.com/zh/dashscope/
    """

    def __init__(self, config: Dict[str, Any]):
        self.api_key = config.get("api_key", "")
        self.model = config.get("model", "qwen-plus")
        self.base_url = config.get("base_url", "https://dashscope.aliyuncs.com/api/v1")
        self.temperature = config.get("temperature", 0.7)
        self.timeout = config.get("timeout", 120)
        self.retry_count = config.get("retry_count", 2)
        self.retry_delay = config.get("retry_delay", 1)

    async def generate_response(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成响应"""
        import asyncio
        import requests
        import time

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 通义千问使用 dashscope 兼容格式
        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            },
            "parameters": {
                "temperature": self.temperature,
                "max_tokens": 2000,
            }
        }

        # DashScope API 端点
        url = f"{self.base_url}/services/aigc/text-generation/generation"

        # 重试机制
        last_error = None
        for attempt in range(self.retry_count):
            try:
                # 在线程池中运行同步请求
                loop = asyncio.get_event_loop()

                def make_request():
                    response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json()

                data = await loop.run_in_executor(None, make_request)
                
                # DashScope 返回格式
                if "output" in data and "text" in data["output"]:
                    content = data["output"]["text"].strip()
                    return content
                elif "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()
                    return content
                else:
                    logger.warning(f"DashScope 返回格式异常：{data}")
                    return "抱歉，响应格式异常。"

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"DashScope 请求超时，{self.retry_delay}秒后重试 ({attempt+1}/{self.retry_count})...")
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误：{str(e)}"
                logger.warning(f"DashScope 网络连接失败，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("DashScope API Key 无效")
                    raise ValueError("API Key 无效")
                elif e.response.status_code == 429:
                    last_error = "请求频率超限"
                    logger.warning(f"DashScope 请求频率超限，{self.retry_delay}秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    last_error = f"HTTP 错误：{e.response.status_code}"
                    logger.error(f"DashScope HTTP 错误：{last_error}")
                    raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"DashScope 请求失败：{str(e)}，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)

        # 所有重试失败
        logger.error(f"DashScope 请求最终失败：{last_error}")
        raise Exception(f"DashScope 请求失败：{last_error}")

    async def generate_structured_output(self, prompt: str, schema: Dict[str, Any],
                                      context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """生成结构化输出"""
        import asyncio
        import requests
        import time

        # 构建要求 JSON 格式输出的提示
        formatted_prompt = f"""{prompt}

请严格按照以下 JSON Schema 生成数据（只返回 JSON 数据对象，不要返回 Schema 定义）：
Schema: {json.dumps(schema, ensure_ascii=False)}

示例：如果 Schema 是 {{"type": "object", "properties": {{"action": {{"type": "string"}}}}}}
你应该返回：{{"action": "具体动作"}}
而不是：{{"type": "object", "properties": {{"action": {{"type": "string"}}}}}}

直接返回 JSON 数据，不要添加任何解释："""

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": self.model,
            "input": {
                "messages": [
                    {"role": "user", "content": formatted_prompt}
                ]
            },
            "parameters": {
                "temperature": 0.1,  # 低温度确保格式准确
                "max_tokens": 2000,
            }
        }

        url = f"{self.base_url}/services/aigc/text-generation/generation"

        # 重试机制
        last_error = None
        for attempt in range(self.retry_count):
            try:
                loop = asyncio.get_event_loop()

                def make_request():
                    response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                    response.raise_for_status()
                    return response.json()

                data = await loop.run_in_executor(None, make_request)
                
                # 提取响应内容
                content = ""
                if "output" in data and "text" in data["output"]:
                    content = data["output"]["text"].strip()
                elif "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"].strip()

                # 尝试从响应中提取 JSON
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    json_str = content[start_idx:end_idx]
                    return json.loads(json_str)
                else:
                    logger.warning(f"DashScope 未返回有效 JSON: {content[:200]}")
                    return {}

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"DashScope 请求超时，{self.retry_delay}秒后重试...")
                time.sleep(self.retry_delay)
            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误：{str(e)}"
                logger.warning(f"DashScope 网络连接失败...")
                time.sleep(self.retry_delay)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 401:
                    logger.error("DashScope API Key 无效")
                    raise ValueError("API Key 无效")
                elif e.response.status_code == 429:
                    last_error = "请求频率超限"
                    logger.warning(f"DashScope 请求频率超限...")
                    time.sleep(self.retry_delay)
                else:
                    last_error = f"HTTP 错误：{e.response.status_code}"
                    logger.error(f"DashScope HTTP 错误：{last_error}")
                    raise
            except json.JSONDecodeError as e:
                logger.error(f"DashScope JSON 解析错误：{e}")
                raise
            except Exception as e:
                last_error = str(e)
                logger.warning(f"DashScope 请求失败：{str(e)}...")
                time.sleep(self.retry_delay)

        # 所有重试失败
        logger.error(f"DashScope 请求最终失败：{last_error}")
        raise Exception(f"DashScope 请求失败：{last_error}")