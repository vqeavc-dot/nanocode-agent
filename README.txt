仓库地址：https://github.com/vqeavc-dot/nanocode-agent

NanoCode Agent 是一个轻量级编程智能体，架构为 ReAct + 轻量 Planner + Skill-like Tools。项目不使用 LangChain、AutoGen、OpenAI Agents SDK 等 Agent 框架，也不依赖 Code Interpreter 或 Files API；只使用普通 OpenAI 兼容模型接口。核心循环、工具定义、本地执行、上下文管理和错误处理均自行实现。

运行方式：安装 Python 3.10+，执行 pip install -e ".[dev]"，复制 .env.example 为 .env，填写 NANOCODE_API_KEY、NANOCODE_BASE_URL、NANOCODE_MODEL。之后运行 nanocode "你的编程任务" --verbose --mode trust；测试执行 python -m pytest。

特色功能：运行开始会生成轻量计划，随后进入模型-工具-observation 的 ReAct 循环。提供 review/trust 两种模式：review 默认保守，强调审查计划、命令确认和 diff；trust 需显式开启，适合演示，可在测试通过后 --auto-commit。参考 SWE-agent ACI 和 aider RepoMap 思想，支持 ranked repo map、代码搜索、窗口式文件查看、Python/JS/TS/Java 符号分析、单文件 unified diff patch、沙箱、危险命令拦截、命令超时、输出截断、语法回滚。运行时展示 plan、tool_call、observation、verify、token、diff，并保存 run_logs。
