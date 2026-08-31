仓库地址：https://github.com/vqeavc-dot/nanocode-agent

NanoCode Agent 是一个轻量级编程智能体，目标是实现简化版 Claude Code/Codex。项目不使用 LangChain、AutoGen、OpenAI Agents SDK 等 Agent 框架，也不依赖 Code Interpreter 或 Files API；只使用普通 OpenAI 兼容模型接口。核心循环、工具定义、本地执行、上下文管理和错误处理均自行实现。

运行方式：安装 Python 3.10+，执行 pip install -e ".[dev]"，复制 .env.example 为 .env，填写 NANOCODE_API_KEY、NANOCODE_BASE_URL、NANOCODE_MODEL。之后运行 nanocode "你的编程任务" --verbose。测试执行 python -m pytest。

特色功能：参考 ReAct、SWE-agent ACI 和 aider RepoMap 思想，支持 ranked repo map、代码搜索、窗口式文件查看、Python/JS/TS/Java 符号分析、精确编辑、单文件 unified diff patch、文件写入和命令执行。系统通过工作目录沙箱、危险命令拦截、可选命令确认、命令超时、输出截断、最大循环步数和 Python 语法检查降低风险。运行时展示每一步并保存 run_logs，结束后输出 token 用量和 git diff 摘要；可选 --auto-commit 在观察到成功测试后提交改动。
