# ICode 使用指南

> 本文档面向已安装 icode-skill 的 Claude Code / Codex CLI 用户，说明如何使用已有的工程知识库（project_docs / module_docs）以及 icode 工作流的各项命令。

## 1. 数据目录结构

ICode 的全局数据存放在 `~/.claude/icode_data/`：

```
~/.claude/icode_data/
├── index.json              # 全局工单索引（首次运行自动创建）
├── project_docs/           # 工程级知识库（/icode doc 生成）
│   ├── mowerware_rl2601/   # 工程名 = git 根 basename
│   │   └── master/          # 分支名子目录（切分支不互相覆盖）
│   │       ├── 00_overview.md
│   │       ├── 10_architecture.md
│   │       └── ...
│   ├── fastmap/
│   ├── lightning-lm/
│   ├── navigationALG/
│   └── visionmowpnc/
└── module_docs/            # 模块共享文档（跨工程复用）
    ├── navigation_0a250a428bcb/
    │   ├── 00_overview.md
    │   └── ...
    └── ...（36 个模块）
```

**project_docs**：每个工程按 `<project_id>/<branch>/` 分目录，章节前 50 行自带元信息 + KEYS 检索词，段零检索时只读前 50 行粗筛、命中后按小节锚点定点读取。

**module_docs**：独立 git 子仓库的模块文档，按 `<repo_url_hash>+<branch>` 作 key 跨工程共享。同一上游仓库同分支只一份，多个工程引用时自动复用。

## 2. 当前已有知识库

| 工程 | 分支 | 章节数 |
|------|------|--------|
| mowerware_rl2601 | master | 37 |
| visionmowpnc | feature_dev_RL2601 | 24 |
| navigationALG | dev_lidar | 15 |
| lightning-lm | dev_no_ros | 11 |
| fastmap | grid3d_fixbug | 9 |

模块文档 36 个，覆盖 navigation、broker、mcu_communication、camera、system_manager 等子仓库。

> **v1 遗留布局**：`mowerware_rl2601/` 目录下同时存在 v1 平铺文件（`00_overview.md` 等直接在工程目录下）和 v2 分支子目录（`master/`）。下次对该工程跑 `/icode doc` 时会自动迁移到 v2 布局（`<project_id>/<branch>/`），旧文件保留备份。

## 3. 自动使用（段零检索）

**无需手动指定路径**。在对应工程目录下运行任何 icode 入口命令时，段零检索会自动读取已有的 project_docs / module_docs 并注入上下文。

### 工作原理

```
你在工程目录下执行 /icode start <需求>
         │
         ▼
① 解析 cwd 的 project_id（git 根 basename）+ 当前分支
         │
         ▼
② 读 project_docs/<project_id>/<branch>/ 各章节前 50 行 KEYS 做关键词匹配
         │
         ▼
③ 读 _meta.json 的 module_deps 列表 → 去 module_docs/<key>/ 读依赖模块文档
         │
         ▼
④ 命中的章节按小节锚点定点注入会话上下文（不灌全章，省 token）
         │
         ▼
⑤ plan / review / code 等步骤引用注入的工程知识做决策
```

### 使用示例

```bash
# 进入工程目录（project_id = git 根 basename，需与 project_docs 下的目录名一致）
cd /work/work_new/RL2601/mowerware_rl2601

# 全流程开发（plan → review → merge → code → deepcheck → audit）
/icode start 添加 OTA 断点续传功能

# 精简全流程（耗时约为全流程 65%，审查范围缩减）
/icode fast 修复 PIN 锁状态迁移边界问题

# 仅出计划
/icode plan 重构 mcu_communication 串口协议层

# 需求初稿对话（多轮对话产出需求文档）
/icode init

# 日志根因分析（把零散日志转化为有证据的根因报告）
/icode log 设备启动后 CAN 通信超时 dmesg 日志片段...
```

### 前提条件

- cwd 必须在 git 仓库内（`git rev-parse --show-toplevel` 能成功）
- git 根 basename 需与 `project_docs/` 下的目录名一致
- 当前分支需与 `project_docs/<project_id>/` 下的分支子目录名一致
- 如果当前分支没有知识库，段零会输出提示「本工程当前分支尚未生成知识库，可运行 `/icode doc`」，不阻塞流程

## 4. 主动维护知识库（`/icode doc`）

工程代码有大变更后，更新知识库：

```bash
cd /work/work_new/RL2601/mowerware_rl2601

# 增量更新当前工程（带增量词触发）
/icode doc 更新

# 全量重生成（会触发确认门，防止覆盖手动编辑）
/icode doc 全量重新生成

# 只更新某个模块的 module_docs（模块名为独立 git 仓库时）
/icode doc navigation

# 不带参数：全局扫描，列出各工程 stale 状态 + 建议动作，用户选择
/icode doc
```

### stale 检测机制

- `/icode doc` 末尾会自动扫描全库章节的 stale 状态（对比章节生成时的 commit 与当前 HEAD）
- 段零检索命中时也会做运行时 stale 校验
- stale 章节降级注入：只注摘要 + ⚠️ 警告，不注正文小节

## 5. 工单管理

### 查询工单

```bash
# 列出所有历史工单
/icode list

# 按工程过滤
/icode list --project /work/work_new/RL2601/mowerware_rl2601

# 按状态过滤
/icode list --status plan_done

# 按时间过滤
/icode list --since 7d

# 限制条数
/icode list --limit 10
```

### 查看当前工单状态

```bash
/icode status
```

### 标注工单结论

```bash
# 标注为已验证
/icode status --verdict mowerware_rl2601-1 verified "PIN 锁状态迁移方案已验证，双安全域架构生效"

# 标注为已证伪
/icode status --verdict mowerware_rl2601-1 disproved "原方案串口协议假设有误" --correct "应改为分帧协议"

# 批量扫描未标注的完成态工单
/icode status --scan-verdict
```

## 6. 项目约束红线（`/icode limit`）

维护工程级约束红线，作为 plan 步骤的硬基线：

```bash
cd /work/work_new/RL2601/mowerware_rl2601

# 查看当前约束
/icode limit

# 追加新红线
/icode limit 串口通信协议变更必须保持向后兼容，新增字段须有默认值

# 追加新红线
/icode limit OTA 升级失败必须保留旧固件可回滚
```

limit 存储在 `~/.claude/icode_data/limits/<project_id>.md`，跨 checkout 共享。plan 步骤会自动读取并作为设计基线。

## 7. 命令速查表

| 命令 | 用途 | 是否创建工单目录 |
|------|------|-----------------|
| `/icode init` | 多轮对话产出需求初稿 | ✅ 新建 |
| `/icode start <需求>` | 全流程（6 步串联） | ✅ 新建/复用 |
| `/icode fast <需求>` | 精简全流程 | ✅ 新建/复用 |
| `/icode plan <需求>` | 仅出计划 | ✅ 新建/复用 |
| `/icode log <日志>` | 日志根因分析 | ✅ 新建 |
| `/icode review [N]` | 仅审查（可指定轮次） | 用最新目录 |
| `/icode merge` | 仅合并审查意见 | 用最新目录 |
| `/icode code` | 仅编码实施 | 用最新目录 |
| `/icode deepcheck` | 仅三阶段复检 | 用最新目录 |
| `/icode audit` | 仅终审 | 用最新目录 |
| `/icode readme` | 生成交付报告 | 用最新目录 |
| `/icode doc [自然语言]` | 生成/维护工程知识库 | ❌ 写全局 project_docs |
| `/icode limit [自然语言]` | 维护项目约束红线 | ❌ 写全局 limits |
| `/icode list [关键词]` | 查询历史工单 | ❌ 纯只读 |
| `/icode status` | 查状态/标注 verdict | ❌ 默认只读 |

## 8. 注意事项

1. **段零文档不盲信**：注入的 project_docs / module_docs 是生成时的快照，可能因工程迭代过时。涉及代码行为、接口位置、调用链的断言，必须用 Read/Grep 实证当前代码后再纳入决策。
2. **分支隔离**：project_docs 按分支分目录，切换分支后段零只读当前分支的章节，不交叉读其他分支。
3. **module_docs commit 校验**：段零会比对工程 `_meta.json` 中 pin 的模块 commit 与 module_docs 的生成 commit，不一致时降级注入并附警告。
4. **Codex CLI 用户**：icode-skill 通过 `~/.codex/skills/icode-skill` 软链共享，`/icode` 命令在 Codex CLI 下通过 AGENTS.md 触发。如果 Codex 不支持 `/icode` 命令触发，可手动读取 `~/.claude/skills/icode-skill/SKILL.md` 按流程执行。
5. **产物目录**：工单产物写在工程根的 `.icode_output/` 目录下，不自动提交 git，建议在 `.gitignore` 中加入 `.icode_output/`。
