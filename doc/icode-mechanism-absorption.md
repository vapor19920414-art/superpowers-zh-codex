# icode-skill 质量机制吸收记录

> **日期**：2026-07-18
> **来源**：`~/.claude/skills-orbbec/icode-skill`（参考源，当前未启用）
> **生效体**：`~/.claude/skills/` 下 superpowers 集合（using-superpowers 为路由入口）
> **状态**：已执行路径 1（机制吸收），icode 本体保持独立不动

## 一、背景与对比结论

icode-skill 是端到端**编排框架**（7 步串联 + 状态机 + ticket 目录），靠 `/icode` 子命令驱动；superpowers 集合是**原子能力库**（每个 skill 处理一个节点，靠 description 语义触发）。

两者哲学相反（强编排 vs 自由组合、有状态 vs 无状态、命令触发 vs 语义触发），**不宜整体合并**。icode 当前未启用（`/icode` 在 Codex CLI 无效，AGENTS.md 已标"暂停"），仅作参考源。

本次只做**质量机制吸收**：把 icode 4 套可复用的质量机制，提炼泛化后注入 superpowers 对应 skill，以补强 superpowers 在"执行过程约束、对抗验证、证据回指"方面的短板。icode 专属的步骤/状态/ticket 概念不吸收。

## 二、吸收映射表（核心）

| # | icode 源文件 | 提炼机制 | 注入目标 skill | 注入锚点 | 注入段标题 | 行号 |
|---|-------------|---------|---------------|---------|-----------|------|
| 1 | `references/anti_laziness.md` | 反偷懒约束（16 条偷懒行为） | `using-superpowers/SKILL.md` | `## 平台适配` 前 | `## 执行反偷懒约束` | 58 |
| 2 | `references/thinking.md` | 深度思考载体分档（MCP/降级文字块） | `using-superpowers/SKILL.md` | `## 执行反偷懒约束` 后 | `## 深度思考载体分档` | 76 |
| 3 | `references/adversarial.md` | 对抗验证（3 质疑者 + 裁决优先级 + 诚实降级 + 子代理失败处理） | `requesting-code-review/SKILL.md` | `## 红线` 前 | `## 对抗验证增强（可选）` | 96 |
| 4 | `references/adversarial.md` | 对反馈做对抗验证（替代解释 + 证据充分性 + 主代理实证优先） | `receiving-code-review/SKILL.md` | `## 底线` 前 | `## 对反馈做对抗验证` | 213 |
| 5 | `references/adversarial.md` | 证据回指纪律（每条结论回指具体证据片段） | `verification-before-completion/SKILL.md` | `## 底线` 前 | `## 证据回指纪律` | 139 |

**改动统计**：4 文件，+89 行，0 删除。原有内容一字未改，frontmatter（name/description）全部未动，skill 触发机制不受影响。

## 三、注入原则

1. **新增段不改原有**：每个注入段作为独立 `## 段` 插入，原有段落顺序与内容保持不变。
2. **frontmatter 不动**：注入只动 body，`name`/`description` 字段不变，保证 Codex 语义自动触发不受影响。
3. **提炼泛化**：去除 icode 专属概念（步骤号、ticket_id、`.icode_output_N` 目录、Agent 工具 spawn 规格等），保留可通用化的核心规则。每段末尾用 `>` 引用块标注提炼来源，便于回溯原文件。
4. **可选 vs 硬约束区分**：对抗验证标"（可选）"（superpowers 是通用场景，不强求 spawn 3 子代理）；诚实降级、证据回指、反偷懒总则标为硬约束。

## 四、后续同步规则

### icode-skill 更新时

当 `~/.claude/skills-orbbec/icode-skill/references/` 下 4 个源文件有更新，按映射表逐项核对：

1. `anti_laziness.md` 改动 → 检查 `using-superpowers` 的「执行反偷懒约束」段是否需同步
2. `thinking.md` 改动 → 检查 `using-superpowers` 的「深度思考载体分档」段是否需同步
3. `adversarial.md` 改动 → 同时检查 3 个目标 skill 的注入段（requesting / receiving / verification）

**核对方式**：`diff` icode 源文件与注入段的提炼点，判断新增/修改的规则是否值得泛化注入。icode 专属概念（步骤号/ticket/Agent spawn 规格）继续不吸收。

### superpowers 维护时

- 修改 4 个目标 skill 的 body 时，注意注入段是后加的，不要误删
- 若调整 `## 红线` / `## 底线` / `## 平台适配` 锚点标题，注入段需同步移位（注入脚本依赖锚点字符串定位）
- 上游 superpowers 同步（`skills-codex-patch.py` 重跑）后，需重新执行注入或确认注入段未被覆盖

### 重新执行注入

注入脚本存于 `/tmp/inject_quality_mechanisms.py`（一次性）。若需重新注入或迁移，核心逻辑：基于锚点字符串（`## 平台适配` / `## 红线` / `## 底线`）在前面插入对应段。锚点唯一性校验已内置（出现次数 ≠ 1 则跳过该文件）。

## 五、未吸收部分（记录原因）

| icode 能力 | 未吸收原因 |
|-----------|-----------|
| 7 步强编排（plan→review→merge→code→deepcheck→audit 固定顺序） | 与 superpowers 自由组合哲学冲突 |
| 工单状态机 + ticket_id + metadata.json + 断点续跑 | 与 superpowers 无状态原子特性冲突 |
| `/icode` 子命令触发 | Codex CLI 下无效（AGENTS.md 已标"暂停"） |
| 工程级知识库（`/icode doc` + project_docs + 段零检索） | 依赖 icode 状态目录，独立性强，不宜拆解注入 |
| 历史检索注入 + verdict 分流标注 | 依赖 icode 全局索引，superpowers 无对应载体 |
| Agent 工具 spawn 规格（subagent_type/schema 强制 StructuredOutput） | icode 专属实现细节，superpowers 各平台工具不同 |
| ADR 决策记录 + 实现偏差回写 | 依赖 icode 产物目录结构 |

以上能力若未来需要在 superpowers 体系内复现，应作为独立新 skill 设计，而非注入现有 skill。

## 六、回滚方法

```bash
cd ~/.claude/skills
git diff                          # 查看全部注入改动
git checkout -- using-superpowers/SKILL.md \
                 requesting-code-review/SKILL.md \
                 receiving-code-review/SKILL.md \
                 verification-before-completion/SKILL.md   # 回滚注入
```

注入段均以 `## 执行反偷懒约束` / `## 深度思考载体分档` / `## 对抗验证增强（可选）` / `## 对反馈做对抗验证` / `## 证据回指纪律` 为标题，可 grep 定位单独删除。
