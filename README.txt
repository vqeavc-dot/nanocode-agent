Git 仓库地址：https://github.com/vqeavc-dot/nanocode-agent

如何运行：
安装 Python 3.10+，在仓库根目录执行 pip install -e ".[dev]"。复制 .env.example 为 .env，填写 NANOCODE_API_KEY、NANOCODE_BASE_URL、NANOCODE_MODEL。运行：nanocode "你的编程任务" --verbose --mode trust；界面：nanocode-ui；测试：python -m pytest。

特色功能：
NanoCode Agent 是从零实现的本地编程智能体，不使用 LangChain、AutoGen、OpenAI Agents SDK 等 Agent 框架，也不依赖 Code Interpreter 或 Files API。项目按“定边界→配工具→封 Skill→规划反思→记忆→安全→评估”设计，架构是 ReAct + 轻量 Planner + Skill-like Tools。系统先用 TaskClassifier 判断任务类型和风险，再由 SkillRegistry 选择代码问答、修复、功能、测试、审查或重构流程，随后进入模型-工具-observation 循环。

工具包括 repo_map、search_code、view_file、apply_patch_file、run_tests、secret_scan 等。RepoMap 压缩仓库结构并提取符号和依赖；Patch Editor 支持单文件 unified diff、上下文校验和语法回滚；Verifier 判断测试是否成功；FailureAnalyzer 对失败 observation 分类。

其它说明：
项目提供 review/trust 两种模式。review 默认保守，强调计划、命令确认和 diff 审查；trust 显式开启，且只有测试通过后才允许 --auto-commit。文件访问限制在 workspace 内，危险命令会被拦截。运行过程展示 mode、profile、skill、plan、tool_call、observation、reflect、verify、token、diff，并保存 run_logs。
