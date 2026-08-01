# Codex Skills 触发速查与配置追溯

> 本文档记录 Codex CLI 与 Claude Code 的 skills 触发机制差异、各 skill 的自然语言触发方式，以及适配工作的完整变更记录，便于后续追溯。

## 文档信息

| 项 | 值 |
|----|-----|
| 创建日期 | 2026-07-13 |
| 版本 | v1.3 |
| 适用范围 | Codex CLI 0.144.1 + Claude Code（skills 共享） |
| 关联配置 | `~/.codex/AGENTS.md`、`~/.claude/skills-codex-patch.py`、memory: `codex-skills-trigger-mechanism` |

---

## 一、背景：两套 CLI 的 skills 触发机制差异

用户同时使用 Claude Code 和 Codex CLI 0.144.1，skills 目录通过软链接共享：
- 源目录：`~/.claude/skills/`（superpowers-zh 安装位置）
- Codex 目录：`~/.codex/skills/*`（软链指向 `~/.claude/skills/*`）

两套工具的 skills 触发机制不同：

| 维度 | Claude Code | Codex CLI |
|------|-------------|-----------|
| `/skill-name` 斜杠命令 | ✅ 支持（按目录名注册） | ❌ 不支持（`/` 菜单只列内置命令） |
| 触发方式 | `/命令` 手动唤醒 + description 自动触发 | 仅靠 description 语义自动触发 |
| description 作用 | 自动触发的依据之一 | **唯一触发依据** |

**关键结论**：
- Codex 的 skills 靠 SKILL.md frontmatter 的 `description` 字段做语义自动触发
- 官方 skill-creator 文档明确："description is the primary triggering mechanism"
- 软链接本身 Codex 能正常识别（实测 `codex exec` 能列出全部 skills），无需改真实目录
- SKILL.md 的 description 里若写"仅当用户显式 /xxx 时调用"，在 Codex 里会形成**死锁** -- skill 被加载但触发条件永远无法发生

---

## 二、Codex Skills 触发速查

**核心规则**：用自然语言说清楚"要做什么"，不要打 `/命令`。Codex 按 description 自动匹配 skill。

### 1. 开发全流程（需求 -> 计划 -> 实现 -> 调试 -> 验证 -> 收尾）

#### brainstorming（需求梳理）
- 该说什么：`先梳理下这个功能的需求和设计` / `这个需求有点模糊，先探索清楚再实现` / `帮我做需求分析`
- 触发标志：先提问澄清意图，不直接写代码

- 使用高级模型（gpt-5.6-sol + High）复核需求文档
基于 docs/superpowers/specs/2026-07-30-ota解耦与进度汇总架构评审.md，结合仓库已有相关代码双向交叉复核：
1、逐条校验状态流转、HMI 与 MCU 通信机制、版本兼容约束，识别内部逻辑冲突；
2、梳理文档缺失的异常场景、边界用例、可落地验收标准；
3、重点排查本次接口ABI变更引入的前后向兼容风险（新旧版本混搭风险优先识别）；
4、输出精简评审意见，严格禁止发散、新增需求与额外方案设计，仅基于现有文档与代码查漏补缺；
5、综合兼容性、异常覆盖、验收项、版本约束维度，评估当前方案文档是否满足工程落地条件，并给出明确结论。

评审意见分级标注：【严重风险｜轻微缺失｜合规无问题】

#### writing-plans（方案设计）
- 该说什么：`出个实现方案再动手` / `写个多步骤实现计划` / `这个任务先规划步骤`
- 触发标志：产出书面计划/步骤清单，不直接编码

#### executing-plans（按计划编码）
- 该说什么：`按这个计划编码实现` / `执行上面的实现计划，设审查检查点`
- 触发标志：按计划逐步实现，带审查节点

#### systematic-debugging（系统排障）
- 该说什么：`这个 bug 先系统排查再修` / `先定位根因，别急着改` / `测试失败了，系统分析下原因`
- 触发标志：先调查根因再出修复方案，不急于改代码

#### compressing-large-context（压缩上下文节省tonken）
- 该说什么：`分析上千行编译日志` / `读取500行以上驱动源码` / `全仓检索代码定位问题` / `查看多文件大型diff变更` / `解析大容量JSON配置`
- 触发标志：任务涉及超大行数源码、长日志、批量检索、多文件 diff、大 JSON；优先限流缩小读取范围，自动调用 headroom 压缩，精准定位时再取回完整原文，任务结束统计 token 节省量

#### verification-before-completion（交付验证）
- 该说什么：`完成前先跑验证确认` / `宣称完成前用证据支撑` / `提交前先验证测试通过`
- 触发标志：运行验证命令并确认输出后才说"完成"

#### finishing-a-development-branch（分支收尾）
- 该说什么：`功能做完了，怎么收尾` / `测试通过了，决定下合并还是 PR`
- 触发标志：给出合并/PR/清理的结构化选项

### 2. 代码评审

#### chinese-code-review（中文 review）
- 该说什么：`用中文规范 review 这段代码` / `帮我做中文代码评审`
- 触发标志：必须修复 / 建议修改 / 仅供参考 分级标注

#### requesting-code-review（发起 review）
- 该说什么：`帮我发起代码审查` / `验证下这个功能是否符合要求`
- 触发标志：主动用 review 视角验证工作成果

#### receiving-code-review（处理 review 反馈）
- 该说什么：`收到 review 意见了，先评估再改` / `这条反馈有疑问，先技术验证`
- 触发标志：对反馈做技术严谨评估，不敷衍附和或盲从

### 3. Commit 规范

#### chinese-commit-conventions（中文 commit）
- 该说什么：`帮我写个中文 commit` / `生成中文 commit message` / `配下中文 commitlint`
- 触发标志：`类型(范围): 描述` 的 Conventional Commits 中文格式

#### english-commit-conventions（英文 commit）
- 该说什么：`写个英文 commit，关联 SRT-986` / `生成英文 commit message`
- 触发标志：英文 Conventional Commits 格式 + Jira ticket 关联

### 4. 文档与 Git 平台

#### chinese-documentation（中文文档排版）
- 该说什么：`检查这段中文文档的中英文空格和标点` / `做下中文文档排版`
- 触发标志：中英文空格 / 全半角标点修正

#### chinese-git-workflow（国内 Git 平台）
- 该说什么：`帮我配 Gitee 的 SSH 凭据` / `配置极狐 GitLab 的 CI` / `做 Gitee 和 GitHub 的镜像同步`
- 触发标志：国内平台（Gitee/Coding.net/极狐 GitLab/CNB）SSH/HTTPS/凭据/CI 配置

### 5. 测试与隔离

#### test-driven-development（TDD）⚠️ 仅用户明确要求时触发
- 该说什么：`写单测` / `补充测试用例` / `完善测试覆盖`（必须明确要求，功能开发中不自动触发）
- 触发标志：仅在用户明确要求写测试时介入；功能开发流程中不自动写测试

#### using-git-worktrees（worktree 隔离）
- 该说什么：`开个隔离工作区开发这个功能` / `用 git worktree 隔离开发`
- 触发标志：创建/使用 git worktree 隔离工作区

### 6. 并行与子代理

#### dispatching-parallel-agents（并行子任务）
- 该说什么：`这几个独立任务并行处理` / `拆成独立子任务并行做`
- 触发标志：2+ 独立无依赖任务并行派发

#### subagent-driven-development（子代理执行计划）
- 该说什么：`用子代理执行这个实现计划` / `当前会话里按计划用子代理推进`
- 触发标志：当前会话内子代理执行计划任务

### 7. 工具/元技能

#### mcp-builder（构建 MCP 服务器）
- 该说什么：`帮我构建一个 MCP 服务器` / `系统化做个 MCP 工具`
- 触发标志：MCP 服务器构建方法论

#### writing-skills（创建/编辑 skill）
- 该说什么：`创建一个新 skill` / `编辑现有 skill 并验证`
- 触发标志：skill 创建/编辑/验证流程

#### using-superpowers ⚠️ Codex 基本不触发
- description 引用 Claude Code 的 `Skill 工具`，Codex 无此工具。Codex 里可忽略，不影响其他 skill 使用。

#### workflow-runner ⚠️ Codex 未明确支持
- description 限定 Claude Code/OpenClaw/Cursor，未提 Codex。提供 `.yaml` 工作流文件时可能触发，但不保证。

### 触发不灵时的技巧

1. **意图说具体**：不要只说"review"，说"用中文规范 review 这段代码：`int a=0;`"
2. **带上关键词**：`中文规范` / `先写测试` / `系统排查` / `验证后再完成` / `Gitee SSH` / `中文 commit`
3. **直接点明场景**：`配 Gitee SSH` / `写中文 commit` / `检查中英文空格` / `先做需求分析`
4. **查可用 skills**：`codex exec "列出你的 skills"`
5. **skill 没触发就明说**：`用 chinese-code-review 的方式 review 这段代码` -- 直接点名 skill 也能触发

### icode-skill 暂停后的替代

icode-skill 暂停使用（/icode 子命令体系在 Codex 无效），其承担的 5 个环节由独立 skill 接替：
- 需求梳理 -> brainstorming
- 方案设计 -> writing-plans
- 编码实现 -> executing-plans
- 排障根因 -> systematic-debugging
- 交付验证 -> verification-before-completion

---

## 三、本次适配变更记录（2026-07-13）

### 问题诊断
- 现象：Codex CLI 里 `/` 菜单看不到 skills，无法用 `/skill-name` 唤醒
- 根因：Codex 不支持自定义斜杠命令，skills 靠 description 自动触发；而多个 SKILL.md 的 description 写了"仅当用户显式 /xxx 时调用"，在 Codex 里形成死锁

### 变更内容

| 变更项 | 说明 |
|--------|------|
| 6 个 SKILL.md description 改 Codex 兼容触发 | chinese-code-review、chinese-commit-conventions、chinese-documentation、chinese-git-workflow、english-commit-conventions（去掉 /xxx 死锁，改语义触发）、test-driven-development（改仅显式触发，不自动写测试） |
| CLAUDE.md 同步更新 | "可用 Skills"一节对应 4 行 + 第 204 行（icode 暂停、5 个 skill 恢复） |
| 恢复 5 个被删 skill | brainstorming、writing-plans、executing-plans、systematic-debugging、verification-before-completion（从 superpowers-zh v1.6.0 包提取，description 本就是语义触发） |
| AGENTS.md 独立维护 | 断开 `~/.codex/AGENTS.md -> CLAUDE.md` 软链，写 Codex 专用版（去除 /skill、/icode、Skill 工具等 Claude Code 专属内容，新增 Codex skills 触发机制说明） |
| 补丁脚本 | `~/.claude/skills-codex-patch.py`（idempotent），重装 superpowers-zh 后跑一次恢复 6 个 Codex 兼容改动 |
| TDD 测试约束 | CLAUDE.md/AGENTS.md 新增 TDD 测试约束节（禁止自动写测试，仅用户明确要求时写）；test-driven-development skill description 改为仅显式触发；补丁脚本同步加入 TDD 条目 |
| memory | `codex-skills-trigger-mechanism.md` 记录机制差异与当前状态 |

### 验证结果
- chinese-code-review：`codex exec "用中文规范 review 这段代码：int a = 0;"` -> 输出含"建议修改/仅供参考"分级标注，触发成功
- `codex exec "列出你的 skills"` -> 列出全部 skills（含软链共享的），软链接识别正常

---

## 四、相关文件索引

| 文件 | 位置 | 作用 |
|------|------|------|
| Codex 行为准则 | `~/.codex/AGENTS.md` | Codex 专用配置（独立维护，非软链） |
| Claude Code 行为准则 | `~/.claude/CLAUDE.md` | Claude Code 配置 |
| Skills 源目录 | `~/.claude/skills/` | superpowers-zh 安装位置 |
| Skills Codex 目录 | `~/.codex/skills/*` | 软链指向 `~/.claude/skills/*` |
| Codex 兼容补丁脚本 | `~/.claude/skills-codex-patch.py` | 重装后恢复 6 个 description 改动 |
| 本速查表（Codex 侧快捷访问） | `~/.codex/skills-trigger-guide.md` | 软链指向本文档 |
| memory | `~/.claude/projects/-home-changyuchun--claude/memory/codex-skills-trigger-mechanism.md` | 跨会话记忆 |

---

## 重装维护指引

**重装或升级 superpowers-zh 后，必须执行以下命令恢复 Codex 兼容改动：**

```bash
python3 ~/.claude/skills-codex-patch.py
```

| 项 | 说明 |
|----|------|
| 脚本位置 | `~/.claude/skills-codex-patch.py` |
| 作用 | 恢复 6 个 skill 的 Codex 兼容 description 改动：chinese-code-review、chinese-commit-conventions、chinese-documentation、chinese-git-workflow、english-commit-conventions、test-driven-development |
| 特性 | idempotent，可安全重复执行，已应用的改动自动跳过 |
| 重装影响 | superpowers-zh 安装会覆盖 SKILL.md 为官方原版（含 /xxx 死锁措辞或自动触发措辞），本脚本一键恢复 Codex 兼容版 |

> 补丁脚本只恢复 description 改动。若重装后 5 个被删 skill（brainstorming/writing-plans/executing-plans/systematic-debugging/verification-before-completion）又缺失，需重新从 superpowers-zh 包提取，见"三、变更记录"中的恢复方法。

## 五、遗留项

1. **CLAUDE.md "功能开发分流规则"整节**：仍是 /icode 子命令体系内容（仅第 204 行标注暂停）。若 icode 长期不用，整节可进一步清理。Claude Code 侧适用，Codex 侧已由 AGENTS.md 解决。
2. **CLAUDE.md "Commit 规范分流规则"**：仍含 `/chinese-commit-conventions` 调用映射，Claude Code 侧有效，Codex 侧已由 AGENTS.md 改写为自然语言触发。
3. **icode-skill 适配**：/icode 子命令体系在 Codex 无效，后续若要在 Codex 使用，需改 icode-skill 的触发方式（同本次 chinese-* 方法）。

---

## 变更历史

| 日期 | 版本 | 变更 |
|------|------|------|
| 2026-07-13 | v1.0 | 初始版本：完成 Codex skills 触发适配，整理速查表与变更记录 |
| 2026-07-13 | v1.1 | 新增 TDD 测试约束；test-driven-development skill 改为仅用户明确要求时触发 |
| 2026-07-13 | v1.2 | 补充"重装维护指引"小节，明确重装后跑补丁脚本恢复 6 个 Codex 兼容改动 |
| 2026-07-13 | v1.3 | 修正 CLAUDE.md 核心规则第 3 条与 TDD 测试约束的冲突，改为测试按需补充 |
