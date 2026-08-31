# RTK - Rust Token Killer (Codex CLI)

**Usage**: Token-optimized CLI proxy for shell commands.

## 核心规则（重要：避免 help 泄漏）

**不要无脑给所有命令加 `rtk` 前缀！** rtk 只对以下子命令有专门优化。对不在列表中的命令加 `rtk` 前缀，rtk 会输出完整 help 文本（约 1400 token）且不执行原命令，造成严重 token 浪费和流程卡死。

## rtk 支持的子命令（可安全加 `rtk` 前缀）

| 原生命令 | rtk 用法 | 说明 |
|----------|----------|------|
| `ls` | `rtk ls` | 目录列表 |
| `tree` | `rtk tree` | 目录树 |
| `find` | `rtk find` | 文件查找 |
| `grep` | `rtk grep` | 内容搜索 |
| `rg` | `rtk rg` | ripgrep 搜索 |
| `wc` | `rtk wc` | 行/词/字节计数 |
| `diff` | `rtk diff` | 文件差异 |
| `git` | `rtk git` | Git 操作 |
| `gh` | `rtk gh` | GitHub CLI |
| `glab` | `rtk glab` | GitLab CLI |
| `log` | `rtk log` | 文件或 stdin 的日志过滤与去重，不替代系统日志查询 |
| `json` | `rtk json` | JSON 压缩 |
| `env` | `rtk env` | 环境变量 |
| `cargo` | `rtk cargo` | Rust 构建 |
| `pytest` | `rtk pytest` | Python 测试 |
| `npm` | `rtk npm` | npm 运行 |
| `curl` | `rtk curl` | HTTP 请求 |
| `test` | `rtk test` | 测试输出过滤 |
| `err` | `rtk err` | 仅显示错误/警告 |
| `summary` | `rtk summary` | 启发式摘要 |

## 需要改名的命令（原生命令 → rtk 等价用法）

| 原生命令 | rtk 等价 | 注意 |
|----------|----------|------|
| `cat file` | `rtk read file` | 仅小文件或已收窄范围；大日志先检索 |
| `head -N file` | `rtk read file --max-lines N` | 用 --max-lines |
| `tail -N file` | `rtk read file --tail-lines N` | 用 --tail-lines |
| `sed -n '1,5p' file` | `rtk read file --max-lines 5` | 只读行范围时用 read 替代 |

## 固件日志排查规则

1. **首轮定位：** 优先 `rtk rg`；仅已有 `grep` 用法或小范围单文件时使用 `rtk grep`。搜索必须限定日志目录或 `--glob`，并至少包含时间、错误码、模块名、session / request ID 或状态关键词之一。禁止用 `.`、`.*` 模拟全量扫描。
2. **上下文：** 默认 `-C 3`，证据链确需关联时扩大到 `-C 5`。不得用 `-C 20+` 代替缩小时间窗、关键词或目录；首轮命中过多时使用 `-m N` 限制结果。
3. **补证据：** 出现 `[see remaining: ... <tee-file>]` 表示后续内容未进入模型上下文。需要时显式执行 `rtk read <tee-file>`；若再次截断，回到原检索命令收窄条件，不递归读取 tee 文件。
4. **文件读取：** 禁止对原始大日志直接 `cat` 或无边界 `rtk read`。查看当前启动末尾或终态时，使用 `rtk read --tail-lines N`，其中 `N` 必须明确。
5. **摘要边界：** `rtk log` 只用于错误/告警摘要，不得单独作为时序、重复次数或状态机因果的证据。它不是系统日志查询命令；系统日志仍用环境对应的原生命令获取。

## 不支持 rtk 的命令（直接用原生命令，禁止加 rtk 前缀）

以下命令 rtk **没有**对应子命令，加了前缀会触发 help 泄漏（~1400 token），必须直接使用原生命令：

```bash
# 直接用原生，不要加 rtk 前缀
sed 's/old/new/g' file.c        # ❌ rtk sed -> help 泄漏
awk '{print $1}' file.c         # ❌ rtk awk -> help 泄漏
cut -d: -f1 file.c              # ❌ rtk cut -> help 泄漏
sort file.c                     # ❌ rtk sort -> help 泄漏
uniq file.c                     # ❌ rtk uniq -> help 泄漏
tr 'a-z' 'A-Z'                  # ❌ rtk tr -> help 泄漏
cmake ..                        # ❌ rtk cmake -> help 泄漏
gcc -o test test.c              # ❌ rtk gcc -> help 泄漏
python3 script.py               # ❌ rtk python3 -> help 泄漏
make -j4                        # ⚠️ rtk make 会执行但附带 help 泄漏，直接用 make
echo / printf                   # 直接用原生
cp / mv / rm / mkdir / chmod    # 直接用原生
which / type / file / stat      # 直接用原生
```

## 管道链处理

含管道的复合命令中，只对 rtk 支持的命令段加前缀，不支持段保持原生：

```bash
# 正确：grep 段用 rtk，sed 段用原生
rtk grep -n 'pattern' file.c | sed 's/old/new/'
# 或整条用原生（简单管道不需要 rtk 优化）
grep -n 'pattern' file.c | sed 's/old/new/'
```

## 万能兜底

如果不确定某命令是否支持 rtk，用 `rtk run` 执行（无过滤但不会 help 泄漏）：

```bash
rtk run sed 's/old/new/g' file.c   # 安全，等价于直接执行 sed
rtk run cmake ..                    # 安全，等价于直接执行 cmake
```

## Meta Commands

```bash
rtk gain            # Token 节省统计
rtk gain --history  # 历史节省记录
rtk proxy <cmd>     # 原样执行命令（不过滤但跟踪用量）
rtk run <cmd>       # 原样执行命令（不过滤不跟踪）
```

## Verification

```bash
rtk --version
rtk gain
which rtk
```
