# IA and IAP

[中文](#中文) · Source: the CapaLens guides
[What is Intelligent Access](https://capalens.com/en/guides/what-is-intelligent-access/),
[Understanding the IAP draft](https://capalens.com/en/guides/iap-protocol-draft/) and
[IAP: an evidence format for Intelligent Access](https://capalens.com/en/guides/iap-evidence-format/).
Where this page and the website differ, the website is current.

## IA — Intelligent Access

An AI can explain how to use a system without being able to connect to it, read its data or act in it. Doing
that needs a concrete entry point, the right runtime environment and permissions.

In CapaLens, **Intelligent Access (IA)** means the specific endpoints and access capabilities that an AI or a
large language model application can connect to, invoke or operate. It answers one practical question:
*through which entry points can an AI use which external capabilities?*

| Form | The entry point | What matters when connecting |
| --- | --- | --- |
| MCP | an MCP server offering tools, resources and prompt templates | server identity, transport, client compatibility, authorization |
| API | a program interface that takes requests and returns results | address, methods, inputs and outputs, authentication, limits |
| CLI | a command-line tool used in a terminal or script | installation, arguments, runtime, output and exit status |
| SDK | a software development kit for one programming environment | package and version, language, initialisation, usage |
| Remote connection | an entry to a remote host or execution environment | target environment, protocol, identity, permissions, scope |
| Agent Skills, agent-to-agent (A2A) | packaged capabilities and agents other agents can call | the declared capabilities, inputs, permissions and interfaces |

Three things to keep in mind:

* **IA is a category of capability, not one protocol.** MCP is one protocol among the forms; an SDK may wrap
  an API, an MCP server may call an API inside. Forms differ, the business capability behind them may overlap.
* **"Intelligent" describes the entry point's place in AI workflows.** The service itself need not contain a
  model: a conventional tool with a clear connection or invocation path, usable by an AI application within its
  authorization, is IA too.
* **Calling something IA says nothing about quality.** Being listed as IA does not mean it was tested or is safe.

Description files are not IA by themselves: an OpenAPI document describes an API, an A2A Agent Card describes an
agent. They are evidence that the IA can be discovered and understood, and they are worth checking for exactly
that reason.

## IAP — Intelligent Access Protocol (draft)

**IAP is an early proposal by the CapaLens project.** It aims to give the capability descriptions, verification
evidence and trust assessments of IA a shared data language, so that people and AI can see a tool's boundaries,
applicable conditions and open questions *before* using it. It is a project proposal: **not an adopted industry
standard, not part of MCP**, and its design statements are not proof of any service's capabilities.

### Where it fits

An integration passes four links of a safety chain between being published and being called:

1. **Identity** — who published it (registries help with namespace ownership).
2. **Definition** — what the tool does, which permissions it needs, what changed between versions.
3. **Runtime** — permissions and isolation at call time (gateways, clients, security products).
4. **Audit** — accountability afterwards (enterprise logs).

IAP is meant for the definition link. **It is not another calling protocol** and replaces neither MCP nor
registries: a registry helps discover *what exists*; IAP records *the evidence for relying on it* — version,
conditions, permissions, test results, check date and evidence source.

### The draft's four layers

| Layer | What it describes | What to examine when using it |
| --- | --- | --- |
| Capability description | node identity, access type, capabilities, inputs, side effects, risks, confirmation requirements | which capability and version the statement covers, and whether it fits the task |
| Evidence | protocol conformance, functional tests, security checks, proposed tracking of change over time | scope, method, environment, time, results and what was not covered |
| Trust credentials | verifiable statements an issuer makes about a subject and its evidence | whether the issuer is trusted, the evidence matches, the credential is valid |
| Governance and audit | call-chain records and governance support for combined use | who judged, on what basis, and how it should be read |

The four layers are related; none replaces another.

### Evidence-format principles

* **Version and check date.** Evidence belongs to the tested version, conditions and date; when versions or
  permissions change, old evidence is marked "re-test pending".
* **Evidence levels labelled, never blended.** Machine checks, human confirmation and AI self-reports have
  different sources and scopes; each is labelled, and there is **no composite score**.
* **Three-state conditions: met / unmet / unknown.** Unknown is written as unknown: no guessing, no defaults.

## How capalens-ia-check relates

capalens-ia-check checks four kinds of IA material — MCP servers, OpenAPI documents, A2A Agent Cards and Agent
Skills — and writes machine-check evidence that follows the IAP evidence-format principles:

| IAP evidence-format principle | In a capalens-ia-check report |
| --- | --- |
| Evidence tied to a version and a check date | `target`, `startedAt` / `finishedAt`, `facts.protocolVersion`, `facts.serverInfo`, a SHA-256 per tool definition |
| Evidence levels labelled, no composite score | every result is a machine check; heuristics only ever produce `review` candidates; there is no score field |
| Met / unmet / unknown | outcomes `pass` / `fail` / `unknown` (plus `review` and `skip`) |
| Changes mark old evidence for re-testing | `--baseline`: a changed, added or removed MCP tool definition becomes `review` (SEC-004) |
| Evidence source recorded | each result's `reference` (the specification) and `evidence` |

capalens-ia-check **does not emit IAP records** and issues no trust credentials. When the IAP evidence format is
published as a schema, an export is the natural next step.

---

## 中文

来源：CapaLens 网站指南[《什么是智能接入》](https://capalens.com/zh/guides/what-is-intelligent-access/)、
[《认识 IAP 智能接入协议草案》](https://capalens.com/zh/guides/iap-protocol-draft/)、
[《IAP：智能接入协议的证据格式设计与考虑》](https://capalens.com/zh/guides/iap-evidence-format/)。本页与网站不一致时，以网站为准。

### IA：智能接入

在 CapaLens 的语境中，**智能接入（Intelligent Access，简称 IA）**是指能够通过 AI 或大模型应用连接、调用或操作的具体端点与入口能力。它涵盖 MCP、API、CLI、SDK、远程连接等形式，回答一个实际问题：AI 可以通过什么入口，使用哪些外部能力？

* 智能接入是一类能力，不是某一种协议。MCP 是其中一种具体协议；不同形态背后的业务能力可能重叠。
* “智能”描述的是入口与 AI 工作流的关系，不要求被接入的服务本身内置大模型。
* 被称为智能接入，不代表已经测试或做了安全背书。
* OpenAPI 文档、A2A Agent Card 这类描述文件本身不是智能接入，而是“能否被发现、能否看懂”的证据，因此值得检查。

### IAP：智能接入协议（草案）

**IAP（Intelligent Access Protocol）是 CapaLens 项目提出的早期协议提案。**它希望让智能接入的能力说明、核查证据与信任判断拥有共同的数据语言，帮助人和 AI 在使用工具之前，看清能力边界、适用条件与尚未确认的问题。

IAP **不是已获行业组织采纳的正式标准，也不是 MCP 的组成部分**；设计说明不能代替具体服务的能力证据。

**定位：**
- 它不是另一个调用协议，不替代 MCP，也不替代注册中心。
- 注册中心帮助发现“有哪些”，IAP 记录“关于一条接入的证据”：版本、条件、权限、测试结果、检查日期、证据来源。
- 在“身份—定义—运行—审计”这条安全链中，IAP 面向“定义”这一环。

**草案的四个层次：**
- 能力描述层；
- 证据层；
- 信任凭证层；
- 治理与审计层。

四者相互关联，不能互相替代。

**证据格式的三条原则：**
1. 证据绑定适用版本和检查日期；版本或权限变化后，旧证据标为“待复测”。
2. 机器检测、人工确认、AI 自述分开标注，不合成总分。
3. 条件三态：已满足、未满足、未知；未知就写未知。

### 与 capalens-ia-check 的关系

capalens-ia-check 检查四类智能接入资料：MCP 服务器、OpenAPI 文档、A2A Agent Card、Agent Skills。它产出的是机器检测证据，遵循 IAP 证据格式的上述原则：
- 结果绑定检查对象与时间；
- 只有机器检测，启发式只给出 review 候选；
- 没有分数字段；
- 未知保留为 unknown；
- 工具定义一旦变化，就标为待复核（`--baseline`）。

它**不输出 IAP 记录，也不签发信任凭证**。等 IAP 证据格式以 Schema 形式公开后，增加导出是自然的下一步。
