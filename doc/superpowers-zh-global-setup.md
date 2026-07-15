# superpowers-zh 全局安装追溯文档

> 本文档记录将 `npx superpowers-zh` 从"项目级安装"转为"全局安装到 `~/.claude/skills/`"的完整操作过程，供后续追溯、升级、回滚参考。
>
> - **操作日期**：2026-07-11
> - **操作环境**：Ubuntu / Linux，Claude Code 全局 skills 目录 `~/.claude/skills/`
> - **安装器源码**：`~/.npm/_npx/b45846acb10a9395/node_modules/superpowers-zh/bin/superpowers-zh.js`

---

## 一、问题现象

在~/.claude/skills/ 目录下执行
执行 `npx superpowers-zh` 后，20 个 superpowers 技能（brainstorming / writing-plans / executing-plans / systematic-debugging / verification-before-completion / chinese-code-review / chinese-git-workflow 等）**未被 Claude Code 识别**，对应命令无法映射。

排查发现：

- `~/.claude/skills/` 顶层只有 `icode-skill/` 一个技能
- 20 个 superpowers 技能被装到了**嵌套路径** `~/.claude/skills/.claude/skills/<技能名>/`
- Claude Code 只扫描 `~/.claude/skills/<技能名>/SKILL.md` 一层，嵌套层不识别
- 另误生成 `~/.claude/skills/CLAUDE.md`（superpowers 技能索引说明），该位置不在 Claude Code 加载路径

## 二、根因分析（源码级）

阅读安装器 `bin/superpowers-zh.js`，关键逻辑如下：

### 1. 路径定位以 cwd 为项目根

```js
// 第 42 行
const PROJECT_DIR = process.cwd();

// 第 50 行 TARGETS 表
{ name: 'Claude Code', dir: '.claude/skills', detect: '.claude' }
```

skills 目标目录是 `cwd/.claude/skills/`，CLAUDE.md 写到 `cwd/CLAUDE.md`，均相对当前工作目录拼接。

### 2. 主目录保护

```js
// 第 702-721 行
if (!force && isHomeDir(PROJECT_DIR)) {
  // 拒绝在 ~ 安装，除非 --force
  process.exit(1);
}
```

cwd 为 `~` 时直接拒绝，避免污染所有项目。

### 3. CLAUDE.md 写入策略（追加 + sentinel，不覆盖）

```js
// 第 391-403 行
const mdPath = resolve(projectDir, 'CLAUDE.md');
if (existsSync(mdPath)) {
  const existing = readFileSync(mdPath, 'utf8');
  if (!existing.includes('superpowers-zh')) {
    // 追加：原内容 + 空行 + sentinel 包裹块，原内容不动
    writeFileSync(mdPath, existing.replace(/\s+$/, '') + '\n\n' + wrapWithSentinel(content));
  } else {
    // 已含 superpowers-zh -> 跳过，完全不动
  }
} else {
  // 文件不存在才新建
}
```

sentinel 标记（第 98-99 行）：

```
<!-- superpowers-zh:begin (do not edit between these markers) -->
<!-- superpowers-zh:end -->
```

### 4. 结论：设计为项目级安装，无全局安装模式

| cwd | skills 装到 | CLAUDE.md 写到 | 问题 |
|-----|------------|---------------|------|
| `~/.claude` | `~/.claude/.claude/skills/` | `~/.claude/CLAUDE.md`（追加） | **skills 嵌套**，CLAUDE.md 位置对 |
| `~`（home） | `~/.claude/skills/` ✓ | `~/CLAUDE.md`（home 根） | skills 对，CLAUDE.md 位置错；需 `--force` 绕过主目录保护 |
| 任意项目目录 | `项目/.claude/skills/` | `项目/CLAUDE.md` | 项目级，非全局 |

无论在哪执行，skills 与 CLAUDE.md 总有一个位置不对，无法一次 `npx` 调用同时写对全局位置。

## 三、解决方案

采用**方案 A：手动移动已装文件 + 手动追加 CLAUDE.md sentinel 块**。

理由：
- 20 个技能文件已在磁盘（仅位置错一层），`mv` 一步到位
- `~/.claude/CLAUDE.md`（手写全局指令）零接触，不跑安装器、无覆盖风险
- 不与安装器路径推断博弈

## 四、操作记录

### 步骤 1：移动 20 个技能到正确层级

```bash
mv ~/.claude/skills/.claude/skills/* ~/.claude/skills/
rmdir ~/.claude/skills/.claude/skills
rmdir ~/.claude/skills/.claude
```

### 步骤 2：备份全局 CLAUDE.md

```bash
mkdir -p ~/.claude/backups
cp ~/.claude/CLAUDE.md ~/.claude/backups/CLAUDE.md.bak.20260711_161843
```

### 步骤 3：追加 superpowers sentinel 引用块到全局 CLAUDE.md

追加源为误生成的 `~/.claude/skills/CLAUDE.md`（其内容即安装器 `generateClaudeCodeBootstrap` 产出的标准 sentinel 块，含 20 个技能清单）：

```bash
printf '\n\n' >> ~/.claude/CLAUDE.md
cat ~/.claude/skills/CLAUDE.md >> ~/.claude/CLAUDE.md
```

> 注：原 `~/.claude/CLAUDE.md` 末尾无换行符（8155 字节、113 个 `\n`、实际 114 行内容），`printf '\n\n'` 同时补齐原末行换行与块间空行。

## 五、验证结果

### 1. 技能目录（步骤 1）

- `~/.claude/skills/` 顶层共 **21 个目录**：20 个 superpowers 技能 + `icode-skill`
- SKILL.md 完整性：**21/21，0 缺失**
- frontmatter 注册字段正常（如 `name: brainstorming`）
- 嵌套 `~/.claude/skills/.claude/` 已删除
- 误生成的 `~/.claude/skills/CLAUDE.md` 保留作参考（不在加载路径，无害）

### 2. 全局 CLAUDE.md（步骤 3）

- 原内容字节级校验：前 8155 字节 SHA = `c486b0493ae2a3367c651f54d2ebc8df`，与备份一致，**未改动**
- 文件结构：

```
第 1~114 行   原有全局指令（未改动）
第 115 行     空行分隔
第 116 行     <!-- superpowers-zh:begin (do not edit between these markers) -->
第 117~157 行 Superpowers-ZH 引用块（20 个技能清单 + 核心规则 + 使用说明）
第 158 行     <!-- superpowers-zh:end -->
```

- 总行数 158，总字节 12684

## 六、关键文件清单

| 文件 | 说明 |
|------|------|
| `~/.claude/CLAUDE.md` | 全局指令，末尾追加 superpowers sentinel 引用块（116~158 行） |
| `~/.claude/skills/<20个技能>/` | 全局技能目录，已就位 |
| `~/.claude/skills/icode-skill/` | 原有技能，未受影响 |
| `~/.claude/skills/CLAUDE.md` | superpowers 误生成的索引说明，保留作参考 |
| `~/.claude/backups/CLAUDE.md.bak.20260711_161843` | 全局 CLAUDE.md 追加前备份，回滚用 |
| `~/.npm/_npx/b45846acb10a9395/node_modules/superpowers-zh/` | npx 缓存的安装器源码 |

## 七、维护指引

### 1. 生效方式

技能在会话启动时加载，操作完成后需**重启 Claude Code 会话**，20 个命令才可用。

### 2. 重复执行 npx 安全性

操作后再跑 `npx superpowers-zh`：
- CLAUDE.md 已含 "superpowers-zh" -> 安装器检测到后**跳过追加**，不会重复
- 但 skills 仍会装到 `cwd/.claude/skills/`，若 cwd 非 `~` 仍会嵌套，需手动 mv

### 3. 升级 superpowers-zh

安装器无全局安装模式，推荐手动升级：

```bash
# 在任意临时目录跑安装器拿到新版技能文件
cd /tmp && mkdir -p sp-upgrade && cd sp-upgrade && npx superpowers-zh
# 把新版技能覆盖到全局目录
cp -r /tmp/sp-upgrade/.claude/skills/* ~/.claude/skills/
# 清理临时目录
rm -rf /tmp/sp-upgrade
# 若技能清单有变化，同步更新 ~/.claude/CLAUDE.md 的 sentinel 块
```

### 4. 卸载

安装器的 `--uninstall` 只清理 cwd 下的内容，全局卸载需手动：

```bash
# 1. 删除 20 个 superpowers 技能目录（保留 icode-skill）
cd ~/.claude/skills
rm -rf brainstorming writing-plans executing-plans systematic-debugging \
       verification-before-completion chinese-code-review chinese-git-workflow \
       chinese-commit-conventions chinese-documentation dispatching-parallel-agents \
       finishing-a-development-branch mcp-builder receiving-code-review \
       requesting-code-review subagent-driven-development test-driven-development \
       using-git-worktrees using-superpowers workflow-runner writing-skills
# 2. 清除 ~/.claude/CLAUDE.md 中的 sentinel 块（116~158 行）
#    用编辑器删除 <!-- superpowers-zh:begin --> 到 <!-- superpowers-zh:end --> 之间含标记的整段
```

### 5. 回滚全局 CLAUDE.md

```bash
cp ~/.claude/backups/CLAUDE.md.bak.20260711_161843 ~/.claude/CLAUDE.md
```

## 八、与 icode-skill 的关系

`~/.claude/skills/icode-skill/` 是独立的端到端编码工作流技能（`/icode start` / `/icode plan` 等命令），与 superpowers 系列技能**无文件依赖、互不引用**，但理念同源（中文、嵌入式 C/C++、闭环交付、最小改动、Token 治理）。两者可共存，命令空间不冲突（`/icode xxx` vs `/brainstorming` 等）。

全局 `~/.claude/CLAUDE.md` 第六节将 Superpowers 列为最高优先级（第 0 级），icode-skill 作为实际编码工作流补充。
