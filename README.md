# Security Test Kit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent](https://img.shields.io/badge/Agent-Claude%20Code%20%7C%20Codex%20%7C%20Cline%20%7C%20Other-brightgreen)](#agent-兼容性)

**AI 驱动的安全测试工具包。** Agent 驱动，灰/黑盒自适应，确定性可复现，回归迭代进化。一项目一 kit。

> **定位**：提供一套**方法论**——在安全测试的**不确定性**中建立**确定性**。工具约定的是 6 个机制（用例历史 / 基线冻结 / 回归 diff / 证据规范化 / KPI / 红线），**不约定字段**；所有示例仅供参考，Agent 按目标系统架构自行发挥。

---

## 核心：在不确定性中建立确定性

每个目标系统架构都不同（签名层、认证方式、响应格式、角色体系），不存在能覆盖所有项目的固定用例或字段。确定性来自**机制**而非**预设字段**：

| 机制 | 作用 |
|------|------|
| 用例历史 | 回归的基础（每条用例记录历轮状态与证据） |
| 基线冻结 | diff 的基准（每轮冻结发现清单 + 覆盖 + 指纹） |
| 回归 diff | 判定修没修好、退没退化（fixed / still / regression / new） |
| 证据规范化 | 可比性（易变字段占位化） |
| KPI 趋势 | 度量进化（修复率 / 回归数 / 覆盖率） |
| 红线 | 安全边界 |

> **机制必须，字段自由，示例仅供参考。** 详细见 `SKILL.md`。

---

## 生命周期

```
冷启动 R0                    迭代 RN（回归+进化）
─────────                   ─────────────────────
clone + 放 materials        比对指纹（漂移?）
  ↓                           ↓
信息收集                    确定性重放基线用例
  ↓                           ↓
设计用例 → 执行 → 冻结基线    diff 四类状态
  ↓                           ↓
R0 报告 + KPI 初始化         提案新用例 → 确认 → 冻结
                              ↓
                           回归报告 + KPI 曲线
```

---

## 两种模式

| | 🏛️ 灰盒 | 🕵️ 黑盒 |
|------|------|------|
| `materials/` | 有设计文档 | 空 |
| 信息源 | 接口文档 + 线上探测 | 仅线上探测（JS 逆向、fuzz、报错推断） |

---

## 快速开始

```bash
git clone https://github.com/fangfireatom-byte/security-test-kit.git /path/to/your-project/security-test-kit
cd /path/to/your-project/security-test-kit
cp config/target.yaml.example config/target.yaml   # 可选，填入目标
cp api-docs.md materials/                            # 可选，灰盒
```

然后对 Agent 说：

```
使用 security-test-kit 对 <目标> 进行安全测试。
目标地址：https://example.com
```

Agent 读 `SKILL.md` 后自行判定模式、设计用例、执行、建基线、回归。无签名项目零依赖；有签名项目 Agent 可参考 `tools/sign.py`（也可弃用自写）。

---

## 目录结构

```
security-test-kit/
├── SKILL.md                  # 方法论 + 机制 + 生命周期（Agent 必读）
├── cases/
│   ├── 000-template.yaml     #   用例示例（参考，非模板）
│   ├── _baseline/            #   参考维度用例（示意，可自建/改写）
│   └── <project>/            #   项目专属用例（Agent 自行设计，不提交）
├── config/                   # 项目配置（.example 为参考模板）
├── tools/sign.py             #   签名辅助（参考实现，可弃用）
├── templates/                # 报告模板（参考）
├── materials/                # 设计文档（按项目放）
└── output/                   # 测试产出（基线/证据/报告，不提交）
```

---

## 红线

| 禁止 | 允许 |
|------|------|
| DoS / 高并发 | 低速率单次探测（默认 1 req/5s） |
| 破坏真实数据 | 只读探查 |
| 实际资金操作 | 0.01 元逻辑验证 |
| 高频短信轰炸 | 使用测试账户 |
| 大规模字典暴破 | 签名/加密逆向（公开前端 JS 范围内） |
| 修改他人账户 | 写操作须确认 |

---

## Agent 兼容性

指令文件为通用 Markdown/YAML/JSON，任何支持文件读取的 AI Agent 均可驱动：Claude Code / Codex / Cline / WorkBuddy / 其他。Agent 启动先读 `SKILL.md`，产出写入 `output/`，守住 6 个机制与红线，其余自由发挥。

---

## 贡献

欢迎补充参考维度、改进示例、增加签名适配案例。提 Issue 前请确认：不含真实项目敏感数据、案例已匿名化。

---

## 许可

MIT License — 详见 [LICENSE](LICENSE)
