# Agent Mesh

**轻量级多 Agent 协作协议。**

> 当你在同一个项目里用 OpenClaw + Codex + Claude Code，每个 Agent 都是孤岛。Agent Mesh 是桥梁。

## 解决什么问题

你有多个 AI Agent 在同一个代码库里工作：
- **OpenClaw** 负责编排和记忆管理
- **Hermes**（基于 Codex）负责实现功能和修 Bug
- **Claude Code** 做代码审查和重构
- **Cursor** 在编辑器里

每个 Agent 有独立的上下文窗口，互相看不到对方的进度。你花在 Agent 之间复制上下文的时间，比真正写代码还多。

### 起源

这个项目诞生于真实痛点：OpenClaw 用 **Hermes**（一个基于 Codex 的 Agent）来实现上游 PR。每次 Hermes 完成一段工作，会写一份 22KB 的交接文档。OpenClaw 要解析这份文档，用 `gh pr view` 交叉验证，然后手动拼出当前状态。每次用户问"进展怎样？"，OpenClaw 都要重复这套流程。

Agent Mesh 用一条 `mesh status` 取代了这一切。

## 怎么解决

Agent Mesh 是一个**基于文件的共享状态层**。任何能读写文件的 Agent 都能参与，不需要服务器、API 或依赖。

```
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ OpenClaw │  │  Codex   │  │  Claude  │  │  Cursor  │
└────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │             │
     └─────────────┴─────────────┴─────────────┘
                         │
                  ┌──────┴──────┐
                  │  .mesh/     │  ← 共享状态，存在你的 repo 里
                  └─────────────┘
```

## 快速开始

```bash
# 1. 在你的项目里初始化
mesh init

# 2. 在任意 Agent 的 prompt 里加上：
#    "开始前，读 .mesh/pulse/*.json 和 .mesh/tasks/active/*.json。
#     完成工作后，更新你的 pulse 和 task history。"

# 3. 就这样，Agent 之间现在能共享状态了
```

## 共享什么

### 📡 Pulse — 实时心跳

每个 Agent 有一个 pulse 文件（`.mesh/pulse/{agent}.json`），显示它当前在做什么。

```bash
mesh pulse read --all          # 查看所有 Agent
mesh pulse update --agent codex --status working --task pr-77540
```

### 📋 Tasks — 工作项

追踪 PR、功能、Bug，带完整历史。每个 task 有一个 owner，其他 Agent 可以观察。

```bash
mesh task list                          # 所有活跃 task
mesh task create --id pr-77540 --title "cache lookups" --type upstream-pr --assign hermes
mesh task update --id pr-77540 --verdict ADOPT
mesh task history --id pr-77540 --action validated --summary "生产环境验证通过"
```

### 📚 Shared Knowledge — 持久上下文

项目级别的上下文、决策和阻塞项，存在 `.mesh/shared/` 里。

```bash
mesh shared read context.md
mesh shared append decisions.md --content "## [2026-05-05] Cache TTL = 1s，用于 RPC 调用"
mesh shared update context.md --content "# 新的项目上下文"
```

## 安装

```bash
# 从源码安装
git clone https://github.com/NikolaFC/agent-mesh.git
cd agent-mesh
chmod +x cli/mesh
ln -s $(pwd)/cli/mesh /usr/local/bin/mesh

# 或者直接复制 CLI 脚本
cp cli/mesh /usr/local/bin/mesh
```

### 依赖

- Python 3.8+（仅标准库）
- [GitHub CLI](https://cli.github.com)（`gh`）— 仅 `mesh sync` 需要

### 环境变量

如果工作目录不是项目根目录：
```bash
export MESH_ROOT=/path/to/project/root
```

## CLI 参考

| 命令 | 说明 |
|------|------|
| `mesh init` | 初始化 `.mesh/` 目录 |
| `mesh status` | 查看所有 Agent + 活跃 task 概览 |
| `mesh export [-o file]` | 导出 markdown 状态报告 |
| `mesh pulse read [--all]` | 读取 Agent pulse |
| `mesh pulse update` | 更新你的 Agent pulse |
| `mesh pulse check` | 查找超时 Agent（30 分钟无更新） |
| `mesh pulse clean` | 清理过期的 done/idle pulse |
| `mesh task create` | 创建新 task |
| `mesh task update` | 更新 task 状态/verdict/进度 |
| `mesh task assign` | 重新分配 task |
| `mesh task search` | 按关键词搜索 task |
| `mesh task history` | 追加 task 事件日志 |
| `mesh task list` | 列出 task（支持过滤） |
| `mesh task archive` | 归档 task |
| `mesh shared read` | 读取共享知识文件 |
| `mesh shared append` | 追加到共享文件（仅追加） |
| `mesh shared update` | 替换共享文件内容 |
| `mesh validate` | 校验所有 .mesh 文件 |
| `mesh sync [--repo]` | 从 GitHub 同步 PR 状态 |

## Agent 集成

### OpenClaw

```bash
# 在 cron 或 heartbeat 中：
mesh pulse read --all > /tmp/mesh-status.md
# 注入上下文或通知用户
```

### Codex / Claude Code

在 Agent prompt 中加入：
```
编辑代码前：
1. 运行 `mesh status` 查看其他 Agent 在做什么
2. 运行 `mesh task list` 检查相关 task
3. 完成工作后：`mesh task history --id <id> --action committed --summary "..."`
```

### GitHub Actions

```yaml
- name: PR 合并后更新 mesh
  run: |
    mesh task update --id pr-${{ github.event.number }} --status merged
    mesh task archive --id pr-${{ github.event.number }}
```

## Git Hooks

自动在每次提交后更新 pulse：

```bash
# 一次性设置
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit

# 或用 symlink 自动更新
git config core.hooksPath hooks
```

设置你的 Agent 名称：
```bash
export MESH_AGENT=hermes  # 或 codex, claude-code 等
```

## GitHub Actions 模板

PR 事件自动同步 mesh task：

```bash
cp .github/workflows/mesh-sync.yml <your-repo>/.github/workflows/
```

详见 [`.github/workflows/mesh-sync.yml`](.github/workflows/mesh-sync.yml)。

## 测试

```bash
python3 tests/test_cli.py
```

46 个测试覆盖：init、pulse CRUD、task 生命周期、assign、search、shared 文件、validate、export、pulse clean、MESH_ROOT 环境变量、schema 校验。

## 为什么用文件？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **文件（当前选择）** | 零依赖、git 原生、到处能用 | 基于约定 |
| SQLite | 查询友好 | 锁问题、不是所有环境都有 |
| HTTP API | 标准 | 需要服务器、不是所有 Agent 都有网络 |

文件胜出的原因：
- 每个 coding Agent 都能读写文件
- Git 免费提供版本历史
- `git log .mesh/` = 完整协作时间线
- 零运维成本

## Schema

完整的 JSON Schema 定义在 `schema/` 目录：
- [`pulse-v1.json`](schema/pulse-v1.json) — Agent 心跳 schema
- [`task-v1.json`](schema/task-v1.json) — Task 追踪 schema

协议规范：[`PROTOCOL.md`](PROTOCOL.md)

## 实际案例

这个项目诞生于真实需求：[OpenClaw](https://github.com/openclaw/openclaw) 使用多个 Agent——**OpenClaw** 作为主编排器，**Hermes**（基于 [Codex](https://github.com/openai/codex) 的 Agent）负责 PR 实现，Claude Code 做 review。在 Agent Mesh 之前，Hermes 每次完成工作都要写 22KB 的交接文档，OpenClaw 每次被问到进度都要重新解析。现在：

```
Hermes: "我刚 force-push 了 #77540"  →  更新 .mesh/pulse/hermes.json
OpenClaw: 读 pulse  →  知道 Hermes 在等 CI
Claude Code: 读 pulse  →  知道不要碰 #77540 区域
用户: mesh status  →  一眼看到全部
```

完整的 [OpenClaw + Hermes 工作流示例](examples/openclaw-hermes/README.md)。

## 参与贡献

1. Fork
2. 创建 feature 分支
3. 在 `.mesh/pulse/` 里加上自己（吃自己的狗粮）
4. 跑测试：`python3 tests/test_cli.py`
5. 提交 PR

## 协议

MIT
