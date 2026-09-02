# NanoCode Agent Design Route

NanoCode is designed from the landing route: define boundaries, choose tools, package skill-like workflows, add planning and reflection, manage memory, build safety rails, and evaluate.

## 1. Job Description

NanoCode is a local coding agent for small and medium repositories. Its job is to understand a user task, choose relevant context, edit files when needed, run verification, and return an auditable result. It must stay inside the configured workspace, avoid unsafe commands, protect secrets, and avoid claiming success without verification when verification is possible.

## 2. Toolbox

The toolbox is deliberately minimal: repository map, ranked search, file windows, patch editing, safe commands, test execution, git status inspection, and secret scanning. The model receives schemas; Python owns local execution.

## 3. Skills

NanoCode uses a lightweight SkillRegistry rather than an external agent framework. Task profiles such as code question, bug fix, feature change, test work, review, and refactor map to recommended workflows.

## 4. Planning and Reflection

A TaskClassifier creates a task profile. The planner selects a skill and writes a plan. ReAct then executes tools. Failed tool observations are classified by FailureAnalyzer so the next step is grounded in actual environment feedback.

## 5. Memory

Memory stores observations plus selected files, plan, task profile, and verification status. Recent observations remain intact; older ones are summarized.

## 6. Safety Rails

Workspace sandboxing controls file access. RiskPolicy assigns low, medium, or high risk to tools. Review mode is conservative; trust mode allows more automation but still blocks high-risk tools. Secret scanning and command blocking protect credentials and destructive actions.

## 7. Evaluation

Unit tests cover tools, memory, sandbox, planner, verifier, modes, and UI. Eval cases describe realistic and red-team scenarios so the project can be judged by task success, verified tests, unsafe-action blocking, and observability.
