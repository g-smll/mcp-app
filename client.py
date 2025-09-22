#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP (Model Context Protocol) SSE 客户端
通过 HTTP SSE 与 MCP 服务端进行通信，支持 Tools、Resources、Prompts 服务
"""

import asyncio
import io
import os
import sys
from contextlib import AsyncExitStack
from typing import List, Dict, Any, Optional

# 设置标准输出编码为 UTF-8 以解决 Windows 控制台乱码问题
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("提示: 安装 python-dotenv 以支持 .env 文件: pip install python-dotenv")

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool, Resource, Prompt


class MCPClient:
    """MCP SSE 客户端"""
    
    def __init__(self):
        """初始化 MCP 客户端"""
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools: List[Tool] = []
        self.resources: List[Resource] = []
        self.prompts: List[Prompt] = []
        
        # Store context managers to keep them alive
        self._streams_context = None
        self._session_context = None

    async def connect_to_sse_server(self, server_url: str):
        """Connect to an MCP server running with SSE transport"""
        try:
            print(f"正在连接到 MCP 服务端: {server_url}")
            
            # Store the context managers so they stay alive
            self._streams_context = sse_client(url=server_url)
            streams = await self._streams_context.__aenter__()

            self._session_context = ClientSession(*streams)
            self.session: ClientSession = await self._session_context.__aenter__()

            # Initialize
            await self.session.initialize()

            # List available tools to verify connection
            print("MCP 连接建立成功...")
            print("MCP 正在验证连接...")
            response = await self.session.list_tools()
            tools = response.tools
            #print(f"连接到服务器，发现工具: {[tool.name for tool in tools]}")
            
            return True
            
        except Exception as e:
            print(f"连接失败: {e}")
            return False

    async def cleanup(self):
        """Properly clean up the session and streams"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
                self._session_context = None
                
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)
                self._streams_context = None
                
            #print("MCP 连接已关闭")
            
        except Exception as e:
            print(f"关闭连接时出错: {e}")
        finally:
            self.session = None

    async def list_tools(self) -> List[Tool]:
        """获取可用工具列表"""
        if not self.session:
            print("未建立连接")
            return []
            
        try:
            print("正在获取工具列表...")
            result = await self.session.list_tools()
            self.tools = result.tools
            
            print(f"发现 {len(self.tools)} 个工具:")
            for i, tool in enumerate(self.tools, 1):
                print(f"  {i}. {tool.name}: {tool.description}")
                
            return self.tools
            
        except Exception as e:
            print(f"获取工具列表失败: {e}")
            return []

    async def list_resources(self) -> List[Resource]:
        """获取可用资源列表"""
        if not self.session:
            return []
            
        try:
            result = await self.session.list_resources()
            self.resources = result.resources

                    
            return self.resources
            
        except Exception as e:
            print(f"获取资源列表失败: {e}")
            return []

    async def list_prompts(self) -> List[Prompt]:
        """获取可用提示词模板列表"""
        if not self.session:
            print("未建立连接")
            return []
            
        try:
            # print("正在获取提示词模板列表...")
            result = await self.session.list_prompts()
            self.prompts = result.prompts
            
            # print(f"发现 {len(self.prompts)} 个提示词模板:")
            # for i, prompt in enumerate(self.prompts, 1):
            #     print(f"  {i}. {prompt.name}: {prompt.description}")
            #     if prompt.arguments:
            #         args = [arg.name for arg in prompt.arguments]
            #         print(f"     参数: {', '.join(args)}")
                    
            return self.prompts
            
        except Exception as e:
            print(f"获取提示词模板列表失败: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """调用工具"""
        if not self.session:
            print("未建立连接")
            return None
            
        if arguments is None:
            arguments = {}
            
        try:
            print(f"正在调用工具: {tool_name}")
            result = await self.session.call_tool(tool_name, arguments)
            
            print("工具调用成功")
            return result
            
        except Exception as e:
            print(f"工具调用失败: {e}")
            return None

    async def read_resource(self, resource_uri: str) -> Any:
        """读取资源"""
        if not self.session:
            #print("未建立连接")
            return None
            
        try:
            #print(f"正在读取资源->: {resource_uri}")
            result = await self.session.read_resource(resource_uri)
            
            #print("资源读取成功->")
            return result
            
        except Exception as e:
            print(f"资源读取失败: {e}")
            return None

    async def get_prompt(self, prompt_name: str, arguments: Dict[str, Any] = None) -> Any:
        """获取提示词模板"""
        if not self.session:
            print("未建立连接")
            return None
            
        if arguments is None:
            arguments = {}
            
        try:
            result = await self.session.get_prompt(prompt_name, arguments)
            return result
            
        except Exception as e:
            print(f"提示词模板获取失败: {e}")
            return None



async def main():
    """主程序"""

    # 从环境变量或命令行参数获取 SSE 服务 URL
    sse_url = None

    sse_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/sse")
    
    # 创建并运行客户端
    client = MCPClient()
    
    try:
        # 连接到服务端
        if await client.connect_to_sse_server(sse_url):
            print("MCP 连接成功可用....")

            # 获取并打印所有资源
            print("\n---1 获取 MCP 静态资源 ---")
            resources = await client.list_resources()

            for resource in resources:
                resource_content = await client.read_resource(resource.uri)
                print(f"resources.content->: {resource_content}")


            print("\n---2 获取 MCP 动态资源 ---")
            table_structure = await client.read_resource("database://table/classes/structure")
            print(f"resources.table_structure->: {table_structure}")

            table_data = await client.read_resource("database://table/classes/data")
            print(f"resources.table_data->: {table_data}")

            print("\n---3 获取 MCP Prompt 服务 ---")
            prompts = await client.list_prompts()
            
            # 如果有可用的 prompt，演示调用
            if prompts:
                for prompt in prompts:
                    # 演示调用第一个 prompt（如果需要参数，可以传入）
                    if prompt.name:
                        try:
                            # 根据 prompt 是否需要参数来调用
                            if prompt.arguments:
                                # 构造参数字典
                                prompt_args = {
                                    "query_description": "查询学生表",
                                    "table_name": "students"
                                }
                                
                                prompt_result = await client.get_prompt(prompt.name, prompt_args)
                                print(f"resources.Prompt->: {prompt_result}")
                            else:
                                # 不需要参数的 prompt
                                prompt_result = await client.get_prompt(prompt.name)
                                print(f"resources.Prompt->: {prompt_result}")
                        except Exception as e:
                            print(f"调用 Prompt {prompt.name} 失败: {e}")
                    
                    print("-" * 50)

    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n程序运行错误: {e}")
    finally:
        await client.cleanup()
        print("\n\n--- 释放 MCP 连接 ---")


if __name__ == "__main__":
    asyncio.run(main())