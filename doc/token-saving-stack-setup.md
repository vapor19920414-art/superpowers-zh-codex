# Codex CLI Token 节省工具栈部署文档

> 创建日期：2026-07-14
> 适用环境：Codex CLI + GLM 模型（自定义 provider）+ 嵌入式 C/C++ 项目
> 部署状态：headroom + RTK + CodeGraph + Ponytail 四件套已就绪

---

## 一、背景与目标

Codex CLI 会话中 token 消耗主要来自以下几个环节：

```
命令输出（ls/cat/grep/git/编译日志）  →  占比最大，单次可达数万 token
文件读取（Read/cat/head）             →  查调用链需读多个文件
MCP 工具响应                          →  数据库/API/搜索结果可能很大
大文本输入（长源码/长日志/大 JSON）    →  一次性塞入上下文
AI 回复输出                           →  冗长解释浪费输出 token
会话历史累积                          →  上下文窗口逐渐膨胀
```

**目标**：在各个环节部署对应的 token 节省工具，形成"自动拦截 + 手动压缩 + 精准检索"的多层防护，最大化降低单次会话 token 消耗。

---

## 二、当前已部署工具栈总览

| 工具 | 版本 | 类型 | 覆盖环节 | 部署方式 | 状态 |
|------|------|------|----------|----------|------|
| **headroom** | - | MCP | 大文本手动压缩 + 存储 + 取回 | config.toml MCP server | ✅ 已有 |
| **RTK** | v0.43.0 | CLI 代理 + 指令 | 命令输出自动压缩 60-90% | ~/.local/bin + AGENTS.md 引用 | ✅ 新装 |
| **CodeGraph** | v1.4.1 | MCP | 代码知识图谱，减少文件读取 | config.toml MCP server | ✅ 新装 |
| **Ponytail** | v4.9.0 | Codex plugin | 收敛实现与评审中的过度设计 | Codex plugin marketplace | ✅ 已装（默认 full） |

### 四者互补关系

```
┌─────────────────────────────────────────────────────────────┐
│                    Codex CLI 会话 token 流向                  │
│                                                             │
│  [命令输出] ──▶ RTK 自动压缩 60-90%（rtk 前缀拦截）          │
│  [文件读取] ──▶ CodeGraph 图谱精准返回（1次MCP调用替代N次读） │
│  [大文本]   ──▶ headroom 手动压缩+存储+按hash取回            │
│  [实现评审] ──▶ Ponytail 按 YAGNI 收敛实现（默认 full）       │
│                                                             │
│  四者覆盖不同环节，互不冲突，可叠加使用                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 三、各工具详情

### 3.1 headroom（已有）

**功能**：手动/按需压缩大文本（源码、日志、搜索结果、JSON、diff），存储后按 hash 取回。

**MCP 工具**：
- `headroom_stats` — 统计压缩次数、节省 token、近期事件
- `headroom_compress` — 压缩长文本，返回 hash
- `headroom_retrieve` — 按 hash 取回原文，支持 query 定向检索

**触发阈值**：源码超过 500 行、日志/命令输出超过 300 行、大型 diff/JSON 时调用。

**配置**（`~/.codex/config.toml`）：
```toml
[mcp_servers.headroom]
type = "stdio"
command = "/home/changyuchun/.local/bin/headroom"
args = ["mcp", "serve"]
startupTimeout = 30
toolTimeout = 90
required = false
```

**获取方式**：
- 二进制位置：`/home/changyuchun/.local/bin/headroom`
- 详细配置文档：`~/.codex/skills/doc/headroom-codex-ccswitch-setup.md`

---

### 3.2 RTK（Rust Token Killer）— 新装

**功能**：CLI 代理，自动过滤/压缩命令输出后才进入 LLM 上下文。单个 Rust 二进制，<10ms 开销，支持 100+ 命令。

**省 token 效果**（30 分钟会话实测估算）：

| 操作 | 频率 | 标准 | RTK | 节省 |
|------|------|------|-----|------|
| ls / tree | 10x | 2,000 | 400 | -80% |
| cat / read | 20x | 40,000 | 12,000 | -70% |
| grep / rg | 8x | 16,000 | 3,200 | -80% |
| git status | 10x | 3,000 | 600 | -80% |
| git diff | 5x | 10,000 | 2,500 | -75% |
| git log | 5x | 2,500 | 500 | -80% |
| cargo/npm test | 5x | 25,000 | 2,500 | -90% |
| **合计** | | ~118,000 | ~23,900 | **-80%** |

**Codex 配置方式**：RTK 对 Codex 使用"AGENTS.md + RTK.md 指令"模式（非自动 hook），AI 会根据指令在执行 shell 命令时自动加 `rtk` 前缀。

**实际验证**（2026-07-14）：
```
$ rtk git status
* master...origin/master [behind 2]
clean - nothing to commit

$ rtk gain
Total commands:    1
Tokens saved:      30 (65.2%)
```

**配置文件**：
- `~/.codex/RTK.md` — RTK 使用指令（让 AI 自动加 rtk 前缀）
- `~/.codex/AGENTS.md` 末尾添加了 `@/home/changyuchun/.codex/RTK.md` 引用

**获取与安装方式**：
```bash
# 安装 需要更新重新执行一次指令
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
# 安装到 ~/.local/bin/rtk

# 配置 Codex
rtk init -g --codex
# 自动创建 ~/.codex/RTK.md 并在 AGENTS.md 末尾加引用

# 验证
rtk --version    # rtk 0.43.0
rtk gain         # 查看 token 节省统计

# 其他安装方式
brew install rtk                          # macOS Homebrew
cargo install --git https://github.com/rtk-ai/rtk  # Cargo
```

**常用命令**：
```bash
rtk git status          # 精简 git status
rtk git diff            # 精简 git diff
rtk cat <file>          # 精简文件内容
rtk rg <pattern>        # 精简搜索结果
rtk pytest -q           # 精简测试输出
rtk gain                # 查看 token 节省统计
rtk gain --history      # 查看最近命令节省历史
rtk proxy <cmd>         # 不压缩，原样运行（需要完整输出时用）
```

**项目信息**：
- 仓库：https://github.com/rtk-ai/rtk
- Stars：70,901
- 语言：Rust
- 许可证：见仓库

**注意事项**：
- RTK 对 Codex 是指令模式（AI 自动加 rtk 前缀），不是 hook 自动改写
- `rtk proxy <cmd>` 可绕过压缩，需要完整输出时使用
- RTK 只压缩 bash 命令输出，不压缩 MCP 工具响应

---

### 3.3 CodeGraph — 新装

**功能**：预索引 SQLite 代码知识图谱，文件变更自动同步。通过 1 个 MCP 工具返回函数源码 + 调用路径，替代多次文件读取。100% 本地运行。

**语言支持**（与本项目相关）：
- C（`.c`, `.h`）— Full support ✅
- C++（`.cpp`, `.hpp`, `.cc`）— Full support ✅
- Python（`.py`）— Full support ✅
- Shell/CMake 等不在列表内

**省 token 原理**：
```
传统方式：查一个函数调用链 → cat 10个文件 → 40,000 tokens
CodeGraph：1次 codegraph_explore MCP 调用 → 返回精确源码+调用路径 → 3,000 tokens
```

**MCP 配置**（`~/.codex/config.toml`）：
```toml
[mcp_servers.codegraph]
type = "stdio"
command = "/home/changyuchun/.local/bin/codegraph"
args = ["serve", "--mcp"]
startupTimeout = 30
toolTimeout = 90
required = false
```

**获取与安装方式**：
```bash
# 安装
curl -fsSL https://raw.githubusercontent.com/colbymchenry/codegraph/main/install.sh | sh
# 安装到 ~/.codegraph/versions/v1.4.1，链接到 ~/.local/bin/codegraph

# 验证
codegraph --version    # 1.4.1

# 打印 MCP 配置片段（用于手动配置）
codegraph install --print-config codex
# 输出：
# [mcp_servers.codegraph]
# command = "codegraph"
# args = ["serve", "--mcp"]

# 自动安装到 Codex（替代手动编辑 config.toml）
codegraph install --target codex --location global -y
```

**项目索引**（⚠️ 当前项目尚未建索引，需手动执行）：
```bash
# 在项目根目录执行
cd /home/changyuchun/work/work/RN2601/mowerware_rn2601
codegraph init .

# 索引完成后查看状态
codegraph status

# 后续文件变更后同步
codegraph sync .

# 重建索引（从头开始）
codegraph index .
```

**⚠️ 本项目索引注意事项**：
- 项目 5.9G、54453 个文件、20648 个 C/C++ 文件，首次索引耗时较长
- `thirdparty/`（1.1G）会被索引，如不需要可在 .gitignore 中排除或使用 `.codegraphignore`
- `build/`、`install/` 已在 .gitignore 中排除，CodeGraph 会自动跳过
- 建议在空闲时执行首次索引，或只索引核心源码目录

**MCP 工具**（Codex 自动调用）：
- `codegraph_explore` — 探索某个区域：相关符号源码 + 调用路径
- `codegraph_node` — 查看单个符号的源码 + 调用者/被调用者
- `codegraph_callers` — 查找所有调用某函数的位置
- `codegraph_callees` — 查找某函数调用的所有函数
- `codegraph_impact` — 分析修改某符号会影响哪些代码

**CLI 命令**（手动查询）：
```bash
codegraph query <search>        # 搜索符号
codegraph explore <query>       # 探索区域（同 MCP 工具）
codegraph node <name>           # 查看符号详情
codegraph callers <symbol>      # 查找调用者
codegraph callees <symbol>      # 查找被调用者
codegraph impact <symbol>       # 影响分析
codegraph files                 # 查看项目文件结构
codegraph status                # 索引状态
codegraph sync                  # 同步变更
```

**项目信息**：
- 仓库：https://github.com/colbymchenry/codegraph
- Stars：59,834
- 语言：TypeScript
- 许可证：MIT

---

### 3.4 Ponytail（默认 full）

**功能**：在实现和评审阶段优先采用 YAGNI、标准库、原生能力和最小正确改动，减少过度设计与无效代码。

**安装方式**：

```bash
codex plugin marketplace add DietrichGebert/ponytail
codex plugin add ponytail@ponytail
```

安装后启动 Codex，通过 `/hooks` 审核并信任 Ponytail 的两个 lifecycle hooks，然后新建会话。Codex Desktop 安装后需要重启。

**常用命令**：

```text
@ponytail                 # 启用默认 full 模式
@ponytail-review          # 审查当前 diff 中的过度设计
@ponytail-audit           # 审计整个仓库的过度设计
@ponytail-help            # 查看帮助
@ponytail off             # 临时关闭
```

**验证方式**：

```bash
codex plugin list
```

**升级插件**：

```bash
codex plugin marketplace upgrade
```

输出中应包含 `ponytail@ponytail`，且状态为 `installed, enabled`。

**与 Superpowers Skills 的关系**：Superpowers Skills 负责需求、调试和验证流程，Ponytail `full` 负责收敛实现；用户指令和 `AGENTS.md` 优先，Ponytail 不得跳过安全或验证要求。默认保持 `full`，仅在实际出现漏实现或误删必要逻辑时再降为 `lite`。

---

## 四、当前 config.toml 完整配置（MCP 部分）

```toml
[mcp_servers]

[mcp_servers.headroom]
type = "stdio"
command = "/home/changyuchun/.local/bin/headroom"
args = ["mcp", "serve"]
startupTimeout = 30
toolTimeout = 90
required = false

[mcp_servers.codegraph]
type = "stdio"
command = "/home/changyuchun/.local/bin/codegraph"
args = ["serve", "--mcp"]
startupTimeout = 30
toolTimeout = 90
required = false
```

> RTK 不在 config.toml 中，它通过 `~/.codex/RTK.md` 指令文件 + AGENTS.md 引用工作；Ponytail 由 Codex plugin 管理，也不写入 config.toml。

---

## 五、其他可选 token 节省工具（未安装，按需评估）

### 5.1 caveman（输出端压缩）

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/JuliusBrussee/caveman |
| Stars | 89,276 |
| 功能 | 让 AI 用精简"穴居人式"语言回复，省 65% 输出 token |
| Codex 支持 | ✅ `npx skills add JuliusBrussee/caveman -a codex` |
| 和已装工具关系 | 不重叠（caveman 管输出，RTK/headroom 管输入） |
| ⚠️ 注意 | caveman 是英文优化的，对中文回复压缩效果需实测 |

```bash
npx skills add JuliusBrussee/caveman -a codex
```

### 5.2 Context Mode（上下文管理）

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/mksglu/context-mode |
| Stars | 18,917 |
| 功能 | 自动隔离工具输出（98%减少）+ SQLite会话记忆 + think-in-code |
| Codex 支持 | ✅ Hook + MCP |
| 和已装工具关系 | 与 headroom 部分重叠（都管上下文），同时用需谨慎 |
| ⚠️ 注意 | 功能重，可能和 headroom 冲突，建议二选一 |

### 5.3 mcpslim（MCP 工具响应压缩）

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/suncal/mcpslim |
| Stars | 0（新项目） |
| 功能 | MCP 代理，压缩 MCP 工具的 tools/call 响应 |
| 和已装工具关系 | 互补（RTK 压缩命令输出，mcpslim 压缩 MCP 响应） |
| ⚠️ 注意 | 需 git clone + npm link 手动安装，⭐0 需评估稳定性 |

### 5.4 tokless（一键安装器）

| 项 | 值 |
|---|---|
| 仓库 | https://github.com/HoangP8/tokless |
| Stars | 125 |
| 功能 | 一键安装 RTK + caveman + CodeGraph + Context Mode 等到 Codex |
| 安装 | `curl -fsSL https://raw.githubusercontent.com/HoangP8/tokless/main/scripts/install.sh \| bash` |
| ⚠️ 注意 | 会写入 AGENTS.md 等指令文件，可能和现有配置冲突 |

---

## 六、部署验证清单

| 检查项 | 状态 | 验证方式 |
|--------|------|----------|
| headroom MCP 配置保留 | ✅ | config.toml 第 24-30 行 |
| RTK 安装 | ✅ | `rtk --version` → rtk 0.43.0 |
| RTK Codex 配置 | ✅ | `~/.codex/RTK.md` 存在 + AGENTS.md 引用 |
| RTK 命令可用 | ✅ | `rtk git status` 正常输出 + `rtk gain` 显示 65.2% 节省 |
| CodeGraph 安装 | ✅ | `codegraph --version` → 1.4.1 |
| CodeGraph MCP 配置 | ✅ | config.toml 第 32-38 行 |
| CodeGraph MCP 可启动 | ✅ | `codegraph serve --mcp` 正常启动 |
| CodeGraph 项目索引 | ⏳ 待建 | 需在项目目录运行 `codegraph init .` |
| Ponytail 插件 | ✅ | `codex plugin list` → `ponytail@ponytail installed, enabled 4.9.0` |
| config.toml 备份 | ✅ | `~/.codex/config.toml.bak.20260714_173342` |
| AGENTS.md 备份 | ✅ | `~/.codex/AGENTS.md.bak.20260714_173441` |

---

## 七、使用建议

### 日常使用

1. **RTK 自动生效**：AI 会根据 RTK.md 指令自动给命令加 `rtk` 前缀，无需手动干预
2. **CodeGraph 查代码**：需要查函数调用链时，AI 会自动调用 codegraph MCP 工具（需先建索引）
3. **headroom 压大文本**：遇到超长日志/源码时，AI 会调用 headroom 压缩存储
4. **Ponytail 收敛实现**：编码和评审时默认使用 full 模式；临时关闭时输入 `@ponytail off`

### 建索引建议（CodeGraph）

本项目 5.9G 较大，建议分步索引：

```bash
# 方案 A：全量索引（耗时较长，建议空闲时执行）
cd /home/changyuchun/work/work/RN2601/mowerware_rn2601
codegraph init .

# 方案 B：只索引核心源码目录（推荐先试）
# 先在子目录建索引，验证效果后再全量
cd /home/changyuchun/work/work/RN2601/mowerware_rn2601/common
codegraph init .
```

### 回滚方式

如需回滚到安装前状态：

```bash
# 恢复 config.toml
cp ~/.codex/config.toml.bak.20260714_173342 ~/.codex/config.toml

# 恢复 AGENTS.md
cp ~/.codex/AGENTS.md.bak.20260714_173441 ~/.codex/AGENTS.md

# 删除 RTK.md
rm ~/.codex/RTK.md

# 卸载 RTK
rm ~/.local/bin/rtk

# 卸载 CodeGraph
rm -rf ~/.codegraph ~/.local/bin/codegraph

# 卸载 Ponytail 并移除 marketplace
codex plugin remove ponytail@ponytail
codex plugin marketplace remove ponytail
```

---

## 八、总结

当前 Codex CLI token 节省工具栈由四个环节组成：

| 层级 | 工具 | 机制 | 自动/手动 | 节省效果 |
|------|------|------|-----------|----------|
| 命令输出层 | RTK | rtk 前缀拦截压缩 | 自动（指令模式） | 60-90% |
| 代码检索层 | CodeGraph | SQLite 图谱精准返回 | 自动（MCP） | 替代 N 次文件读取 |
| 大文本层 | headroom | 压缩+存储+取回 | 手动（MCP） | 按需压缩 |
| 实现评审层 | Ponytail | YAGNI + 最小正确改动 | 自动（plugin） | 减少无效代码与解释成本 |

四者覆盖不同环节，互不冲突，可叠加使用。对于嵌入式 C/C++ 项目，RTK 压缩编译日志和 git 操作输出效果最显著，CodeGraph 的 C/C++ Full support 适合查调用链，headroom 兜底处理漏网的大文本，Ponytail 在实现和评审阶段控制不必要的复杂度。

> 本文档路径：`~/.codex/skills/doc/token-saving-stack-setup.md`
> 配置备份：`~/.codex/config.toml.bak.20260714_173342`、`~/.codex/AGENTS.md.bak.20260714_173441`

---

## 九、RTK 被动 Hook 模式（自动拦截，无需 AI 配合）

### 背景

RTK 默认对 Codex 使用"指令模式"（RTK.md 让 AI 主动加 rtk 前缀），效果取决于模型的指令遵循能力。Codex CLI 支持 PreToolUse hook，可以在命令执行前**自动改写命令**，实现真正的被动拦截。

### 原理

```
大模型生成命令: git diff
       ↓
Codex PreToolUse hook 触发
       ↓
rtk_auto_prefix.py 拦截
       ↓
返回 updatedInput: rtk git diff
       ↓
Codex 执行改写后的命令: rtk git diff（压缩输出）
       ↓
大模型收到压缩后的输出（完全无感知）
```

### 已部署文件

| 文件 | 路径 | 作用 |
|------|------|------|
| hook 脚本 | `~/.codex/hooks/rtk_auto_prefix.py` | 拦截 Bash 命令，自动加 rtk 前缀 |
| hook 配置 | `~/.codex/hooks.json` | 注册 PreToolUse hook 到 Codex |

### hook 脚本逻辑

1. 读取 stdin JSON（包含 tool_name, tool_input.command）
2. 检查 tool_name == "Bash"，否则放行
3. 检查命令第一个 token：
   - shell 内建命令（cd/export/source/eval 等 50+ 个）-> 放行（rtk 无法代理）
   - 已有 rtk 前缀 -> 放行（避免双重前缀）
   - 特殊命令（rtk/codex）-> 放行
   - 其他命令 -> 加 rtk 前缀
4. 返回 `permissionDecision: "allow"` + `updatedInput.command`
5. 保留原始 tool_input 的其他字段（如 workdir）

### ⚠️ 启用步骤（必须手动信任 hook）

Codex 要求非 managed hook 必须经过用户信任才能运行：

```bash
# 方式 1：在 Codex CLI 中信任（推荐）
# 启动 Codex 后输入 /hooks，找到 rtk_auto_prefix.py，选择 trust
************************************************************
  Hooks need review
  1 hook is new or changed.
  Hooks can run outside the sandbox after you trust them.

  1. Review hooks
› 2. Trust all and continue
  3. Continue without trusting (hooks won't run)

  Press enter to confirm or esc to go back
************************************************************

# 方式 2：跳过信任检查（每次启动需加 flag）
codex --dangerously-bypass-hook-trust
```

> 如果 hook 未被信任，Codex 启动时会打印警告提示打开 /hooks。

### 两种模式共存策略

| 模式 | 机制 | 覆盖率 | 依赖 |
|------|------|--------|------|
| **Hook 模式**（新） | PreToolUse 自动改写命令 | 高（拦截简单 Bash 命令） | 需信任 hook |
| **指令模式**（已有） | RTK.md 让 AI 主动加前缀 | 中（取决于模型遵循度） | AGENTS.md 引用 |

两种模式共存互补：
- Hook 模式作为主力的自动拦截
- 指令模式作为补充（hook 未拦截的命令，AI 仍可手动加前缀）
- 已加 rtk 前缀的命令会被 hook 脚本识别并放行，不会双重前缀

### 已知限制

1. **unified_exec 拦截不完整**：Codex 文档明确说 "This doesn't intercept all shell calls yet, only the simple ones. The newer unified_exec mechanism allows richer streaming stdin/stdout handling of shell, but interception is incomplete." 部分通过 unified_exec 执行的命令可能不被 hook 拦截。
2. **复合命令只改写第一个**：`ls -la && echo done` 会变成 `rtk ls -la && echo done`，只有 ls 被 rtk 处理，echo 不被处理。
3. **shell 内建命令排除**：cd/export/source 等内建命令不加 rtk 前缀（rtk 无法代理）。
4. **MCP 工具不经过 hook**：MCP 工具调用（如 headroom/codegraph）不经过 Bash hook，不受影响。

### 禁用 hook

如需临时禁用 hook 模式（保留指令模式）：

```bash
# 方式 1：在 config.toml 中关闭 hooks 功能
# [features]
# hooks = false

# 方式 2：在 Codex CLI 中 /hooks 禁用
# 方式 3：重命名 hooks.json
mv ~/.codex/hooks.json ~/.codex/hooks.json.disabled
```

### 测试验证（2026-07-14）

```
✅ git diff HEAD~1     -> rtk git diff HEAD~1（改写）
✅ cd /tmp             -> 放行（shell 内建）
✅ rtk git status      -> 放行（已有前缀）
✅ apply_patch         -> 放行（非 Bash 工具）
✅ ls -la && echo done -> rtk ls -la && echo done（改写第一个命令）
✅ export PATH=...     -> 放行（shell 内建）
✅ 保留 workdir 字段   -> 改写 command 且保留 workdir
```

---

## 十、CodeGraph 被动调用与自动同步机制

### 1. 被动调用：MCP initialize 自动暴露工具

CodeGraph MCP server 启动时，通过 MCP `initialize` 协议自动向 Codex 暴露 `codegraph_explore` 工具。大模型在需要查代码时会自动调用该工具，**不需要手动触发**。

**主 agent**：MCP initialize 自动暴露工具描述，主 agent 自然知道何时使用。
**Subagents**：subagents 不收到 MCP initialize 指令，需要 AGENTS.md 中的 CodeGraph section 引导（已添加）。

> 官方实测数据（CodeGraph issue #704）：没有 AGENTS.md section 时，subagents 仅 1/9 概率使用 codegraph；有 section 后一致使用。

### 2. AGENTS.md 优化（已完成）

在 AGENTS.md 中添加了两处改动：

**工具使用优先级**（第六节）：
```
1. codegraph：函数调用链查询、符号定义检索、影响分析（MCP 工具，需已建索引）
2. auggie：跨文件语义分析（codegraph 未索引时使用）
3. 高速检索：rg、fd、fzf
4. Token 治理工具：headroom
5. 基础兜底：Read、Grep、Glob、Find、Kill
```

**CodeGraph section**（AGENTS.md 末尾，CODEGRAPH_START/END 标记内）：
引导模型在已索引项目中优先使用 `codegraph_explore` 而非 grep/find/逐文件读取。

### 3. 自动增量同步：file watcher 默认开启

`codegraph serve --mcp` 默认启动 file watcher（native OS file events）：

- **文件变更自动检测**：使用操作系统原生文件事件（inotify/FSEvents）
- **2 秒防抖**：变更后等待 2 秒安静窗口再同步，避免频繁触发
- **仅源码文件**：只同步代码文件，跳过二进制/缓存/构建产物
- **增量同步**：只更新变更部分，不全量重建

**不需要手动 `codegraph sync .`**，除非：
- 用 `--no-watch` 禁用了 watcher（慢速文件系统如 WSL2 /mnt）
- MCP server 未运行时大量文件变更（重启 MCP server 后会自动检测）

### 4. 首次索引注意事项

```bash
# 在项目根目录执行（只需一次）
cd /home/changyuchun/work/work/RN2601/mowerware_rn2601
codegraph init .
```

索引完成后：
- `.codegraph/codegraph.db`（SQLite 数据库）生成在项目根目录
- MCP server 启动后自动监控变更，增量同步
- AGENTS.md 中的 CodeGraph section 生效（检测到 .codegraph/ 目录存在）
- 大模型自动优先使用 codegraph_explore 查代码

### 5. CodeGraph 默认排除规则（无需手动配置）

CodeGraph 自动排除以下内容（即使不在 .gitignore 中）：
- 依赖/构建/缓存目录：`node_modules`, `vendor`, `dist`, `build`, `target`, `.venv`, `Pods` 等
- `.gitignore` 中的所有内容
- 大于 1MB 的文件

如需额外排除（如 `thirdparty/`）或包含被 .gitignore 排除的源码，在项目根目录创建 `codegraph.json`：
```json
{
  "exclude": ["thirdparty/"],
  "include": ["app_communication/", "broker/", "common/"]
}
```
