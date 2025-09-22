#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SiliconFlow API 交互式对话客户端
使用 DeepSeek-V3 模型进行单轮和多轮对话
"""

import json
import requests
import time
import logging
import os
import asyncio
from typing import List, Dict, Optional
from dotenv import load_dotenv
from client import MCPClient

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DeepSeekChat:
    """DeepSeek-V3 对话客户端"""
    
    def __init__(self, api_url: str, api_token: str):
        """
        初始化客户端
        
        Args:
            api_url: API 端点 URL
            api_token: API 认证 Token
        """
        self.api_url = api_url
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json'
        })
        
        # 对话历史
        self.conversation_history: List[Dict[str, str]] = []
        
        # MCP 客户端
        self.mcp_client = None
        self.mcp_tools = []
        
        # 默认模型参数
        self.model_params = {
            "model": "Pro/deepseek-ai/DeepSeek-V3.1",
            "max_tokens": 1024,
            "enable_thinking": False,
            "thinking_budget": 4096,
            "temperature": 0.7,
            "top_p": 0.7,
            "stream": False,
            "tools": []
        }
    
    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history.clear()
        print("对话历史已清除")
    
    def safe_json_dumps(self, obj):
        """安全的JSON序列化，处理不可序列化的对象"""
        # 首先检查是否是 CallToolResult 对象
        if hasattr(obj, 'content') and hasattr(obj, '__class__') and 'CallToolResult' in str(type(obj)):
            try:
                # 提取 CallToolResult 的内容
                content_list = obj.content
                if content_list:
                    # 如果有多个内容项，合并它们
                    text_parts = []
                    for content_item in content_list:
                        if hasattr(content_item, 'text'):
                            text_parts.append(content_item.text)
                        elif hasattr(content_item, 'type') and content_item.type == 'text':
                            text_parts.append(getattr(content_item, 'text', str(content_item)))
                        else:
                            text_parts.append(str(content_item))
                    
                    combined_text = '\n'.join(text_parts) if text_parts else str(obj)
                    return combined_text
                else:
                    return str(obj)
            except Exception as e:
                logger.warning(f"处理 CallToolResult 失败: {e}")
                return str(obj)
        
        # 原有的 JSON 序列化逻辑
        try:
            return json.dumps(obj, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.warning(f"JSON序列化失败，使用字符串表示: {e}")
            try:
                # 尝试转换为字符串
                return str(obj)
            except Exception as str_e:
                logger.error(f"字符串转换也失败: {str_e}")
                return f"序列化失败: {type(obj).__name__}"
    
    async def init_mcp_client(self, server_url: str):
        """初始化 MCP 客户端"""
        try:
            self.mcp_client = MCPClient()
            await self.mcp_client.connect_to_sse_server(server_url)
            await self.load_mcp_tools()
            logger.info(f"MCP 客户端已连接，加载了 {len(self.mcp_tools)} 个工具")
        except Exception as e:
            logger.error(f"初始化 MCP 客户端失败: {e}")
            self.mcp_client = None
    
    async def load_mcp_tools(self):
        """加载 MCP 工具并转换为 API 格式"""
        if not self.mcp_client:
            return
        
        try:
            # 获取 MCP 工具列表
            tools = await self.mcp_client.list_tools()
            self.mcp_tools = []
            
            for tool in tools:
                # 转换为硅基流动 API 格式
                api_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or f"MCP工具: {tool.name}",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                
                # 处理工具参数
                if hasattr(tool, 'inputSchema') and tool.inputSchema:
                    schema = tool.inputSchema
                    if isinstance(schema, dict):
                        if 'properties' in schema:
                            api_tool["function"]["parameters"]["properties"] = schema['properties']
                        if 'required' in schema:
                            api_tool["function"]["parameters"]["required"] = schema['required']
                
                self.mcp_tools.append(api_tool)
            
            # 更新模型参数中的工具列表
            self.model_params["tools"] = self.mcp_tools
            logger.info(f"已加载 {len(self.mcp_tools)} 个 MCP 工具")
            
        except Exception as e:
            logger.error(f"加载 MCP 工具失败: {e}")
    
    async def handle_tool_calls(self, tool_calls):
        """处理工具调用"""
        if not self.mcp_client or not tool_calls:
            return []
        
        results = []
        for tool_call in tool_calls:
            try:
                # 提取工具名称和参数
                function_name = tool_call.get('function', {}).get('name')
                arguments_raw = tool_call.get('function', {}).get('arguments', {})
                
                # 处理参数格式
                if isinstance(arguments_raw, str):
                    try:
                        arguments = json.loads(arguments_raw)
                    except json.JSONDecodeError as e:
                        logger.error(f"无法解析工具参数: {arguments_raw}, 错误: {e}")
                        arguments = {}
                elif isinstance(arguments_raw, dict):
                    arguments = arguments_raw
                else:
                    logger.warning(f"未知的参数类型: {type(arguments_raw)}, 值: {arguments_raw}")
                    arguments = {}
                
                logger.info(f"调用工具: {function_name}, 参数: {arguments}")
                
                # 调用 MCP 工具
                result = await self.mcp_client.call_tool(function_name, arguments)
                
                logger.info(f"工具调用结果类型: {type(result)}")
                logger.info(f"工具调用结果: {result}")
                
                # 使用安全的序列化方法
                content = self.safe_json_dumps(result) if result is not None else "null"
                
                results.append({
                    "tool_call_id": tool_call.get('id'),
                    "role": "tool",
                    "name": function_name,
                    "content": content
                })
                
            except Exception as e:
                logger.error(f"工具调用失败 {function_name}: {e}")
                logger.error(f"工具调用详情: {tool_call}")
                results.append({
                    "tool_call_id": tool_call.get('id'),
                    "role": "tool", 
                    "name": function_name,
                    "content": f"工具调用失败: {str(e)}"
                })
        
        return results
    
    async def send_message(self, user_message: str) -> Optional[str]:
        """发送消息并获取回复"""
        # 添加用户消息到历史
        self.add_message("user", user_message)
        
        # 构建请求数据
        request_data = {
            **self.model_params,
            "messages": self.conversation_history
        }
        
        # 如果没有工具，移除 tools 字段
        if not self.mcp_tools:
            request_data.pop("tools", None)
        
        try:
            # 发送请求
            response = self.session.post(
                self.api_url,
                json=request_data,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"API 请求失败: {response.status_code} - {response.text}")
                return f"API 请求失败: {response.status_code}"
            
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                logger.error("API 响应格式错误: 缺少 choices 字段")
                return "API 响应格式错误"
            
            # 获取 AI 回复消息
            message = response_data['choices'][0]['message']
            
            # 检查是否有工具调用
            if 'tool_calls' in message and message['tool_calls']:
                # 添加助手消息（包含工具调用）到历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": message.get('content', ''),
                    "tool_calls": message['tool_calls']
                })
                
                # 处理工具调用
                tool_results = await self.handle_tool_calls(message['tool_calls'])
                
                # 添加工具结果到历史
                for result in tool_results:
                    self.conversation_history.append(result)
                
                # 再次发送请求获取最终回复
                request_data["messages"] = self.conversation_history
                if not self.mcp_tools:
                    request_data.pop("tools", None)
                
                response = self.session.post(
                    self.api_url,
                    json=request_data,
                    timeout=30
                )
                
                if response.status_code != 200:
                    logger.error(f"工具调用后的 API 请求失败: {response.status_code} - {response.text}")
                    return f"工具调用后的 API 请求失败: {response.status_code}"
                
                response_data = response.json()
                
                if 'choices' not in response_data or not response_data['choices']:
                    logger.error("工具调用后的 API 响应格式错误")
                    return "工具调用后的 API 响应格式错误"
                
                message = response_data['choices'][0]['message']
            
            # 获取最终回复内容
            ai_response = message.get('content', '')
            
            # 添加 AI 回复到历史
            self.add_message("assistant", ai_response)
            
            return ai_response
            
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return "请求超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            logger.error(f"网络请求错误: {e}")
            return f"网络请求错误: {e}"
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误: {e}")
            return "响应格式错误"
        except Exception as e:
            logger.error(f"发送消息时发生未知错误: {e}")
            return f"发生未知错误: {e}"
    
    def show_params(self):
        """显示当前模型参数"""
        print("\n当前模型参数:")
        for key, value in self.model_params.items():
            if key != "tools":  # 工具列表太长，单独显示
                print(f"  {key}: {value}")
        
        if self.mcp_tools:
            print(f"  tools: {len(self.mcp_tools)} 个工具已加载")
        else:
            print("  tools: 无")
    
    def show_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("\n对话历史为空")
            return
        
        print(f"\n对话历史 (共 {len(self.conversation_history)} 条消息):")
        for i, msg in enumerate(self.conversation_history, 1):
            role = msg['role']
            content = msg.get('content', '')
            print(f"  {i}. [{role.upper()}]: {content[:100]}{'...' if len(content) > 100 else ''}")


def get_user_input() -> str:
    """获取用户输入"""
    try:
        return input("\n你: ").strip()
    except (EOFError, KeyboardInterrupt):
        return "quit"


def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print("🤖 DeepSeek-V3 对话客户端")
    print("=" * 60)
    print("输入消息开始对话")
    print("特殊命令:")
    print("  - 'quit' 或 'exit': 退出程序")
    print("  - 'clear': 清除对话历史")
    print("  - 'params': 显示模型参数")
    print("  - 'history': 显示对话历史")
    print("  - 'tools': 显示可用工具")
    print("-" * 60)


def load_config():
    """加载配置"""
    load_dotenv()
    
    api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
    api_token = os.getenv('SILICONFLOW_API_TOKEN')
    mcp_server_url = os.getenv('MCP_SERVER_URL', 'http://localhost:8000/sse')
    
    if not api_token:
        print("错误: 请在 .env 文件中设置 SILICONFLOW_API_TOKEN")
        print("示例: SILICONFLOW_API_TOKEN=your_token_here")
        exit(1)
    
    print(f"API URL: {api_url}")
    print(f"MCP 服务器 URL: {mcp_server_url}")
    
    return api_url, api_token, mcp_server_url


async def main():
    """主函数"""
    try:
        # 加载配置
        api_url, api_token, mcp_server_url = load_config()
        
        # 初始化客户端
        client = DeepSeekChat(api_url, api_token)
        
        # 尝试初始化 MCP 客户端
        print(f"正在连接 MCP 服务器: {mcp_server_url}")
        await client.init_mcp_client(mcp_server_url)
        
        # 打印欢迎信息
        print_welcome()
        
        # 主对话循环
        while True:
            try:
                # 获取用户输入
                user_input = get_user_input()
                
                # 处理退出命令
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n再见! 👋")
                    break
                elif user_input.lower() == 'clear':
                    client.clear_history()
                    continue
                elif user_input.lower() == 'params':
                    client.show_params()
                    continue
                elif user_input.lower() == 'history':
                    client.show_history()
                    continue
                elif user_input.lower() == 'tools':
                    if client.mcp_tools:
                        print(f"\n可用工具 ({len(client.mcp_tools)} 个):")
                        for tool in client.mcp_tools:
                            func = tool['function']
                            print(f"  - {func['name']}: {func['description']}")
                    else:
                        print("\n当前没有可用的工具")
                    continue
                elif not user_input:
                    print("请输入消息或命令")
                    continue
                
                # 发送消息并获取回复
                print("\nAI 正在思考中...")
                start_time = time.time()
                
                ai_response = await client.send_message(user_input)
                
                end_time = time.time()
                
                if ai_response:
                    print(f"\nAI: {ai_response}")
                    print(f"\n⏱️  响应时间: {end_time - start_time:.2f} 秒")
                else:
                    print("\n抱歉，无法获取回复，请稍后重试")
                    
            except KeyboardInterrupt:
                print("\n\n程序被用户中断")
                break
            except Exception as e:
                print(f"\n发生错误: {e}")
                logger.error(f"主循环错误: {e}")
                
    except Exception as e:
        print(f"程序启动失败: {e}")
        logger.error(f"程序启动失败: {e}")
    finally:
        # 清理资源
        if hasattr(client, 'mcp_client') and client.mcp_client:
            await client.mcp_client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())