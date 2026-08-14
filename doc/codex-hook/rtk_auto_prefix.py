#!/usr/bin/env python3
"""
RTK auto-prefix hook for Codex CLI PreToolUse (v2).
matcher: * (匹配所有工具)，脚本内部判断是否需要加 rtk 前缀。

v2 改进（2026-07-16）：
- 基于 allowlist 只对 rtk 支持的命令加前缀，杜绝 help 泄漏
- 跳过注释行、heredoc、写重定向、命令替换等不安全场景
- cat 自动改名为 rtk read
- echo/printf 补入 SHELL_BUILTINS
"""
import sys, json, os, shlex, datetime, re

# ── rtk 支持的子命令（可直接加 rtk 前缀，已验证）──
RTK_SUPPORTED = {
    'ls', 'tree', 'find', 'grep', 'rg', 'wc', 'diff',
    'git', 'gh', 'glab', 'log', 'json', 'env',
    'cargo', 'pytest', 'npm', 'npx', 'curl', 'test', 'err',
    'summary', 'smart', 'docker', 'kubectl',
    'ruff', 'mypy', 'pip', 'go', 'wget',
}

# ── 需要改名的命令（原生 -> rtk 子命令名）──
RTK_RENAME = {
    'cat': 'read',  # cat file -> rtk read file
}

# ── shell 内建命令（不加前缀）──
SHELL_BUILTINS = {
    'cd', 'export', 'source', 'alias', 'unalias', 'eval', 'exec', 'trap',
    'umask', 'set', 'unset', 'exit', 'return', 'shift', 'type', 'hash',
    'getopts', 'command', 'builtin', 'declare', 'local', 'typeset',
    'readonly', 'pushd', 'popd', 'dirs', 'history', 'shopt', 'compgen',
    'complete', 'compopt', 'enable', 'help', 'mapfile', 'readarray',
    'caller', 'coproc', 'suspend', 'times', 'wait', 'jobs', 'fg', 'bg',
    'disown', 'fc', 'bind', 'ulimit', 'continue', 'break', 'read',
    'echo', 'printf',  # v2 补充：echo/printf 是 shell 内建，rtk 无对应子命令
}

SKIP_COMMANDS = {'rtk', 'codex'}
RTK_PATH = os.path.expanduser('~/.local/bin/rtk')
LOG_PATH = '/tmp/rtk_hook_debug.log'

def log(msg):
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(f"{datetime.datetime.now().isoformat()} | {msg}\n")
    except: pass

def _has_write_redirect(tokens):
    """检测 tokens 中是否包含写重定向操作符。
    允许 2>/dev/null、2>&1、1>/dev/null 等数字 fd 重定向。
    跳过 > file、>> file、>file 等写重定向。
    """
    for token in tokens:
        if token in ('>', '>>', '<'):
            return True
        if token.startswith('<<'):      # heredoc
            return True
        if token.startswith('>') and len(token) > 1 and not token[1].isdigit():
            return True                 # >file 但不是 >2
        if token.startswith('>&'):
            return True                 # >&fd 重定向
    return False

def should_prefix(command):
    """返回 (bool_do_prefix, str_rewritten_command_or_None)"""
    command = command.strip()
    if not command or command.startswith('rtk ') or command == 'rtk':
        return False, None

    # v2: 注释行跳过（首个非空字符是 #）
    if command.lstrip().startswith('#'):
        return False, None

    # v2: 命令替换跳过
    if '$(' in command or '`' in command:
        return False, None

    try:
        tokens = shlex.split(command)
    except ValueError:
        return False, None
    if not tokens:
        return False, None

    # v2: 写重定向/heredoc 跳过
    if _has_write_redirect(tokens):
        return False, None

    first = tokens[0]
    basename = os.path.basename(first) if '/' in first else first

    # shell 内建和跳过命令
    if basename in SHELL_BUILTINS or basename in SKIP_COMMANDS:
        return False, None

    # v2: rtk 直接支持的命令 -> 加 rtk 前缀
    if basename in RTK_SUPPORTED:
        return True, f'rtk {command}'

    # v2: 需要改名的命令（cat -> rtk read）
    if basename in RTK_RENAME:
        rtk_sub = RTK_RENAME[basename]
        return True, command.replace(first, f'rtk {rtk_sub}', 1)

    # v2: 不在支持列表中的命令，不加前缀（核心修复：杜绝 help 泄漏）
    return False, None

def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        log("STDIN_PARSE_FAILED")
        sys.exit(0)

    tool_name = data.get('tool_name', 'UNKNOWN')
    tool_input = data.get('tool_input', {})
    command = ''
    if isinstance(tool_input, dict):
        command = tool_input.get('command', '')

    log(f"tool_name={tool_name} | cmd={str(command)[:120]}")

    if not command or not isinstance(command, str):
        sys.exit(0)

    if not os.path.isfile(RTK_PATH) or not os.access(RTK_PATH, os.X_OK):
        sys.exit(0)

    do_prefix, rewritten = should_prefix(command)
    if not do_prefix:
        log(f"SKIP | {command[:80]}")
        sys.exit(0)

    updated = dict(tool_input)
    updated['command'] = rewritten
    log(f"PREFIXED | {command[:80]} -> {rewritten[:80]}")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": updated
        }
    }))

if __name__ == '__main__':
    main()
