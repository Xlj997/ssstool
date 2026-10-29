# ssstool 文档中心

本目录记录 **ssstool 能干什么、怎么发版、为什么这么设计**。代码回答「怎么实现」，这里回答「为什么」和「边界在哪」。

## 文档地图

| 文档 | 回答什么问题 | 什么时候读 | 谁维护 |
| --- | --- | --- | --- |
| [capabilities/README.md](capabilities/README.md) | 现在到底有哪些能力？每个能力的状态？ | 接需求、对外介绍、判断能不能用 | 改能力的人 |
| [capabilities/version.md](capabilities/version.md) | 版本查询怎么用、边界在哪？ | 装完自检、排查版本不一致 | 改 CLI 的人 |
| [capabilities/doctor.md](capabilities/doctor.md) | 环境自检输出什么、能证明什么？ | 用户报「跑不起来」时 | 改 CLI 的人 |
| [capabilities/browser.md](capabilities/browser.md) | 怎么开/关带 CDP 的 Chrome、临时 profile 放哪、回收规则 | 需要接管浏览器时 | 改 browser 能力的人 |
| [architecture.md](architecture.md) | 目录结构、版本单一来源、CLI 与打包约定 | 动手改代码前 | 架构改动的人 |
| [LEDGER.md](LEDGER.md) | 每个版本改了什么、为什么、动了哪些文件、怎么验证 | 每次发版前、追溯历史决策 | 发版的人 |
| [release-process.md](release-process.md) | 从改版本号到 PyPI 上线要过哪些门 | 每次发版 | 发版的人 |
| [../AGENTS.md](../AGENTS.md) | 仓库硬约束与 DoD | 任何人动手前 | 项目所有者 |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 能用/不能用、分发义务与竞品边界 | 想提 issue 或 PR 前 | 项目所有者 |

## 写作规则

1. **一份文档只回答一类问题**。能力文档只讲「怎么用 + 边界」，不讲实现细节；实现细节进 `architecture.md`。
2. **示例必须可复制执行**并经过真实验证，输出与当前版本一致。改行为必须同步改示例。
3. **能力文档必须与代码同时改**：新增/删除/改参数/改退出码，都要更新文档；否则按缺陷处理（见 `AGENTS.md` 第 2 节第 3 条）。
4. **不写「将来会支持」**。未实现的能力只能出现在 `capabilities/README.md` 的「候选池」，并明确标注「未实现、不构成承诺」。
5. **中文正文**；命令、代码、输出保持原样（ASCII），不要翻译或替换引号。
6. **相对链接**优先，禁止写死 `https://github.com/.../blob/main/...` 指向仓库内文件（分支改名会全站死链）。

## 目录约定

```
docs/
├─ README.md                  本文件：文档地图 + 写作规则
├─ LEDGER.md                  工具发展台账（唯一版本事实来源）
├─ release-process.md         发布 SOP
├─ architecture.md            工程结构与技术约定
└─ capabilities/
   ├─ README.md               能力登记表（对外能力的唯一清单）
   ├─ _TEMPLATE.md            新能力文档模板
   ├─ version.md              能力：版本查询
   └─ doctor.md               能力：环境自检
```

新增能力文档：复制 `capabilities/_TEMPLATE.md` 为 `capabilities/<英文短名>.md`，并在 `capabilities/README.md` 登记表加一行。
