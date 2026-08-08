# Security Test Kit

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent](https://img.shields.io/badge/Agent-Claude%20Code%20%7C%20Codex%20%7C%20Cline%20%7C%20Other-brightgreen)](#agent-兼容性)

**AI 驱动的安全测试工具包。** 放设计文档就是灰盒，不放就是黑盒。复制到项目目录，一行指令启动测试。

---

## 设计理念

```
一个项目 = 一个 security-test-kit 目录
```

- 每个项目独立拥有一份工具包副本
- `materials/` 放该项目的设计文档，`output/` 出该项目的报告
- 测试产出随项目归档，不污染工具包仓库本身
- 零外部依赖，纯 Markdown 驱动，任何 AI Agent 都能读取

---

## 两种模式

| | 🏛️ 灰盒 | 🕵️ 黑盒 |
|------|------|------|
| `materials/` | 有设计文档 | 空 |
| 信息源 | 接口文档 + 线上探测 | 仅线上探测（JS 逆向、fuzz、报错推断） |
| 适合 | 内部系统安全审计 | 外部渗透测试 |

---

## 快速开始

```bash
# 克隆到你的项目
git clone https://github.com/fangfireatom-byte/security-test-kit.git /path/to/your-project/security-test-kit

# 放入设计文档（可选）
cp api-docs.md /path/to/your-project/security-test-kit/materials/

# 清理示例产出
rm -rf /path/to/your-project/security-test-kit/output/*
```

然后向 AI Agent 发送：

```
使用 security-test-kit 对 <目标> 进行安全测试。
目标地址：https://example.com
```

Agent 会**首先扫描 `materials/`**，有文档走灰盒，没有走黑盒。

---

## 目录结构

```
security-test-kit/
├── README.md                 # 本文件
├── LICENSE                   # MIT
├── SKILL.md                  # Agent 行为指令（核心）
├── materials/                # 设计文档（按项目放，不提交）
│   ├── README.md
│   └── .gitkeep
├── templates/                # 报告模板
│   ├── test-plan.md
│   ├── test-report.md
│   └── executive-summary.md
├── examples/                 # 匿名化案例
└── output/                   # 测试产出（按项目生成，不提交）
    └── .gitkeep
```

---

## 工作流程

```
P0 信息收集 → P1 制定方案 → P2 执行测试 → P3 输出报告
```

| 阶段 | 产出 | 需要确认 |
|------|------|:--:|
| P0 | 攻击面清单 | |
| P1 | `output/<项目>-测试方案.md` | ✅ 用户确认 |
| P2 | 用例执行记录 | |
| P3 | `output/<项目>-测试报告.md` + `一页摘要.md` | |

---

## 红线

| 禁止 | 允许 |
|------|------|
| DoS / 高并发 | 低速率单次探测 |
| 破坏真实数据 | 只读探查 |
| 实际资金操作 | 0.01 元逻辑验证 |
| 高频短信轰炸 | 使用测试账户 |
| 大规模字典暴破 | 签名/加密逆向（公开 JS） |

---

## Agent 兼容性

本工具包的指令文件为通用 Markdown，任何支持文件读取的 AI Agent 均可驱动：

- **Claude Code** — 直接读取 `SKILL.md`
- **OpenAI Codex** — 将 `SKILL.md` 作为 system prompt
- **Cline (VS Code)** — 导入目录作为 custom instruction
- **其他 Agent** — `SKILL.md` 为独立指令文件，直接作为上下文传入

核心约定：
1. Agent 启动时先扫描 `materials/`，判定灰盒/黑盒模式
2. `SKILL.md` 包含完整的 AI 行为规范，Agent 须严格遵守
3. 所有产出写入 `output/`，不修改 `templates/`

---

## 贡献

欢迎提交 PR 改进模板、补充测试维度、增加案例。

在提 Issue 前请确认：
- 不包含任何真实项目的敏感数据
- 案例使用了匿名化处理

---

## 许可

MIT License — 详见 [LICENSE](LICENSE)
