# capalens-check

**面向 AI 智能体所连接对象的只读检查工具：MCP 服务器、OpenAPI 文档、A2A Agent Card 和 Agent Skills。每条结果都附证据，不打分。**

[English](README.md) · [检查项清单](docs/checks.md) · [GitHub Action](docs/github-action.md) ·
[持续监测](docs/monitoring.md) · [报告格式](docs/report-format.md) · [方法说明](docs/methodology.md) ·
[同类项目对比](docs/comparison.md)

`capalens-check` 是 **CapaLens** 检测引擎的开源简化版。它快速、可重复地回答一个问题：*此刻对照这个接入自己的规范，能观察到什么？*

## 特点

* **一个工具覆盖四类 AI 接入。** 远程 MCP 服务器、工具背后的 OpenAPI 文档、A2A Agent Card、Agent Skill，用同样的方式检查，输出同样格式的报告。
* **只读、只在本地分析。**
  - 对 MCP 服务器，只发送握手和各类 `*/list` 请求、一次不存在方法的探测，最后结束会话。
  - **从不调用工具**，也不读取资源、不获取提示词。
  - 检查结果不会发给任何第三方；安全筛查是本机运行的词表。
* **给证据，不给分数。** 每条结果是以下五种之一，并附说明、证据和所依据的规范：
  - `pass`、`fail`、`review`、`unknown`、`skip`；
  - `review` 表示“需要人看一眼”的启发式候选，绝不是结论；
  - 没有分数、等级或徽章可刷。
* **为 CI 和持续监测设计。** 提供退出码，JSON、Markdown、SARIF 2.1.0 三种输出，以及 GitHub Action。还会固定 MCP 工具定义的指纹：定时运行时，工具描述被悄悄改动（“rug pull”）会变成待复核候选。
* **零依赖。** 只用 Python 标准库；读取 YAML 格式的 OpenAPI 时需另装可选的 PyYAML。

## 安装

需要 Python 3.10 及以上：

```bash
pipx install capalens-check                                   # 发布到 PyPI 之后
pipx install git+https://github.com/Capalens/capalens-check   # 直接从仓库安装
```

需要读取 YAML 的 OpenAPI 文档时：`pip install "capalens-check[yaml]"`。

## 十秒体验

```bash
capalens-check demo
```

`demo` 会做两件事：
1. 在 127.0.0.1 启动一个本地 MCP 演示服务器，分别检查“规范的”和“故意有风险的”两组工具；
2. 再检查内置的 OpenAPI 文档、Agent Card 和 Agent Skill。

全程不出本机。有风险的那组会演示失败项和待复核候选长什么样：
- 重名工具；
- 含空格的会话 id；
- 藏在 `<IMPORTANT>` 里、要求读取 `~/.ssh/id_rsa` 的指令；
- 不可见 Unicode 字符；
- 声明只读、描述里却在删除文件的工具。

## 用法

```bash
# 远程 MCP 服务器（Streamable HTTP）。令牌从环境变量读取，不出现在命令行里
export MCP_TOKEN=...
capalens-check mcp https://mcp.example.com/mcp --bearer-env MCP_TOKEN

# OpenAPI 3.0/3.1 文档、A2A Agent Card（只给域名时读取 /.well-known/agent-card.json）、Agent Skill
capalens-check openapi ./openapi.json
capalens-check agent-card https://agents.example.com
capalens-check skill ./skills/release-notes

# 一次检查多个目标，并与上一次的报告对比
capalens-check run capalens-targets.json --baseline last-report.json --json-out report.json
```

| 选项 | 含义 |
| --- | --- |
| `--format text\|json\|markdown\|sarif` | 屏幕输出格式（默认 text） |
| `--json-out` / `--markdown-out` / `--sarif-out` | 同时写出这些文件 |
| `--fail-on fail\|review\|unknown\|never` | 出现该级别及以上结果时退出码为 1（默认 fail） |
| `--baseline` | 上一次的 JSON 报告；MCP 工具定义有变化即标为 review（SEC-004） |
| `--timeout` / `--max-requests` | 单次请求超时（15 秒）和每个目标的请求预算（25 次） |
| `--bearer-env` / `--header` | 凭据；值会发送出去，但绝不打印、不写入报告 |

退出码：`0` 没有达到 `--fail-on` 的结果；`1` 有；`2` 用法或输入错误。

## 检查内容

共 39 项，分三层：**L0** 可达性与传输，**L1** 协议与格式，**L3** 安全候选。完整清单和规范链接见 [docs/checks.md](docs/checks.md)。

## 在 GitHub Actions 中使用

```yaml
- uses: Capalens/capalens-check@v0
  with:
    kind: openapi          # mcp | openapi | agent-card | skill | run
    target: openapi.yaml
```

可直接复制的工作流：[PR 检查](examples/github/capalens-pr.yml)、[定时监测](examples/github/capalens-monitor.yml)。

## 它不做什么

* 不证明一个接入安全或不安全：`pass` 是这次观察到的结果，`review` 是交给人看的候选。
* 不调用工具，不跟随外部 `$ref`，不验证 Agent Card 签名，不运行 Skill 脚本，不测业务行为。
* 不是完整的一致性测试。MCP 的完整测试请同时使用官方 [conformance](https://github.com/modelcontextprotocol/conformance)。
* 安全筛查读的是英文词，不是语义：带欺骗性的文本可能通过，无害的文本也可能被标出。

## 与 CapaLens 的关系

CapaLens 为 MCP 服务器、API、智能体、技能等 AI 接入建立有证据支撑的目录。它的检测引擎是完整的四层流水线，带签名、版本化的证据和人工复核。

`capalens-check` 取其中一部分检查和共享的启发式算法（`action-heuristic/3`、`poisoning-lexicon/0.1`），做成随处可运行的工具。本工具的结果不是 CapaLens 目录结果。

## 贡献、安全与许可

* 欢迎贡献：新增检查项、反馈误报、改进文档。见 [CONTRIBUTING.md](CONTRIBUTING.md)。
* 安全问题请私下报告，见 [SECURITY.md](SECURITY.md)。
* Apache License 2.0。版权所有 2026 南京定义未来科技有限公司。
