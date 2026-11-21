# capalens-ia-check

[![Website](https://img.shields.io/badge/website-capalens.com-0b6fbf)](https://capalens.com)
[![CI](https://github.com/DefineFuture/capalens-ia-check/actions/workflows/ci.yml/badge.svg)](https://github.com/DefineFuture/capalens-ia-check/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab)

**面向智能接入（IA）的只读检查工具：AI 所连接的 MCP 服务器、API、智能体与技能。每条结果都附证据，遵循 IAP 证据格式的原则，不打分。**

[官网](https://capalens.com) · [IA 与 IAP](docs/ia-and-iap.md#中文) · [Wiki：思路理念](https://github.com/DefineFuture/capalens-ia-check/wiki) · [English](README.md) · [检查项清单](docs/checks.md) · [GitHub Action](docs/github-action.md) ·
[持续监测](docs/monitoring.md) · [报告格式](docs/report-format.md) · [方法说明](docs/methodology.md) ·
[同类项目定位差异](docs/comparison.md#中文)

`capalens-ia-check` 是 **CapaLens** 检测引擎的开源简化版。它快速、可重复地回答一个问题：*此刻对照这个接入自己的规范，能观察到什么？*

## IA 与 IAP

> **IA：智能接入（Intelligent Access）。**在 CapaLens 的语境中，指能够通过 AI 或大模型应用连接、调用或操作的具体端点与入口能力，涵盖 MCP、API、CLI、SDK、远程连接、技能等形式。“智能”描述的是入口与 AI 工作流的关系，不要求服务本身内置大模型；被称为智能接入，不代表已经测试或做了安全背书。
>
> **IAP：智能接入协议（Intelligent Access Protocol，草案）。**CapaLens 项目提出的早期协议提案，希望让智能接入的能力说明、核查证据与信任判断拥有共同的数据语言。它不是另一个调用协议，不替代 MCP，也不替代注册中心：注册中心回答“有哪些”，IAP 记录“关于一条接入的证据”，包括版本、条件、权限、测试结果、检查日期和证据来源。IAP **不是已获采纳的行业标准，也不是 MCP 的组成部分**。

| | IA（智能接入） | IAP（智能接入协议，草案） |
| --- | --- | --- |
| 是什么 | AI 使用外部能力的入口：MCP、API、CLI、SDK、远程连接、技能、智能体 | 关于一条智能接入的证据的数据语言（草案） |
| 回答的问题 | AI 可以通过什么入口，使用哪些外部能力？ | 这条接入是什么、在什么条件下、有哪些依据？ |
| capalens-ia-check 做什么 | 检查四类智能接入资料：MCP 服务器、OpenAPI 文档、A2A Agent Card、Agent Skills | 产出遵循 IAP 证据原则的机器检测证据：绑定版本和时间、未知写未知、不合成总分（暂不输出 IAP 记录） |

延伸阅读：[IA 与 IAP](docs/ia-and-iap.md#中文) ·
[什么是智能接入](https://capalens.com/zh/guides/what-is-intelligent-access/) ·
[认识 IAP 智能接入协议草案](https://capalens.com/zh/guides/iap-protocol-draft/) ·
[IAP 证据格式](https://capalens.com/zh/guides/iap-evidence-format/)

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

需要 Python 3.11 及以上：

```bash
pipx install capalens-ia-check                                   # 发布到 PyPI 之后
pipx install git+https://github.com/DefineFuture/capalens-ia-check   # 直接从仓库安装
```

需要读取 YAML 的 OpenAPI 文档时：`pip install "capalens-ia-check[yaml]"`。

## 十秒体验

```bash
capalens-ia-check demo
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
capalens-ia-check mcp https://mcp.example.com/mcp --bearer-env MCP_TOKEN

# OpenAPI 3.0/3.1 文档、A2A Agent Card（只给域名时读取 /.well-known/agent-card.json）、Agent Skill
capalens-ia-check openapi ./openapi.json
capalens-ia-check agent-card https://agents.example.com
capalens-ia-check skill ./skills/release-notes

# 一次检查多个目标，并与上一次的报告对比
capalens-ia-check run capalens-targets.json --baseline last-report.json --json-out report.json
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
- uses: DefineFuture/capalens-ia-check@v0
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

[CapaLens](https://capalens.com) 为 MCP 服务器、API、智能体、技能等 AI 接入建立有证据支撑的目录。它的检测引擎是完整的四层流水线，带签名、版本化的证据和人工复核。

`capalens-ia-check` 取其中一部分检查和共享的启发式算法（`action-heuristic/3`、`poisoning-lexicon/0.1`），做成随处可运行的工具。本工具的结果不是 CapaLens 目录结果。

## 贡献、安全与许可

* 欢迎贡献：新增检查项、反馈误报、改进文档。见 [CONTRIBUTING.md](CONTRIBUTING.md)。
* 安全问题请私下报告，见 [SECURITY.md](SECURITY.md)。
* Apache License 2.0。版权所有 2026 南京定义未来科技有限公司。
