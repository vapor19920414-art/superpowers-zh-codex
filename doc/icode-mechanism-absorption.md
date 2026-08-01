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
| 6 | `references/thinking.md`（对抗质疑三问段） | 调试假设对抗三问（改造式：质疑历史工单 -> 质疑调试假设） | `systematic-debugging/SKILL.md` | 第三阶段第 1 步后、原第 2 步前 | `2. **假设对抗三问（强制必答，缺项视为流程不合规）**` | 159 |

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
4. `thinking.md` 的「对抗质疑三问」段改动 -> 检查 `systematic-debugging` 第三阶段「假设对抗三问」段是否需同步。注意：源段针对历史工单，注入段是改造后针对调试假设的，同步时只比对「反确认偏误精神」的提炼点是否变化，不照搬 verdict/工单概念。

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
| `references/thinking.md` 强制 Read references（每步重读 + 确认行） | 调试场景 references 不固定（日志/代码每次不同），强制重读代价高且无法定义「该读哪个文件」；systematic-debugging 第一阶段「完整阅读堆栈跟踪」「逐行阅读参考实现」已含等价精神 |

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

## 七、二次吸收：systematic-debugging 对抗三问（2026-07-19，改造式注入）

> 本次吸收采用**改造式**（区别于第二轮的直接提炼式）：源段针对「历史工单复用」场景，注入场景是「调试假设验证」，场景不同须改造而非照搬。

### 7.1 吸收对象

- **源**：`references/thinking.md` 的「历史参考小节 -> 对抗质疑三问」段（针对 verdict=unknown 的历史工单）
- **目标**：`systematic-debugging/SKILL.md` 第三阶段「假设与验证」
- **注入位置**：第 1 步「提出单一假设」后、原第 2 步「最小化测试」前（原 2/3/4 步顺延为 3/4/5）

### 7.2 改造映射（icode 三问 -> 调试三问）

| icode 原问（针对历史工单） | 调试改造问（针对当前假设） | 改造逻辑 |
|---------------------------|--------------------------|---------|
| ① 该工单核心方案前提是否仍成立？（Read/Grep 实证当前代码） | ① 该假设的前提证据是否实证成立？（Grep/Read 实证日志/代码原文） | 「实证前提」精神保留，对象从「历史 ADR」换成「当前假设依据」 |
| ② 该工单结论是否被后续推翻过？（查末轮摘要/audit） | ② 有没有反对该假设的证据被忽略？（主动找反证，默认怀疑） | 「找推翻信号」改为「主动找反证」，调试无工单可查故改为现场搜索 |
| ③ 该 ADR 是借鉴还是避坑？（默认怀疑） | ③ 已证实还是只是当前最像？（须列替代假设并排除） | 「默认怀疑」保留，强化为「须列替代假设排除才算证实」 |

### 7.3 改造式 vs 直接提炼式的区别

| 维度 | 直接提炼式（第二轮，4 个 skill） | 改造式（本次，systematic-debugging） |
|------|-------------------------------|--------------------------------------|
| 源场景与目标场景 | 一致（通用质量机制） | 不同（历史工单 vs 调试假设） |
| 注入方式 | 去除 icode 专属概念后保留原意 | 提取核心精神 + 改造问题表述 + 重建适用场景 |
| 同步策略 | 源文件改 -> 直接比对注入段 | 源文件改 -> 只比对「精神提炼点」，不照搬源段表述 |

### 7.4 强度与闭环

- **强制必答**：与 icode 一致，缺项视为流程不合规（systematic-debugging 第三阶段第 2 步标题明确标注）
- **规则闭环**：同步更新红线（新增「假设我已有把握，直接验证」信号）+ 速查表（第三阶段关键活动加「对抗三问」）+ 第 4 步补注「新假设仍须经三问」

### 7.5 本次改动统计

1 文件（`systematic-debugging/SKILL.md`），+23 行，0 删除。原有 4 个阶段、红线、常见借口、辅助技术等全部保留；frontmatter 未改；~/.codex/skills 软链自动同步。

### 7.6 未吸收的配套机制

- **强制 Read references**（thinking.md 通用流程第 2 步）：调试场景 references 不固定，强制重读代价高；systematic-debugging 第一阶段已含等价精神（见五、未吸收部分新增行）
- **sequential-thinking MCP 载体**：Codex 第三方模型下 MCP 不可用（AGENTS.md provider-aware 策略），本次直接采用文字块形式，不引入 MCP 依赖
- **verdict 分流标注 / 末轮扩读 / 历史检索注入**：仍依赖 icode 工单系统，不吸收（见五、未吸收部分）

## 八、三次吸收：需求收敛双视角 + 多层审查增强（2026-08-01，直接提炼式）

> 本次吸收 2 项 P0 机制，分别注入 `verification-before-completion` 和 `requesting-code-review`，补强"完成前验证只看计划不看需求"和"单层审查遗漏深层问题"两个短板。

### 8.1 吸收对象

| # | icode 源文件 | 提炼机制 | 注入目标 skill | 注入锚点 | 注入段标题 |
|---|-------------|---------|---------------|---------|-----------|
| 7 | `steps/06_audit.md` §6.7 | 需求收敛双视角（需求角度 vs 计划角度逐条对照） | `verification-before-completion/SKILL.md` | `## 证据回指纪律` 后、`## 底线` 前 | `## 需求收敛双视角` |
| 8 | `steps/05_deepcheck.md` | 三阶段递进复检（Reverse 逆推 -> Fixed 固定维度 -> Free 自由探索） | `requesting-code-review/SKILL.md` | `## 对抗验证增强（可选）` 后、`## 红线` 前 | `## 多层审查增强（可选）` |

### 8.2 提炼要点

**吸收 7·需求收敛双视角**：
- **源规则**：icode 终审步骤 §6.7 双视角对照（视角 A 需求角度 vs 视角 B 计划角度），依赖 `metadata.requirement` / `limit_refs` 字段
- **泛化处理**：去除 metadata/limit_refs 依赖，改为"重读用户原始需求 -> 逐条拆解 -> 双视角对照表"
- **注入逻辑**：补强 verification-before-completion 的"需求已满足"检查--原来只说"逐项核对清单"但不区分计划角度和需求角度，实测会出现"计划功能点全实现但用户需求某个边角遗漏"
- **与门控函数的关系**：双视角是门控函数在需求维度的细化--把笼统的"需求已满足"拆成逐条可验证的对照表

**吸收 8·多层审查增强**：
- **源规则**：icode 步骤 5 三阶段递进复检（Reverse 只给代码逆推需求 -> Fixed 7 维度逐项覆盖 -> Free 15 角度自由探索），依赖 `03_plan_final.md` / metadata
- **泛化处理**：去除 icode 产物文件依赖，保留三阶段递进结构与核心维度；Fixed 维度从 icode 原 6 个调整为 7 个（合并"现有实现对照"与"跨文件一致性"为独立维度）；Free 15 角度精简为 12 个关键角度
- **按变更规模分档**：小变更仅第 1 层、中等变更 1+2 层、重要变更三层全跑（icode 原文是固定三层全跑）
- **与对抗验证的关系**：多层审查是审查深度的分层递进，对抗验证是审查结论的独立验证，两者可叠加使用

### 8.3 改动统计

2 文件，+76 行，0 删除：
- `verification-before-completion/SKILL.md`：+30 行（需求收敛双视角段）
- `requesting-code-review/SKILL.md`：+46 行（多层审查增强段）
- `doc/icode-mechanism-absorption.md`：+本节

frontmatter（name/description）全部未动，原有内容一字未改，skill 触发机制不受影响。~/.codex/skills 软链自动同步。

### 8.4 同步规则追加

当 `icode-skill/steps/` 下 2 个源文件有更新时，按以下规则核对：

5. `steps/06_audit.md` §6.7 改动 -> 检查 `verification-before-completion` 的「需求收敛双视角」段是否需同步。注意：源规则依赖 metadata.requirement / limit_refs，注入段已泛化去除，同步时只比对「双视角对照核心规则」是否变化（如新增视角、调整收敛判定逻辑）。
6. `steps/05_deepcheck.md` 三阶段段改动 -> 检查 `requesting-code-review` 的「多层审查增强」段是否需同步。注意：源规则的三阶段含 fast 模式降级、schema 迁移等 icode 专属逻辑，同步时只比对「三阶段递进结构 + Fixed 维度清单 + Free 角度清单」是否变化。

### 8.5 回滚方法追加

```bash
# 回滚本次两项注入
git checkout -- verification-before-completion/SKILL.md \
                 requesting-code-review/SKILL.md
```

注入段标题为 `## 需求收敛双视角` / `## 多层审查增强（可选）`，可 grep 定位单独删除。
