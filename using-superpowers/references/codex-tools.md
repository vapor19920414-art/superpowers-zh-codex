# Codex 工具映射

Skills 使用 Claude Code 的工具名称。在 Codex 中遇到这些名称时，请使用对应的平台等价工具：

| Skill 中的引用 | Codex 等价工具 |
|---------------|---------------|
| `Task` 工具（派遣子 agent） | `spawn_agent` |
| 多个 `Task` 调用（并行） | 多个 `spawn_agent` 调用 |
| Task 返回结果 | `wait_agent` |
| Task 状态检查 | `list_agents`；等待超时不代表子 agent 已失败 |
| `TodoWrite`（任务跟踪） | `update_plan` |
| `Skill` 工具（调用 skill） | Skills 原生加载——直接按说明操作 |
| `Read`、`Write`、`Edit`（文件） | 使用原生文件工具 |
| `Bash`（执行命令） | 使用原生 shell 工具 |

## 子 Agent 派遣

以**当前会话实际暴露且可调用的工具**为准。配置文件只能用于排查“为什么当前会话没有该工具”，不能单独证明子 agent 可用或不可用。

当任务简报已包含完整上下文、且需要隔离上下文时，调用 `spawn_agent` 应使用 `fork_turns="none"`；如果子 agent 必须理解最近对话，才选择最小必要的正数或 `all`。

部分 Codex 版本可通过以下配置启用多 agent：

```toml
[features]
multi_agent = true
```

配置生效后仍需重新启动会话，并检查当前工具面是否实际包含 `spawn_agent`、`wait_agent`、`list_agents` 等接口。只有当前接口确实提供清理/关闭工具时才调用；未提供时不要虚构 `close_agent`。
