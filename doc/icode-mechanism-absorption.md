# icode-skill 质量机制吸收记录

> **首次记录**：2026-07-18
> **最近复核**：2026-08-14
> **来源**：`~/.claude/skills/icode-skill`（独立 Git 仓库；`SKILL.md` 版本 `v2.17.0`，commit `00fb6fe`）
> **生效体**：`~/.claude/skills/` 下 superpowers 集合（using-superpowers 为路由入口）
> **状态**：已完成 5 轮选择性吸收；第 6 轮已完成源端复核，2 项候选待确认后才注入。icode 本体保持独立，Claude Code 可用，Codex 侧因 `/icode` 不受支持而暂停

## 一、背景与对比结论

icode-skill 是端到端**编排框架**（步骤 0 + 1～6 主流程，另有 log、doc、limit、README、patch 等独立流程，并配套状态机与 ticket 目录），靠 `/icode` 子命令驱动；superpowers 集合是**原子能力库**（每个 skill 处理一个节点，靠 description 语义触发）。

两者哲学相反（强编排 vs 自由组合、有状态 vs 无状态、命令触发 vs 语义触发），**不宜整体合并**。icode 当前未启用（`/icode` 在 Codex CLI 无效，AGENTS.md 已标"暂停"），仅作参考源。

本记录持续做**质量机制吸收**：把 icode 中可复用的机制提炼、泛化后注入 superpowers 对应 skill，以补强执行约束、对抗验证、证据回指、需求收敛和增量验证。icode 专属的步骤、状态、ticket 与补丁编排概念不吸收。

## 二、吸收映射表（核心）

| # | icode 源文件 | 提炼机制 | 注入目标 skill | 当前段标题 |
|---|-------------|---------|---------------|-----------|
| 1 | `references/anti_laziness.md` | 反偷懒约束 | `using-superpowers/SKILL.md` | `## 执行反偷懒约束` |
| 2 | `references/thinking.md` | 可审计的重要决策记录；不要求暴露内部推理，不强制 MCP | `using-superpowers/SKILL.md` | `## 重要决策记录` |
| 3 | `references/adversarial.md` | 对抗验证与诚实降级 | `requesting-code-review/SKILL.md` | `## 对抗验证增强（可选）` |
| 4 | `references/adversarial.md` | 对反馈做对抗验证 | `receiving-code-review/SKILL.md` | `## 对反馈做对抗验证` |
| 5 | `references/adversarial.md` | 证据回指纪律 | `verification-before-completion/SKILL.md` | `## 证据回指纪律` |
| 6 | `references/thinking.md` | 调试假设对抗三问 | `systematic-debugging/SKILL.md` | `假设对抗三问` |
| 14 | `references/necessity_check.md` | 实现前核实现有功能覆盖度与复用边界 | `brainstorming/SKILL.md` | `### 现有功能覆盖度检查` |
| 15 | `steps/05_deepcheck.md`、`steps/06_audit.md` | 多 Git 根分别取证，避免父仓状态掩盖嵌套仓改动 | `requesting-code-review/SKILL.md`、`verification-before-completion/SKILL.md` | `## 审查范围与多 Git 根`、`## 多 Git 根验证边界` |
| 16 | `steps/06_audit.md` | 增量修改使旧证据失效，必须重读当前 diff 并重跑受影响验证 | `verification-before-completion/SKILL.md` | `## 证据新鲜度与增量修改` |

> 表中 1～6 为首轮与二轮机制，14～16 为 2026-08-07 新增机制。历史各轮改动统计见后文，不再把早期统计误作当前整体统计。

## 三、注入原则

1. **新增段不改原有**：每个注入段作为独立 `## 段` 插入，原有段落顺序与内容保持不变。
2. **frontmatter 不动**：注入只动 body，`name`/`description` 字段不变，保证 Codex 语义自动触发不受影响。
3. **提炼泛化**：去除 icode 专属概念（步骤号、ticket_id、`.icode_output_N` 目录、Agent 工具 spawn 规格等），保留可通用化的核心规则。每段末尾用 `>` 引用块标注提炼来源，便于回溯原文件。
4. **可选 vs 硬约束区分**：对抗验证标"（可选）"（superpowers 是通用场景，不强求 spawn 3 子代理）；诚实降级、证据回指、反偷懒总则标为硬约束。

## 四、后续同步规则

### icode-skill 更新时

当 `~/.claude/skills/icode-skill/` 更新时，先记录新旧 commit，再按映射表逐项核对：

1. `anti_laziness.md` 改动 → 检查 `using-superpowers` 的「执行反偷懒约束」段是否需同步
2. `thinking.md` 改动 → 检查 `using-superpowers` 的「重要决策记录」段是否需同步；不得恢复强制 MCP 或要求输出内部推理的规则
3. `adversarial.md` 改动 → 同时检查 3 个目标 skill 的注入段（requesting / receiving / verification）
4. `thinking.md` 的「对抗质疑三问」段改动 -> 检查 `systematic-debugging` 第三阶段「假设对抗三问」段是否需同步。注意：源段针对历史工单，注入段是改造后针对调试假设的，同步时只比对「反确认偏误精神」的提炼点是否变化，不照搬 verdict/工单概念。

**核对方式**：`diff` icode 源文件与注入段的提炼点，判断新增/修改的规则是否值得泛化注入。icode 专属概念（步骤号/ticket/Agent spawn 规格）继续不吸收。

### superpowers 维护时

- 修改目标 skill 的 body 时，注意本地策略段是后加的，不要误删
- 若调整 `## 红线` / `## 底线` / `## 平台适配` 等历史锚点，需同步检查本地策略段位置，并重新生成、审查 overlay
- 上游 superpowers 同步后，运行 `scripts/skills-codex-patch.py`，再用 overlay 的 `--check` 确认本地策略未被覆盖

### 重新应用本地策略

本地策略以仓库内 overlay 保存，不再依赖 `/tmp` 一次性脚本：

```bash
cd ~/.claude/skills
scripts/apply-local-skill-overlays --check
scripts/apply-local-skill-overlays --dry-run
scripts/apply-local-skill-overlays --apply
```

`--check` 用于确认策略是否已应用；`--dry-run` 仅判断当前上游是否可安全应用；`--apply` 才会修改文件。脚本先执行反向检查识别“已应用”状态；若上游内容漂移导致补丁无法干净应用，会安全失败并要求人工复核，不强制覆盖。

## 五、未吸收部分（记录原因）

| icode 能力 | 未吸收原因 |
|-----------|-----------|
| 固定主流程与独立 patch/state 编排 | 与 superpowers 自由组合哲学冲突 |
| 工单状态机 + ticket_id + metadata.json + 断点续跑 | 与 superpowers 无状态原子特性冲突 |
| `/icode` 子命令触发 | Codex CLI 下无效（AGENTS.md 已标"暂停"） |
| 工程级知识库（`/icode doc` + project_docs + 段零检索） | 依赖 icode 状态目录，独立性强，不宜拆解注入 |
| 历史检索注入 + verdict 分流标注 | 依赖 icode 全局索引，superpowers 无对应载体 |
| Agent 工具 spawn 规格（subagent_type/schema 强制 StructuredOutput） | icode 专属实现细节，superpowers 各平台工具不同 |
| ADR 决策记录 + 实现偏差回写 | 依赖 icode 产物目录结构 |
| `references/thinking.md` 强制 Read references（每步重读 + 确认行） | 调试场景 references 不固定（日志/代码每次不同），强制重读代价高且无法定义「该读哪个文件」；systematic-debugging 第一阶段「完整阅读堆栈跟踪」「逐行阅读参考实现」已含等价精神 |

以上能力若未来需要在 superpowers 体系内复现，应作为独立新 skill 设计，而非注入现有 skill。

## 六、回退方法

先用 `git status --short` 和 `git diff -- <目标文件>` 确认目标与影响范围。未获得明确授权时，不执行覆盖式回退。

- 已提交批次：优先使用 `git revert <commit>` 生成可审计的反向提交。
- 未提交批次：用户确认具体文件和片段后，使用 `git restore --patch <文件>` 选择性回退。
- overlay 整体回退：用户确认后可执行 `git apply --reverse overlays/codex-local-policy.patch`；执行前必须先用 `git apply --reverse --check` 验证。

不要使用会覆盖整文件未提交改动的 `git checkout -- <文件>`。

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

## 八、三次吸收：需求收敛多视角 + 多层审查增强（2026-08-01，直接提炼式）

> 本次吸收 2 项 P0 机制，分别注入 `verification-before-completion` 和 `requesting-code-review`，补强"完成前验证只看计划不看需求"和"单层审查遗漏深层问题"两个短板。

### 8.1 吸收对象

| # | icode 源文件 | 提炼机制 | 注入目标 skill | 注入锚点 | 注入段标题 |
|---|-------------|---------|---------------|---------|-----------|
| 7 | `steps/06_audit.md` §6.7 | 需求收敛多视角（需求、计划、必要性逐条对照） | `verification-before-completion/SKILL.md` | `## 证据回指纪律` 后、`## 底线` 前 | `## 需求收敛三视角` |
| 8 | `steps/05_deepcheck.md` | 三阶段递进复检（Reverse 逆推 -> Fixed 固定维度 -> Free 自由探索） | `requesting-code-review/SKILL.md` | `## 对抗验证增强（可选）` 后、`## 红线` 前 | `## 多层审查增强（可选）` |

### 8.2 提炼要点

**吸收 7·需求收敛多视角**：
- **源规则**：icode 终审步骤 §6.7 双视角对照（视角 A 需求角度 vs 视角 B 计划角度），依赖 `metadata.requirement` / `limit_refs` 字段
- **泛化处理**：最初去除 metadata/limit_refs 依赖，改为“重读用户原始需求 -> 逐条拆解 -> 双视角对照表”；2026-08-07 再增加“实现必要性/现有行为”视角
- **注入逻辑**：补强 verification-before-completion 的"需求已满足"检查--原来只说"逐项核对清单"但不区分计划角度和需求角度，实测会出现"计划功能点全实现但用户需求某个边角遗漏"
- **与门控函数的关系**：多视角是门控函数在需求维度的细化——把笼统的“需求已满足”拆成逐条可验证的对照表

**吸收 8·多层审查增强**：
- **源规则**：icode 步骤 5 三阶段递进复检（Reverse 只给代码逆推需求 -> Fixed 7 维度逐项覆盖 -> Free 15 角度自由探索），依赖 `03_plan_final.md` / metadata
- **泛化处理**：去除 icode 产物文件依赖，保留三阶段递进结构与核心维度；Fixed 维度从 icode 原 6 个调整为 7 个（合并"现有实现对照"与"跨文件一致性"为独立维度）；Free 15 角度精简为 12 个关键角度
- **按变更规模分档**：小变更仅第 1 层、中等变更 1+2 层、重要变更三层全跑（icode 原文是固定三层全跑）
- **与对抗验证的关系**：多层审查是审查深度的分层递进，对抗验证是审查结论的独立验证，两者可叠加使用

### 8.3 改动统计

2 文件，+76 行，0 删除：
- `verification-before-completion/SKILL.md`：+30 行（当时为需求收敛双视角段，现已演进为三视角）
- `requesting-code-review/SKILL.md`：+46 行（多层审查增强段）
- `doc/icode-mechanism-absorption.md`：+本节

frontmatter（name/description）全部未动，原有内容一字未改，skill 触发机制不受影响。~/.codex/skills 软链自动同步。

### 8.4 同步规则追加

当 `icode-skill/steps/` 下 2 个源文件有更新时，按以下规则核对：

5. `steps/06_audit.md` §6.7 改动 -> 检查 `verification-before-completion` 的「需求收敛三视角」段是否需同步。注意：源规则依赖 metadata.requirement / limit_refs，注入段已泛化去除，同步时只比对“需求、计划、必要性三视角对照”的核心规则是否变化。
6. `steps/05_deepcheck.md` 三阶段段改动 -> 检查 `requesting-code-review` 的「多层审查增强」段是否需同步。注意：源规则的三阶段含 fast 模式降级、schema 迁移等 icode 专属逻辑，同步时只比对「三阶段递进结构 + Fixed 维度清单 + Free 角度清单」是否变化。

### 8.5 回退说明

按“六、回退方法”执行。对应段标题为 `## 需求收敛三视角` / `## 多层审查增强（可选）`，只回退已确认的片段。

## 九、四次吸收：Codex 兼容性补强 + 修复分档 + 前提假设 + 工具调用模式（2026-08-03，直接提炼式 + 改造式）

> 本次吸收 5 项机制，核心驱动是 **Codex CLI 兼容性**：前三次吸收未考虑“当前会话未暴露 spawn 能力”的场景，对抗验证段会直接失效。本次补齐按会话实际能力判定的降级路径，同时吸收 icode-skill 7-8 月新增的 3 项质量机制。

### 9.1 吸收对象

| # | icode 源文件 | 提炼机制 | 注入目标 skill | 注入位置 | 操作类型 |
|---|-------------|---------|---------------|---------|---------|
| 9 | `references/adversarial.md`（v2.3/v2.4「环境无 spawn 工具场景」段） | 环境无 spawn 工具降级路径 | `requesting-code-review/SKILL.md` | 「对抗验证增强」段内，「子代理失败处理」后 | 新增子段 |
| 10 | `SKILL.md`（`746d61b` commit「工具调用模式规范」段） | 工具调用模式规范（批量并行 + 连续执行） | `using-superpowers/SKILL.md` | 「执行反偷懒约束」后、「深度思考载体分档」前 | 新增段 |
| 11 | `references/adversarial.md`（v2.4「显式等待+超时」+ v2.6「重试 2 次」） | 对抗验证增强：显式等待+超时四态+重试 2 次（按当前接口支持调整执行配置） | `requesting-code-review/SKILL.md` | 替换原「子代理失败处理」单行 | 增强替换 |
| 12 | `references/anti_laziness.md` 第 26 条（v2.7） | 修复方案三档分级（A/B/C） | `systematic-debugging/SKILL.md` | 第四阶段第 2 步「实施单一修复」后 | 新增子段 |
| 13 | `references/anti_laziness.md` 第 27 条 + `steps/00_init.md` §5（v2.10） | 前提假设验证（外部前提实验表） | `brainstorming/SKILL.md` | 「流程详述·理解想法」后、「探索方案」前 | 新增子段 |

### 9.2 提炼要点

**吸收 9·环境无 spawn 工具降级路径**：
- **源规则**：icode `adversarial.md` v2.3/v2.4「环境无 spawn 工具场景」--环境结构性无 spawn 能力时不重试、诚实降级标 `[未验证-环境无spawn工具]`、主代理代行须三视角各自独立
- **Codex 驱动**：不同 Codex 会话暴露的工具能力可能不同；若当前会话未暴露或无法调用 `spawn_agent`，前三次吸收的对抗验证段会失效且无降级路径
- **泛化处理**：去除 `no_spawn_env` flag / `log_analysis.md §6` 产物标记要求；Codex 以当前会话是否实际暴露且可调用 `spawn_agent` 判定，配置文件仅作排障线索
- **与原注入段的关系**：补强第三轮吸收的「对抗验证增强（可选）」段--原段只说"重试 1 次"，无环境不可用的降级路径

**吸收 10·工具调用模式规范**：
- **源规则**：icode `SKILL.md` commit `746d61b` 新增段--两条硬性规则：①无依赖工具调用必须批量并行；②拿到结果后立即继续不等用户推进
- **泛化处理**：去除"Agent 工具"措辞改为平台中性"子代理工具"；去除"MCP 调用覆盖强制化"关联（icode 专属）
- **Codex 价值**：Codex CLI 下同样存在"每次只发一个工具调用就停"的问题，此规则平台无关

**吸收 11·对抗验证增强（显式等待+超时+重试 2 次）**：
- **源规则**：icode `adversarial.md` v2.4「显式等待+超时机制」+ v2.6「子代理失败处理」第 2 步升级
- **改造点**：原注入版"重试 1 次"升级为"重试 2 次（第 2 次仅在当前接口支持时调整执行配置）"；新增四态枚举（`sync_ok`/`timeout_retry_used`/`still_failed_after_retry`/`env_no_spawn`）；新增显式等待契约（120s 超时 + 超时触发重试 1 次）
- **泛化处理**：去除 `task_timeout_seconds` metadata 字段依赖，保留 120s 默认值 + 四态枚举

**吸收 12·修复方案三档分级**：
- **源规则**：icode `anti_laziness.md` 第 26 条（v2.7）--Bug 修复方案分 A（根因修复 Must-fix）/ B（兜底防御 Defensive）/ C（后续工单 Out-of-scope）三档
- **泛化处理**：去除 `fix_tiers` metadata / `confirmed_B_fixes` 字段依赖，保留三档判定逻辑 + "最小修复=只做 A 档"原则
- **与 systematic-debugging 的关系**：补强第四阶段"实施修复"--原段只说"实施单一修复"，缺乏修复范围分级机制

**吸收 13·前提假设验证**：
- **源规则**：icode `anti_laziness.md` 第 27 条（v2.10）+ `steps/00_init.md` §5「前提假设实验表」--需求依赖无法代码验证的外部事实时必须设计最小实验
- **泛化处理**：去除 `00_init.md §5` / `plan §9` 字段依赖，保留"识别外部前提 -> 代码能验证则标注验证方法、不能则设计实验 -> 证伪回写"核心规则
- **与 brainstorming 的关系**：补强「理解想法」阶段--原段不强制验证需求前提，实测痛点是"需求前提与事实不符但到实现/测试阶段才暴露"

### 9.3 初始注入范围

初始注入涉及 4 个 skill 文件；相对当时基线为 +95 行、-3 行（-3 行为 ①+③ 增强替换的旧"重试 1 次"单行 + 旧引用行）：
- `using-superpowers/SKILL.md`：+23 行（工具调用模式规范段）
- `requesting-code-review/SKILL.md`：+32 行 / -3 行（显式等待+超时+重试2次+环境无spawn降级，替换旧单行）
- `systematic-debugging/SKILL.md`：+17 行（修复方案三档分级子段）
- `brainstorming/SKILL.md`：+26 行（前提假设验证子段）
- `doc/icode-mechanism-absorption.md`：+本节

frontmatter（name/description）全部未动，skill 触发机制不受影响。Codex CLI `~/.codex/skills/` 软链自动同步（指向同一份源文件）。

### 9.3.1 评审复核后的规则对齐（2026-08-03）

- `requesting-code-review`：Codex 是否具备子代理能力以当前会话实际暴露且可调用 `spawn_agent` 为准；配置文件仅作排障线索。第二次重试只在当前接口支持时调整执行配置。
- `using-superpowers`：批量并行仅适用于无依赖、无副作用或不共享写入目标、且工具允许并行的调用；受资源、速率或工具串行要求约束的调用必须串行。
- `systematic-debugging`：未明确要求“写单测”“补充测试用例”或“完善测试覆盖”时，不自动新增或修改 `test/` 下测试代码；验证优先复用已有测试、构建、静态检查或用户提供的复现路径。

2026-08-07 再次复核后补充：

- 等待超时只表示“尚未返回”，不能据此判定子代理失败，也不能自动重复派生同一任务；先查询实际状态，再决定继续等待或在明确失败后替换。
- Codex 的自包含审查任务优先使用 `fork_turns="none"` 和完整任务简报，降低无关上下文污染。
- 仅在当前接口真实提供清理/关闭能力时调用；不得把不存在的 `close_agent` 当成必需步骤。
- 只记录事实、假设、取舍和验证边界，不要求输出内部推理过程，也不强制使用 sequential-thinking MCP。

### 9.4 Codex 兼容性设计

本次吸收的核心创新是**所有涉及 spawn 的段均含"环境无 spawn 工具"降级路径**，确保当前 Codex 会话未暴露该工具时不会失效：

| 注入段 | 是否依赖 spawn | Codex 降级路径 |
|--------|-------------|--------------|
| 工具调用模式规范（②） | ❌ 不依赖 | 无需降级，平台中性 |
| 显式等待+超时+重试2次（③） | ✅ 依赖 | 四态中 `env_no_spawn` 状态 |
| 环境无 spawn 降级路径（①） | ✅ 依赖 | 本段即降级路径本身 |
| 修复方案三档分级（④） | ❌ 不依赖 | 无需降级，纯逻辑规则 |
| 前提假设验证（⑤） | ❌ 不依赖 | 无需降级，纯思考规则 |

**平台中性措辞约束**：所有注入段不使用 `Task 工具`/`Agent 工具` 等 Claude Code 专属名称，改用"子代理工具"或"spawn"通用表述。具体工具名、执行参数和等待方式均以当前运行环境实际接口为准。

### 9.5 同步规则追加

当 icode-skill 源文件有更新时，按以下规则核对：

7. `references/adversarial.md`「环境无 spawn 工具场景」段改动 -> 检查 `requesting-code-review` 的「环境无 spawn 工具的降级路径」段是否需同步。注意：源规则依赖 `no_spawn_env` flag / 产物文件标记，注入段已泛化去除，同步时只比对"结构性不可用 vs 临时失败区分 + 主代理代行条件"核心规则是否变化。
8. `SKILL.md`「工具调用模式规范」段改动 -> 检查 `using-superpowers` 的「工具调用模式规范」段是否需同步。注意：源规则含"MCP 调用覆盖强制化"关联，注入段已去除，同步时只比对"批量并行 + 连续执行"两条核心规则是否变化。
9. `references/adversarial.md`「显式等待+超时」/「重试 2 次」段改动 -> 检查 `requesting-code-review` 的对应段是否需同步。注意：源规则含 `task_timeout_seconds` 字段依赖，注入段已泛化为 120s 默认值，同步时只比对"四态枚举 + 重试 2 次（按当前接口支持调整执行配置）+ 等待契约"是否变化。
10. `references/anti_laziness.md` 第 26 条改动 -> 检查 `systematic-debugging` 的「修复方案三档分级」段是否需同步。注意：源规则含 `fix_tiers`/`confirmed_B_fixes` metadata 依赖，注入段已泛化去除，同步时只比对"A/B/C 三档判定逻辑 + 最小修复原则"是否变化。
11. `references/anti_laziness.md` 第 27 条 + `steps/00_init.md` §5 改动 -> 检查 `brainstorming` 的「前提假设验证」段是否需同步。注意：源规则含 `00_init.md §5`/`plan §9` 字段依赖，注入段已泛化去除，同步时只比对"识别外部前提 -> 验证分流 -> 实验设计要求 -> 证伪回写"核心规则是否变化。

### 9.6 回退说明

按“六、回退方法”执行，只选择性回退已确认的段落：

注入段标题/锚点为：
- `using-superpowers`：`## 工具调用模式规范`
- `requesting-code-review`：`**显式等待 + 超时` / `**子代理失败处理（重试 2 次` / `**环境无 spawn 工具的降级路径` / `**Codex CLI 判定方法`
- `systematic-debugging`：`**修复方案三档分级`
- `brainstorming`：`**前提假设验证`

可用 `rg` 定位。注意 `requesting-code-review` 的「环境无 spawn 工具的降级路径」与等待、失败处理配套；回退前须整体评估，不能只删其中一段。

## 十、五次吸收：现有覆盖、多 Git 根与增量证据（2026-08-07）

### 10.1 更新复核结论

- 复核源：`~/.claude/skills/icode-skill`；`SKILL.md` 声明版本为 `v2.14.0`，HEAD 与 `origin/main` 均为 `ccfe991`。该仓库未用同名 Git tag 标记当前提交。
- 保持边界：不合并 icode 的固定状态机、ticket 目录、patch 编排、Serena 依赖、显式思考 MCP 和低成本模型分流。
- 选择吸收：实现前核实现有功能覆盖度、多 Git 根分别取证、增量修改后的证据失效与重验。

### 10.2 本轮注入

| 机制 | 目标 | 收敛效果 |
|------|------|---------|
| 现有功能覆盖度检查 | `brainstorming` | 先在当前仓库及相关嵌套 Git 根查复用实现，并区分“已覆盖/部分覆盖/未覆盖” |
| 多 Git 根审查与验证 | `requesting-code-review`、`verification-before-completion` | 每个变更文件按所属 Git 根分别计算状态、diff 与验证边界 |
| 证据新鲜度 | `verification-before-completion` | 后续修改使受影响的旧证据失效，必须重读当前内容并重跑相关验证 |
| 需求收敛三视角 | `verification-before-completion` | 在需求和计划之外，增加“是否确有必要、现有行为是否已覆盖” |

### 10.3 superpowers-zh 整体规则修正

本轮同时修正了与本地授权边界不一致的通用规则：

- `brainstorming`、`writing-plans`、`executing-plans`：不再默认创建文档提交或频繁 commit；提交仅在用户明确授权时执行。
- `writing-plans`、`subagent-driven-development`、`verification-before-completion`：TDD 和新增/修改测试文件仅在用户明确要求测试时启用，其他情况复用已有验证路径。
- `requesting-code-review`：不再假设 `HEAD~1` 或固定 `main`；审查包含已提交、暂存和未暂存改动，并处理嵌套 Git 根。
- `subagent-driven-development`：审查包覆盖 committed、staged、unstaged 和 untracked 内容，未授权 commit 时也不会因 HEAD 未变化而漏审实现。
- `using-git-worktrees`：修改忽略规则、commit 或退回原工作区都必须遵循用户授权，不再自动执行。
- `using-superpowers`：把“深度思考载体”改为“重要决策记录”，保留可审计结论，不输出内部推理。
- 各 reviewer prompt：改为平台中性表述，避免把 Claude Code 的 `Task` 工具当成所有运行环境的固定接口。

### 10.4 可恢复 overlay

- 策略补丁：`overlays/codex-local-policy.patch`
- 应用脚本：`scripts/apply-local-skill-overlays`
- 重装入口：`~/.claude/skills/scripts/skills-codex-patch.py` 会先恢复历史 Codex 兼容措辞，再调用 overlay 脚本。

overlay 只包含已审查的本地 skill、prompt 和配套 helper script 策略改动，不包含本文档、恢复入口脚本、测试文件或 `icode-skill` 嵌套仓内容。上游漂移时脚本会失败并要求人工审查，不会强制覆盖。

## 十一、第六轮复核：对抗输出卫生与跨轮隔离（2026-08-14，待确认注入）

### 11.1 为什么此前没有更新“吸收点”

第十节复核的基线是 `ccfe991`（`v2.14.0`）。当前 `icode-skill` 已推进到 `00fb6fe`（`v2.17.0`），8 月 12～13 日在 `references/adversarial.md` 新增了跨轮隔离、去引导措辞、输出预算与 verdict 优先等规则；此前没有完成这段增量的逐项复核，所以不能把尚未注入目标 skill 的内容提前记为“已吸收”。

本轮已对 `ccfe991..00fb6fe` 做源端差异复核。下面两项与 `requesting-code-review` 的可选对抗验证直接相关，但尚未修改该 skill：用户确认后再作为独立第六轮注入。

### 11.2 待确认的候选吸收项

| 候选 | icode 源 | 拟注入目标 | 泛化后的约束 | 当前状态 |
|------|----------|------------|--------------|----------|
| 17·跨轮隔离与去引导 | `references/adversarial.md`（`6f0d7e3`） | `requesting-code-review/SKILL.md` 的「对抗验证增强（可选）」 | 每轮使用全新、互不共享历史裁决过程的质疑者；prompt 仅提供待核查结论、文件路径和证据指针，不夹带“已确认”“无需质疑”等价值预判。 | 待确认 |
| 18·verdict 优先与输出卫生 | `references/adversarial.md`（`00fb6fe`） | `requesting-code-review/SKILL.md` 的「对抗验证增强（可选）」 | 先给简短裁决和证据定位，再给必要理由；禁止转储读取到的代码或日志原文；输出预算用于防截断，不得为省 token 压缩到丢失竞争假设或证据。 | 待确认 |

两项均去除了 `StructuredOutput`、`max_output_tokens` 数值、Agent 类型和 icode 产物字段等平台专属实现细节，只保留独立判断与防输出失控的质量目标。

### 11.3 明确不吸收：后台 spawn watchdog

`bee1f66` 的后台 watchdog 依赖 `run_in_background`、`TaskOutput` 与 `TaskStop`。当前 Codex 会话以实际暴露的 agent 生命周期接口为准，不能假定这些参数或停止接口存在；而且对正在运行的 agent 重复等待/轮询也与本地“不要反复轮询阻塞 agent”约束冲突。因此本轮不将“10 分钟无返回后停掉并改前台重跑”写入通用 skill。

现有 `requesting-code-review` 继续采用更保守的规则：等待超时后先查询实际状态；仅在原 agent 明确失败、终止或最终输出不可用时，才启动一个替代任务。

### 11.4 后续同步规则追加

12. `references/adversarial.md` 的 Freshness / Anti-coaching 段改动 → 若候选 17 获确认并注入，检查 `requesting-code-review` 的对抗 prompt 是否仍避免历史裁决污染和预设结论措辞。
13. `references/adversarial.md` 的输出预算 / verdict 优先段改动 → 若候选 18 获确认并注入，检查 `requesting-code-review` 是否仍保留“裁决优先、禁止原文转储、预算不牺牲必要证据”的平台中性约束。
