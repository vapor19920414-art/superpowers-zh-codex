# RTK Auto-Prefix Hook 优化记录

> 日期：2026-07-16
> 背景：Codex CLI 调研阶段卡死 10 分钟，根因为 rtk hook 对不支持命令加前缀导致 help 泄漏

## 一、问题现象

Codex CLI 执行调研任务时（如查询 CMakeLists.txt 中的 RPATH 配置），单次任务耗时 10+ 分钟，远超合理预期。具体表现为：

1. agent 执行 `sed -n '1,5p' file.c` 等命令
2. hook 自动改写为 `rtk sed -n '1,5p' file.c`
3. rtk 没有 `sed` 子命令，向 stderr 输出完整 help 文本（约 1400 token / 70 行）
4. rtk **不执行原命令**（sed 实际没跑）
5. agent 看到一大段 help 文本，判断出出错，换 Python 重做
6. 每次泄漏 = 1 次浪费往返 + 1 次重试往返 = 至少 2 轮白跑

## 二、根因分析

### 2.1 hook 脚本缺陷（`rtk_auto_prefix.py` v1）

| 缺陷 | 严重度 | 说明 |
|------|--------|------|
| **无 allowlist** | P0 致命 | `should_prefix()` 对所有非 shell-builtin 命令返回 True，导致 `sed`/`awk`/`cut`/`cmake`/`gcc`/`python3`/`cat` 等全部被加 `rtk` 前缀 |
| **注释行被前缀** | P1 严重 | 命令以 `#` 开头时，改写为 `rtk # comment...`，rtk 把 `#` 当未知子命令，dump help |
| **heredoc 被前缀** | P1 严重 | `cat > file << 'EOF'` 改写为 `rtk cat > file << 'EOF'`，rtk 无 `cat` 子命令，dump help |
| **echo/printf 漏网** | P2 中等 | `echo`/`printf` 不在 SHELL_BUILTINS 中，被加前缀 `rtk echo`，dump help |
| **cat 未改名** | P3 低 | rtk 有 `read` 子命令但无 `cat`，应改名而非直接加前缀 |

### 2.2 rtk 行为机制

通过实测确认 rtk 对未知子命令的行为：

```
rtk <已知子命令> <args>    -> 正常执行，输出过滤后的结果
rtk <未知子命令> <args>    -> 向 stderr 输出完整 help（~1400 token），不执行原命令
rtk run <任意命令>         -> 安全执行（无过滤但无 help 泄漏）
```

Codex CLI 的 PTY 会捕获 stderr，所以 help 文本会进入 agent 上下文，造成 token 浪费。

### 2.3 与 AGENTS.md 约束的关系

**不是 AGENTS.md 的问题。** AGENTS.md 的"前置三问""先读后改"只增加 2-3 次合理查询。瓶颈是 hook 的"无脑前缀"策略，与 AGENTS.md 约束无关。

## 三、修复方案

### 3.1 RTK.md 重写（`~/.codex/RTK.md`）

从"Always prefix shell commands with rtk"改为三张精确表：

| 表 | 内容 | 作用 |
|----|------|------|
| 支持表 | ls/tree/find/grep/rg/wc/diff/git/... 25 个命令 | 可安全加 rtk 前缀 |
| 改名表 | cat->rtk read、head->rtk read --max-lines、tail->rtk read --tail-lines | 需换子命令名 |
| 禁用表 | sed/awk/cut/sort/cmake/gcc/python3/make/... | 禁止加 rtk 前缀，直接用原生 |

### 3.2 hook 脚本重写（`~/.codex/hooks/rtk_auto_prefix.py` v2）

核心改动：

```python
# v1: 黑名单策略（除 builtin 外全部前缀）-> help 泄漏
return basename not in SHELL_BUILTINS and basename not in SKIP_COMMANDS

# v2: 白名单策略（只前缀 rtk 支持的命令）-> 杜绝泄漏
if basename in RTK_SUPPORTED:
    return True, f'rtk {command}'
if basename in RTK_RENAME:
    rtk_sub = RTK_RENAME[basename]
    return True, command.replace(first, f'rtk {rtk_sub}', 1)
return False, None  # 不支持的命令，不加前缀
```

新增安全过滤：

| 过滤项 | 实现 | 场景 |
|--------|------|------|
| 注释行 | `command.lstrip().startswith('#')` | `# comment\ncommand` |
| heredoc | token 检测 `<<` | `cat > file << 'EOF'` |
| 写重定向 | token 检测 `>`/`>>` (排除 `2>/dev/null`) | `echo "x" > file` |
| 命令替换 | 字符串检测 `$(` / backtick | `result=$(cmd)` |
| echo/printf | 加入 SHELL_BUILTINS | `echo "==="` |

### 3.3 RTK_SUPPORTED 白名单（已验证）

通过 `rtk --help` + `rtk hook check` 交叉验证的子命令列表：

```
ls tree find grep rg wc diff     # 文件/搜索
git gh glab                      # Git
log json env                     # 工具
cargo pytest npm npx curl        # 构建/测试
test err summary smart           # 输出过滤
docker kubectl                   # 容器
ruff mypy pip go wget            # 语言工具
```

RTK_RENAME 改名映射：

```
cat -> rtk read    # cat file -> rtk read file
```

> `head`/`tail` 的改名逻辑较复杂（需解析 `-N` 参数位置），暂不自动改名，由 agent 按 RTK.md 手动使用 `rtk read --max-lines N` / `--tail-lines N`。

## 四、修复前后对比

| 指标 | v1（修复前） | v2（修复后） |
|------|-------------|-------------|
| `sed` 命令 | `rtk sed` -> help 泄漏 ~1400 token | `sed`（原生，不前缀） |
| `awk` 命令 | `rtk awk` -> help 泄漏 | `awk`（原生，不前缀） |
| `cat file` | `rtk cat` -> help 泄漏 | `rtk read file`（正确改名） |
| `# comment\ncmd` | `rtk # comment` -> help 泄漏 | 跳过（不前缀） |
| `echo "x"` | `rtk echo` -> help 泄漏 | `echo "x"`（builtin，不前缀） |
| `grep -n pat file` | `rtk grep -n pat file`（正确） | `rtk grep -n pat file`（不变） |
| `ls -la` | `rtk ls -la`（正确） | `rtk ls -la`（不变） |
| `cat > file << 'EOF'` | `rtk cat > file` -> help 泄漏 | 跳过（heredoc，不前缀） |
| 每次泄漏 token | ~1400 | 0 |
| 10 分钟调研阶段 | 3-4 次泄漏 = ~5000 token 浪费 | 0 次泄漏 |

## 五、验证方法

### 5.1 hook 日志验证

```bash
# 清空日志后执行几条命令，检查日志中的 PREFIXED/SKIP 记录
> /tmp/rtk_hook_debug.log
# 在 Codex CLI 中执行：
#   grep -n 'pat' file    -> 应记录 PREFIXED ... rtk grep
#   sed 's/a/b/' file     -> 应记录 SKIP
#   cat file              -> 应记录 PREFIXED ... rtk read
#   echo "hello"          -> 应记录 SKIP
command tail -20 /tmp/rtk_hook_debug.log
```

### 5.2 rtk 子命令验证

```bash
# 确认 rtk 对某命令是否有专门子命令
rtk hook check "命令"
# 输出 "rtk xxx" = 有子命令，可安全前缀
# 输出 "No rewrite for: xxx" = 无子命令，不应前缀
```

### 5.3 回退方案

如 v2 hook 出现问题，可临时禁用：

```bash
# 方法1：重命名 hooks.json
mv ~/.codex/hooks.json ~/.codex/hooks.json.bak

# 方法2：恢复 v1（不推荐）
# v1 代码见 git 历史
```

## 六、涉及文件

| 文件 | 改动 |
|------|------|
| `~/.codex/RTK.md` | 全文重写，从"无脑前缀"改为白名单+改名表+禁用表 |
| `~/.codex/hooks/rtk_auto_prefix.py` | v2 重写，黑名单策略改白名单，新增安全过滤 |
| `~/.claude/skills/doc/rtk-hook-optimization.md` | 本文档（追溯记录） |

## 七、后续优化方向

1. **head/tail 自动改名**：解析 `-N` / `-n N` 参数位置，自动改写为 `rtk read --max-lines N` / `--tail-lines N`
2. **管道链智能前缀**：对 `cmd1 | cmd2` 中的每段独立判断是否加 rtk 前缀（当前只前缀首段）
3. **rtk 子命令同步**：rtk 更版本后，用 `rtk --help` 输出自动更新 RTK_SUPPORTED 白名单
