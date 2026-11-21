# Security policy

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue.

* GitHub: **Security → Report a vulnerability** on this repository (private vulnerability reporting), or
* e-mail **Capalens@deffuture.com** (monitored by the project owner, 南京定义未来科技有限公司 / Nanjing Define
  Future Technology Co., Ltd.). If you need to encrypt, say so in a first plain message and we will arrange a key.

Include the version or commit, a minimal reproduction (a local test server or a small document is ideal) and
the impact you see. Never include real credentials, personal data or another party's private endpoints.

| Step | Target |
| --- | --- |
| Acknowledgement | 3 business days |
| Initial assessment | 10 business days |
| Fix for a confirmed issue | coordinated with the reporter; private until a release is available |
| Credit | in the release notes, with your consent |

## In scope

capalens-check itself: anything that makes it send more than read-only metadata requests, call a tool, follow a
redirect to another host, leak a credential into output or a report, execute content from a target, crash or hang
on hostile input (oversized, malformed or endless responses), or let a target influence the checks run against it.

## Out of scope

The security of the servers, documents or agents you check — report those to their owners. A `review`
candidate or a `pass` is not a vulnerability in capalens-check; if you believe a result is wrong, open a
"wrong result" issue.

## Using it safely

* Check endpoints you own or are allowed to test. The tool is read-only but it does send requests.
* Pass credentials through environment variables (`--bearer-env`, `bearerEnv` in a targets file), not on the
  command line; they are never written to reports.
* Treat reports as data about the target: they quote text the target wrote.
