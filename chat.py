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
from typing import List, Dict, Optional
from dotenv import load_dotenv

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
        
        # 默认模型参数
        self.model_params = {
            "model": "Pro/deepseek-ai/DeepSeek-V3",
            "max_tokens": 512,
            "enable_thinking": True,
            "thinking_budget": 4096,
            "min_p": 0.05,
            "temperature": 0.7,
            "top_p": 0.7,
            "top_k": 50,
            "frequency_penalty": 0.5,
            "n": 1
        }
    
    def add_message(self, role: str, content: str):
        """添加消息到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
    
    def clear_history(self):
        """清除对话历史"""
        self.conversation_history.clear()
        print("对话历史已清除")
    
    def send_message(self, user_message: str) -> Optional[str]:
        """
        发送消息到 API 并获取回复
        
        Args:
            user_message: 用户消息
            
        Returns:
            AI 回复内容，失败时返回 None
        """
        try:
            # 添加用户消息到历史
            self.add_message("user", user_message)
            
            # 构建请求数据
            request_data = {
                **self.model_params,
                "messages": self.conversation_history
            }
            
            logger.info(f"发送请求到 API: {self.api_url}")
            
            # 发送请求
            response = self.session.post(
                self.api_url,
                json=request_data,
                timeout=30
            )
            
            # 检查响应状态
            if response.status_code != 200:
                logger.error(f"API 请求失败: {response.status_code} - {response.text}")
                return f"API 请求失败: {response.status_code}"
            
            # 解析响应
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                logger.error("API 响应格式错误: 缺少 choices 字段")
                return "API 响应格式错误"
            
            # 获取 AI 回复
            ai_message = response_data['choices'][0]['message']['content']
            
            # 添加 AI 回复到历史
            self.add_message("assistant", ai_message)
            
            return ai_message
            
        except requests.exceptions.Timeout:
            logger.error("请求超时")
            return "请求超时，请稍后重试"
        except requests.exceptions.ConnectionError:
            logger.error("网络连接错误")
            return "网络连接错误，请检查网络连接"
        except json.JSONDecodeError:
            logger.error("JSON 解析错误")
            return "响应解析错误"
        except Exception as e:
            logger.error(f"未知错误: {str(e)}")
            return f"发生错误: {str(e)}"
    
    def show_params(self):
        """显示当前模型参数"""
        print("\n当前模型参数:")
        for key, value in self.model_params.items():
            print(f"  {key}: {value}")
        print()
    
    def show_history(self):
        """显示对话历史"""
        if not self.conversation_history:
            print("暂无对话历史")
            return
        
        print("\n对话历史:")
        for i, msg in enumerate(self.conversation_history, 1):
            role = "用户" if msg["role"] == "user" else "AI"
            print(f"  {i}. {role}: {msg['content'][:100]}{'...' if len(msg['content']) > 100 else ''}")
        print()


def get_user_input() -> str:
    """获取用户输入，支持多行输入"""
    try:
        user_input = input("\n你: ").strip()
        return user_input
    except (KeyboardInterrupt, EOFError):
        return "quit"


def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print("  DeepSeek-V3 交互式对话客户端")
    print("  支持单轮和多轮对话")
    print("=" * 60)
    print("\n使用说明:")
    print("  - 直接输入消息开始对话")
    print("  - 输入 'quit' 或 'exit' 退出程序")
    print("  - 输入 'clear' 清除对话历史")
    print("  - 输入 'params' 查看模型参数")
    print("  - 输入 'history' 查看对话历史")
    print("  - 按 Ctrl+C 也可退出程序")
    print("-" * 60)


def load_config():
    """加载配置文件"""
    # 加载环境变量
    load_dotenv()
    
    api_url = os.getenv('SILICONFLOW_API_URL')
    api_token = os.getenv('SILICONFLOW_API_TOKEN')
    
    if not api_url:
        api_url = "https://api.siliconflow.cn/v1/chat/completions"
        print(f"使用默认 API URL: {api_url}")
    
    if not api_token:
        print("错误: 请在 .env 文件中配置 SILICONFLOW_API_TOKEN")
        print("请复制 .env.example 为 .env 并填入你的 API Token")
        return None, None
    
    return api_url, api_token


def main():
    """主程序"""
    print_welcome()
    
    # 从配置文件加载 API 配置
    print("\n正在加载配置...")
    api_url, api_token = load_config()
    
    if not api_url or not api_token:
        return
    
    # 初始化客户端
    try:
        client = DeepSeekChat(api_url, api_token)
        print(f"\n✓ 客户端初始化成功")
        print(f"✓ 使用模型: {client.model_params['model']}")
        print("\n开始对话吧! (输入 'quit' 退出)")
    except Exception as e:
        print(f"客户端初始化失败: {e}")
        return
    
    # 主对话循环
    while True:
        try:
            user_input = get_user_input()
            
            # 处理退出命令
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n再见! 👋")
                break
            
            # 处理特殊命令
            if user_input.lower() == 'clear':
                client.clear_history()
                continue
            elif user_input.lower() == 'params':
                client.show_params()
                continue
            elif user_input.lower() == 'history':
                client.show_history()
                continue
            elif not user_input:
                print("请输入消息或命令")
                continue
            
            # 发送消息并获取回复
            print("\nAI 正在思考中...")
            ai_response = client.send_message(user_input)
            
            if ai_response:
                print(f"\nAI: {ai_response}")
            else:
                print("\n抱歉，无法获取回复，请稍后重试")
                
        except KeyboardInterrupt:
            print("\n\n程序被用户中断")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")
            logger.error(f"主循环错误: {e}")


if __name__ == "__main__":
    main()