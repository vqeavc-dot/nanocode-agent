仓库地址：https://github.com/vqeavc-dot/nanocode-agent

NanoCode Agent 是一个轻量级编程智能体，目标是实现简化版 Claude Code/Codex。项目不使用 LangChain、AutoGen、OpenAI Agents SDK 等 Agent 框架，也不依赖 Code Interpreter 或 Files API；只使用普通 OpenAI 兼容模型接口。核心循环、工具定义、本地执行、上下文管理和错误处理均自行实现。

运行方式：安装 Python 3.10+，执行 pip install -e ".[dev]"，复制 .env.example 为 .env，填写 NANOCODE_API_KEY、NANOCODE_BASE_URL、NANOCODE_MODEL。之后运行 nanocode "你的编程任务"。测试执行 python -m pytest。

特色功能：参考 ReAct 和 SWE-agent 的 Agent-Computer Interface 思想，支持代码搜索、窗口式文件查看、精确编辑、文件写入和命令执行。系统通过工作目录沙箱、危险命令拦截、命令超时、输出截断、最大循环步数和 Python 语法检查降低风险。支持 --verbose 展示每一步，并把运行轨迹保存到 run_logs，便于复盘和录制演示。内置 calculator 示例，可演示 Agent 自主读代码、改代码、补测试并运行 pytest 的完整闭环。
