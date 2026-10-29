# 贡献指南（CONTRIBUTING）

> 本项目的许可是 **PolyForm Shield 1.0.0**：可以自由使用、修改、分发（含商业用途），**唯一红线是不能拿它做与维护者竞争的产品**。这不是 OSI 开源许可。

## 一句话规则

| 你想做的事 | 是否允许 | 说明 |
| --- | --- | --- |
| 在项目里用 `ssstool`、公司内部用、商用 | ✅ | `pip install ssstool` / `uv add ssstool` |
| 改代码（自己用、内部用） | ✅ | 随便改 |
| 分发原版或修改版 | ✅ | 必须附带 [LICENSE](LICENSE) 或许可证 URL，保留 `Required Notice:` 行 |
| 把 ssstool 或其修改版做成竞品对外提供 | ❌ | 违反 Noncompete，许可证自动终止 |
| 分发时删掉许可证、冒充原创 | ❌ | 违反 Notices 义务 |
| 声称本项目是 open source | ❌ | 带非竞争限制，不满足 OSI 定义 |

## 竞争边界（按许可证原文，不是我的解释）

- **允许**：任何用途，包括商业用途、内部部署、二次开发。
- **禁止**：提供与 `ssstool` 或维护者基于 `ssstool` 提供的产品相竞争的产品。
- **判定很宽**：接口不同、平台不同、语言不同、**哪怕免费**，只要构成实际替代品就算竞争；按替代品营销则确定构成竞争。
- **保护期条款**：若维护者后来推出与你产品竞争的版本，你可继续使用当时已发布的旧版本，但不能升级到后续版本。
- 完整定义见 [LICENSE](LICENSE) 的 *Noncompete*、*Competition*、*New Products*、*Discontinued Products* 四节。

## 分发义务（容易踩）

1. 任何副本（含修改版）都必须带上 `LICENSE` 或指向许可证的 URL。
2. 许可证里的 `Required Notice:` 行必须原样保留，不得删除。
3. 不得暗示修改版获得原作者背书，不得使用 `ssstool` 名义发布非官方版本。

## 代码贡献

本项目采用 **inbound = outbound**：你提交的 PR，视为同意以 PolyForm Shield 1.0.0 授权你的贡献。流程：

1. **先开 issue**：说明问题、场景、期望行为；大于 200 行或涉及公共 API 的改动必须先对齐方向。
2. **维护者确认**：确认要做、边界没歧义。
3. **提 PR**：附测试（成功路径 + 失败路径），本地门禁全绿。
4. **维护者合并**：按 `AGENTS.md` 的 Definition of Done 检查后合入，并同步台账与能力文档。

> 不需要签 CLA；但如果你要提交的是你雇主拥有的代码，请先确认你有权授权。

## Issue 模板

```text
ssstool 版本：<ssstool --version>
环境：<ssstool doctor 的输出，注意脱敏本机路径>
复现步骤：
  1.
  2.
期望结果：
实际结果：
补充信息（日志/最小示例）：
```

## 安全与隐私

- `ssstool doctor` 会输出本机路径与解释器位置，贴到公开 issue 前请自行脱敏。
- 安全漏洞不要开公开 issue，走仓库 Security 页面或私下联系维护者。

## 维护者承诺

- 72 小时内给出 issue 首次响应（尽力而为，非 SLA）。
- 采纳的改动同步更新 `docs/LEDGER.md`、`docs/capabilities/README.md` 与相关文档。
- 拒绝的改动会说明原因，不做无声关闭。
