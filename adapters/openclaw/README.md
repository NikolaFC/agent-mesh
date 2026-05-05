# OpenClaw Adapter for Agent Mesh

## 架构

OpenClaw 和 Hermes 是**对等关系**——各自独立运行，通过 Agent Mesh 共享状态。

```
┌──────────┐         ┌──────────┐
│ OpenClaw │ ◄─────► │  Hermes  │
│ (main)   │  对等    │ (codex)  │
└────┬─────┘         └────┬─────┘
     │                    │
     └────────┬───────────┘
              │
       .mesh/ (共享)
```

## 接入步骤

### 1. 确保 mesh CLI 可用

```bash
# 两个实例都需要
mesh --version  # 应该输出版本信息
```

### 2. 设置环境变量

在两个实例的启动配置中加入：

```bash
export MESH_ROOT=<workspace根目录>
```

### 3. OpenClaw 侧接入

已在 HEARTBEAT.md 中集成：
- Heartbeat 自动跑 `mesh pulse check`
- 发现 stale/blocked agent 时汇报
- 随时 `mesh status` 查看全部状态

### 4. Hermes 侧接入

在 Hermes 的启动文件或系统 prompt 中加入：

```markdown
## Agent Mesh 协作协议

本项目使用 Agent Mesh 做跨 agent 状态共享。

环境：
export MESH_ROOT=<workspace根目录>

开始前：
1. mesh status — 查看其他 agent 在做什么
2. mesh task list — 检查是否有相关 task

工作期间：
- 每次重要提交后：mesh pulse update --agent hermes --status working --task <id> --summary "做了什么"
- 遇到阻塞：mesh pulse update --agent hermes --status blocked --summary "为什么阻塞"

完成时：
1. mesh task history --id <id> --action committed --summary "完成内容"
2. mesh task update --id <id> --status <新状态> --progress <0-1>
3. mesh pulse update --agent hermes --status done --summary "任务完成"

你的 agent 名称：hermes
```

### 5. Git Hooks（可选）

自动在提交后更新 pulse：

```bash
cp hooks/post-commit .git/hooks/post-commit
chmod +x .git/hooks/post-commit
export MESH_AGENT=hermes  # 或 openclaw
```

## 验证

```bash
# 从任一实例运行
mesh status        # 应该看到两个 agent
mesh pulse check   # 检查是否超时
mesh validate      # 校验所有文件
```

## 协作模式

| 场景 | OpenClaw | Hermes |
|------|----------|--------|
| 开始 PR | `mesh task create` | `mesh pulse update --status working` |
| 提交代码 | — | `mesh task history --action committed` |
| CI 通过 | `mesh task update --status ci-pass` | — |
| 生产验证 | `mesh task history --action validated` | — |
| PR 合并 | `mesh task archive` | `mesh pulse update --status done` |

每个 agent 只写自己的 pulse，task 操作由 owner 负责。
