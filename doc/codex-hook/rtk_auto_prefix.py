#!/usr/bin/env python3
"""
RTK auto-rewrite hook for Codex CLI PreToolUse (v3).
matcher: * (匹配所有工具)，改写规则统一委托给 rtk rewrite。
"""
import datetime
import json
import os
import subprocess
import sys

RTK_PATH = os.path.expanduser('~/.local/bin/rtk')
LOG_PATH = '/tmp/rtk_hook_debug.log'

def log(msg):
    try:
        with open(LOG_PATH, 'a') as f:
            f.write(f"{datetime.datetime.now().isoformat()} | {msg}\n")
    except: pass

def rewrite_command(command):
    """调用 RTK 的统一规则源，返回 (退出码, 改写后的命令)。"""
    try:
        result = subprocess.run(
            [RTK_PATH, 'rewrite', command],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        log(f'REWRITE_FAILED | {exc}')
        return None, ''
    return result.returncode, result.stdout.strip()

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

    exit_code, rewritten = rewrite_command(command)
    if exit_code not in (0, 3) or not rewritten or rewritten == command:
        log(f"SKIP rc={exit_code} | {command[:80]}")
        sys.exit(0)

    updated = dict(tool_input)
    updated['command'] = rewritten
    hook_output = {
        'hookEventName': 'PreToolUse',
        'updatedInput': updated,
    }
    if exit_code == 0:
        hook_output.update({
            'permissionDecision': 'allow',
            'permissionDecisionReason': 'RTK auto-rewrite',
        })
    log(f"REWRITTEN rc={exit_code} | {command[:80]} -> {rewritten[:80]}")
    print(json.dumps({'hookSpecificOutput': hook_output}))

if __name__ == '__main__':
    main()
