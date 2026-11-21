# Related projects: how capalens-ia-check is positioned

[中文](#中文)

> **About this page.** This page compares **functional positioning**: what each project is for, what it looks
> at, how it works and what it produces, so that you can choose a tool or combine several. **It does not compare
> detection effectiveness.** No benchmark was run; nothing here says that one project finds more, fewer or better
> problems than another, and nothing here is a ranking. Each project is valuable for its own purpose. Descriptions
> follow each project's own description and README (checked on 2026-11-21) and may be out of date — corrections
> are welcome as an issue.

## Positioning at a glance

| Project | Its purpose (from its own documentation) | How capalens-ia-check is positioned differently |
| --- | --- | --- |
| [modelcontextprotocol/inspector](https://github.com/modelcontextprotocol/inspector) | The official developer tool for inspecting MCP servers: web UI, scriptable CLI, terminal UI; connects, lists and calls tools | Read-only by design (never calls a tool, stores no secrets); a pass/fail report against the specification with evidence, SARIF and exit codes; security screens; also OpenAPI, A2A and Skills |
| [modelcontextprotocol/conformance](https://github.com/modelcontextprotocol/conformance) | The official conformance tests for MCP | A small read-only subset that runs against any remote server, plus security screens; for full conformance, the official suite is the reference |
| [snyk/agent-scan](https://github.com/snyk/agent-scan) (formerly invariantlabs-ai/mcp-scan) | Discovers the agent components installed on your machine (harnesses, MCP servers, skills) and scans them for prompt injection, sensitive data handling and malware | Looks at the endpoints and documents you name rather than local installs; runs open word lists locally and sends nothing to a service; reports outcomes and evidence rather than scores |
| [cisco-ai-defense/mcp-scanner](https://github.com/cisco-ai-defense/mcp-scanner) | MCP security scanning with YARA rules, LLM analysis and the Cisco AI Defense API, plus code, package and readiness scanning | Uses no model and no service; puts protocol checks next to the security screens; each candidate carries the word and sentence that raised it |
| [a2aproject/a2a-inspector](https://github.com/a2aproject/a2a-inspector) | Validation tools for A2A agents: inspect Agent Cards and exchange messages | Command line and CI; validates cards from files or URLs without talking to the agent |
| [stoplightio/spectral](https://github.com/stoplightio/spectral) | A flexible JSON/YAML linter with rulesets for OpenAPI 2.0/3.0/3.1, Arazzo and AsyncAPI | Covers ten OpenAPI points that tool generation relies on, in the same report as MCP, A2A and Skills; for full OpenAPI style rules, a dedicated linter is the right tool |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) | The Agent Skills specification and documentation, with its reference validator | Applies the same front-matter rules and adds content screening and a listing of bundled executables |
| [ossf/scorecard](https://github.com/ossf/scorecard) | Security health metrics for open-source repositories, scored 0-10, with a GitHub Action and SARIF | Shares the CI shape (Action, SARIF, scheduled runs); its subjects are integrations rather than repositories, and it reports per-check outcomes with evidence instead of a score |

## Where the positions differ

The differences above come down to five design choices, none of which is better in general:

| Dimension | capalens-ia-check's choice | Other choices you will find |
| --- | --- | --- |
| What is examined | remote endpoints and documents you name | local installations, source code, packages, repositories |
| How it interacts | read-only metadata requests only | calling tools, exchanging messages |
| How it analyses | open word lists and specification rules, run locally | models, rule engines, hosted analysis services |
| What it reports | per-check outcomes with evidence; no score | findings with severities, scores, interactive views |
| Breadth vs depth | four kinds of Intelligent Access (IA) in one report | one protocol or format in depth |

## What this page is not

* Not a comparison of detection quality, accuracy, coverage or speed, and not a ranking.
* Not a claim that capalens-ia-check replaces any of these projects. Several are complementary: run the official
  MCP conformance suite for full conformance and a dedicated OpenAPI linter for style.
* Not a statement about CapaLens catalogue results or about any integration these tools examine.

## Why this tool reports no score

Scores serve well where many similar subjects are ranked on shared criteria, as Scorecard does for repository
practices. capalens-ia-check examines integrations an agent will call, where the property that matters differs
from case to case (does it authenticate? does a read-only tool describe deleting data?). It therefore reports
per-check outcomes with evidence and leaves the weighing to the reader — the same choice the CapaLens engine made
for its catalogue.

## Ideas taken, with thanks

* **Tool pinning** (mcp-scan, now Snyk Agent Scan): hashes of tool definitions to detect changes after approval.
* **Rule ids with references, SARIF output, a GitHub Action, scheduled runs** (Scorecard, Spectral).
* **Testing against the specification text** (the official conformance suite).

---

## 中文

> **关于本页。**本页对比的是**功能定位**：各项目用来做什么、检查什么对象、以什么方式工作、产出什么，便于你选择或组合使用合适的工具。**本页不对比检测效果**：
> - 没有做任何基准测试；
> - 不表示哪个项目发现的问题更多、更少或更准；
> - 不构成任何排名。
>
> 各项目在各自的定位上都有价值。描述依据各项目自己的简介和 README（2026-11-21 核对），可能已过时，欢迎通过 issue 更正。

### 定位一览

| 项目 | 它的定位（依据其自身文档） | capalens-ia-check 的定位差异 |
| --- | --- | --- |
| modelcontextprotocol/inspector | 官方 MCP 检查工具（Web 界面、可脚本化 CLI、终端界面），可连接、列出并调用工具 | 设计上只读（从不调用工具、不存储密钥）；对照规范输出带证据的 pass/fail 报告、SARIF 和退出码；有安全筛查；还覆盖 OpenAPI、A2A、Skills |
| modelcontextprotocol/conformance | MCP 官方一致性测试 | 可对任意远程服务器运行的只读子集，另加安全筛查；完整一致性以官方套件为准 |
| snyk/agent-scan（原 mcp-scan） | 发现本机已安装的智能体组件（客户端、MCP 服务器、Skills），扫描提示注入、敏感数据处理与恶意载荷 | 检查用户指定的端点和文档，而非本机安装；开源词表本地运行，不向任何服务发送数据；输出结论与证据而非分数 |
| cisco-ai-defense/mcp-scanner | 结合 YARA 规则、LLM 分析和 Cisco AI Defense API 的 MCP 安全扫描，另有代码、依赖包和就绪度扫描 | 不使用模型和外部服务；协议检查与安全筛查在同一份报告里；每个候选都给出触发它的词和句子 |
| a2aproject/a2a-inspector | A2A 智能体的校验工具：查看 Agent Card、收发消息 | 命令行和 CI 使用；从文件或 URL 校验 Card，不与智能体对话 |
| stoplightio/spectral | 灵活的 JSON/YAML 检查工具，带 OpenAPI、Arazzo、AsyncAPI 规则集 | 只做工具生成所依赖的 10 项 OpenAPI 检查，与 MCP、A2A、Skills 合在同一份报告；完整的 OpenAPI 风格规则应使用专门的检查工具 |
| agentskills/agentskills | Agent Skills 规范、文档及参考校验器 | 采用相同的前置元数据规则，另加内容筛查和可执行文件清单 |
| ossf/scorecard | 开源仓库安全健康度指标（0–10 分），提供 GitHub Action 和 SARIF | 借鉴其 CI 形态（Action、SARIF、定时运行）；检查对象是智能接入而非代码仓库，逐项给出结论与证据，不打分 |

### 定位差异的五个维度

这些差异归结为五个设计选择，没有哪一种在一般意义上更好：

| 维度 | capalens-ia-check 的选择 | 其他常见选择 |
| --- | --- | --- |
| 检查对象 | 用户指定的远程端点和文档 | 本机安装、源代码、依赖包、代码仓库 |
| 交互方式 | 只发只读的元数据请求 | 调用工具、收发消息 |
| 分析方式 | 本地运行的公开词表和规范规则 | 模型、规则引擎、托管分析服务 |
| 输出形式 | 逐项结论与证据，不打分 | 带严重级别的发现、评分、交互式界面 |
| 广度与深度 | 一份报告覆盖四类智能接入（IA） | 针对单一协议或格式做深 |

### 本页不是什么

* 不是检测质量、准确率、覆盖率或速度的比较，也不是排名。
* 不表示 capalens-ia-check 能取代上述任何项目。其中多个与本工具互补：完整的 MCP 一致性请使用官方套件，OpenAPI 风格检查请使用专门的检查工具。
* 不是对 CapaLens 目录结果或任何被检查接入的表态。
