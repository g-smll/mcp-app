# 项目需求文档

## 项目概述
本项目包含两个独立的 Python 客户端：
1. **SiliconFlow API 客户端** (`chat.py`) - 与 SiliconFlow API 集成，使用 DeepSeek-V3 模型进行对话
2. **MCP 客户端** (`mcp_client.py`) - 与 Model Context Protocol (MCP) 服务端通信的独立客户端

## MCP 客户端需求

### 项目概述
创建一个独立的 MCP (Model Context Protocol) 客户端 (`client.py`)，通过 HTTP SSE (Server-Sent Events) 与 MCP 服务端进行通信，支持工具调用、资源访问和提示词模板管理。

### 核心功能
- [ ] 通过用户输入获取 MCP SSE 服务 URL
- [ ] 建立 SSE 连接与 MCP 服务端通信
- [ ] 服务发现：获取服务端所有可用服务
  - [ ] Tools（工具）列表和调用
  - [ ] Resources（资源）列表和访问
  - [ ] Prompts（提示词模板）列表和使用
- [ ] 在 `run()` 方法中执行服务调用
- [ ] 实时接收服务端推送的事件和通知
- [ ] 错误处理和连接管理
- [ ] 交互式控制台界面

### 技术规格
- **通信协议**: JSON-RPC 2.0 over HTTP SSE
- **传输方式**: Server-Sent Events (SSE)
- **连接方式**: HTTP/HTTPS
- **消息格式**: JSON
- **启动方式**: `python client.py`
- **输入方式**: 运行时输入 MCP SSE 服务 URL

### 依赖包
- **官方 MCP 包**: `mcp>=1.0.0`
- **核心组件**:
  - `mcp.client.session.ClientSession` - 客户端会话管理
  - `mcp.client.sse.sse_client` - SSE 传输层实现
  - `mcp.types` - MCP 协议类型定义（Tool, Resource, Prompt）

### 服务类型支持
- **Tools**: 可调用的工具函数
- **Resources**: 可访问的资源（文件、数据等）
- **Prompts**: 提示词模板和参数化提示

### 实现架构
```python
# 主要组件结构
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool, Resource, Prompt

class MCPClient:
    def __init__(self, sse_url: str)
    def connect(self) -> bool
    def list_tools(self) -> List[Tool]
    def list_resources(self) -> List[Resource] 
    def list_prompts(self) -> List[Prompt]
    def run(self)  # 执行服务调用的主方法
```

---

## SiliconFlow API 客户端需求 (原有需求)

## 功能需求

### 核心功能（本次开发范围）
- [ ] 与 SiliconFlow API 建立连接和认证
- [ ] 调用 DeepSeek-V3 模型进行对话生成
- [ ] 支持单轮对话（单次问答）
- [ ] 支持多轮对话（会话上下文管理）
- [ ] 支持可配置的模型参数（温度、top_p、top_k等）
- [ ] 处理 API 响应和错误处理
- [ ] 支持思维模式（thinking mode）功能

### 暂不开发的功能
- 参数预设和模板功能
- 使用统计和监控
- 批量请求处理
- 持久化存储（数据库）
- Web API 接口

## 技术需求

### API 集成规格
- API 端点：https://api.siliconflow.cn/v1/chat/completions
- 认证方式：Bearer Token
- 请求方法：POST
- 内容类型：application/json

### 模型参数配置
- 模型：Pro/deepseek-ai/DeepSeek-V3
- max_tokens：512（可配置）
- enable_thinking：true（支持思维模式）
- thinking_budget：4096（思维预算）
- min_p：0.05（最小概率阈值）
- temperature：0.7（温度参数）
- top_p：0.7（核采样参数）
- top_k：50（top-k采样）
- frequency_penalty：0.5（频率惩罚）
- n：1（生成数量）

### 技术栈
- 编程语言：Python 3.8+
- HTTP 客户端：requests 库
- 配置管理：python-dotenv（环境变量）+ JSON配置文件
- 日志记录：Python logging 模块
- 依赖管理：pip + requirements.txt
- 项目结构：模块化设计
- 交互方式：控制台输入输出（input/print）

### 交互式控制台规格
- 启动方式：`python chat.py`
- 用户输入：通过 input() 函数获取用户消息
- 系统输出：通过 print() 显示 AI 回复
- 退出方式：输入 "quit"、"exit" 或 Ctrl+C
- 会话管理：自动维护多轮对话上下文
- 命令支持：支持特殊命令（如清除历史、显示参数等）

### 性能要求
- API 响应时间：< 30秒
- 并发请求支持：[待确认数量]
- 错误重试机制：指数退避策略

## 非功能性需求

### 安全性
- API Token 安全存储（环境变量，不硬编码）
- 输入参数验证和清理
- 错误信息不泄露敏感信息
- HTTPS 通信加密

### 可用性
- 清晰的错误提示和日志记录
- 配置文件易于修改和维护
- 模块化代码结构，便于扩展
- 完整的文档和使用示例

### 兼容性
- Python 3.8+ 版本兼容
- 跨平台支持（Windows、Linux、macOS）
- 标准库优先，最小化外部依赖

## 项目约束

### 时间约束
- 项目开始时间：2025年8月1日
- 预期完成时间：待确认
- 重要里程碑：
  - 基础 API 集成完成
  - 核心功能实现完成
  - 测试和文档完成

### 资源约束
- 开发语言：仅限 Python
- 外部依赖：最小化，优先使用标准库
- API 限制：受 SiliconFlow API 调用频率和配额限制

## 验收标准
- [ ] 成功调用 SiliconFlow API 并获得 DeepSeek-V3 模型响应
- [ ] 支持单轮对话（独立的问答交互）
- [ ] 支持多轮对话（维护会话上下文和历史）
- [ ] 支持所有指定的模型参数配置和调整
- [ ] 实现完整的错误处理和重试机制
- [ ] 通过环境变量安全管理 API Token
- [ ] 提供清晰的日志记录和错误信息
- [ ] 代码结构模块化，易于维护和扩展
- [ ] 包含完整的使用文档和示例代码
- [ ] 支持思维模式（thinking mode）功能

## 风险评估
- **API 服务不可用风险**：SiliconFlow API 服务中断或限流
  - 应对措施：实现重试机制、错误处理和降级策略
- **API Token 泄露风险**：认证凭据被意外暴露
  - 应对措施：使用环境变量存储，添加 .env 到 .gitignore
- **网络连接问题**：网络超时或连接失败
  - 应对措施：设置合理的超时时间和重试策略
- **参数配置错误**：模型参数设置不当导致异常
  - 应对措施：参数验证和默认值设置
- **依赖库兼容性**：第三方库版本冲突或不兼容
  - 应对措施：固定版本号，使用虚拟环境

---
*文档创建日期：2025年8月1日*
*最后更新：2025年8月1日*