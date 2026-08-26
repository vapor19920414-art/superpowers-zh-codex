#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只读检查 mower-tb-triage 的本机运行环境，不访问 Teambition。"""

import importlib
import json
import os
import re
import stat
import sys


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_ENV = "MOWER_TB_CONFIG"
HOSTNAME_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
    r"(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\Z"
)


def valid_hostname(value):
    return isinstance(value, str) and bool(HOSTNAME_RE.fullmatch(value.strip().lower()))


def resolve_path(path, base=SKILL_DIR):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.abspath(path)


def find_config():
    paths = []
    if os.environ.get(CONFIG_ENV):
        paths.append(os.path.expanduser(os.environ[CONFIG_ENV]))
    paths.extend((os.path.join(SKILL_DIR, "config.json"),
                  os.path.join(SKILL_DIR, "config.example.json")))
    for path in paths:
        if os.path.isfile(path):
            return path
    return None


def nearest_existing_parent(path):
    current = os.path.abspath(path)
    while not os.path.lexists(current):
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return current


def main():
    failures = 0
    warnings = 0

    def report(level, message):
        nonlocal failures, warnings
        if level == "FAIL":
            failures += 1
        elif level == "WARN":
            warnings += 1
        print(f"[{level}] {message}")

    if sys.version_info >= (3, 10):
        report("PASS", f"Python {sys.version.split()[0]}")
    else:
        report("FAIL", f"需要 Python >= 3.10，当前 {sys.version.split()[0]}")

    for module in ("requests", "cryptography", "secretstorage"):
        try:
            importlib.import_module(module)
            report("PASS", f"依赖可导入：{module}")
        except Exception as exc:
            report("FAIL", f"依赖不可导入：{module}: {type(exc).__name__}: {exc}")

    if os.environ.get("PYTHONPATH"):
        report("WARN", "检测到外部 PYTHONPATH；建议按文档使用 env -u PYTHONPATH 运行")
    else:
        report("PASS", "未继承外部 PYTHONPATH")

    config_path = find_config()
    if not config_path:
        report("FAIL", f"找不到配置：{SKILL_DIR}/config.json")
        print(f"\n[SUMMARY] failures={failures} warnings={warnings}")
        return 1

    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
        report("PASS", f"配置可解析：{config_path}")
    except (OSError, ValueError) as exc:
        report("FAIL", f"配置不可解析：{type(exc).__name__}: {exc}")
        print(f"\n[SUMMARY] failures={failures} warnings={warnings}")
        return 1

    domain = str(cfg.get("domain", "")).strip()
    if valid_hostname(domain):
        report("PASS", f"TB 域名：{domain}")
    else:
        report("FAIL", "domain 为空或格式不合法")

    attachment_hosts = cfg.get("attachment_hosts", [])
    if (isinstance(attachment_hosts, list) and
            all(valid_hostname(host) for host in attachment_hosts)):
        report("PASS", "附件主机白名单格式合法")
    else:
        report("FAIL", "attachment_hosts 必须是合法主机名数组")

    projects = cfg.get("projects", {})
    for lib, project in projects.items():
        pid = str((project or {}).get("pid", "")).strip()
        if pid and not pid.startswith("REPLACE_WITH_"):
            report("PASS", f"{lib} project ID 已配置")
        else:
            report("FAIL", f"{lib} project ID 未配置")

    chrome_base = resolve_path(cfg.get("chrome_base", "~/.config/google-chrome"))
    profile = str(cfg.get("chrome_profile", "Default")).strip()
    cookie_db = os.path.join(chrome_base, profile, "Cookies")
    if os.path.isfile(cookie_db):
        report("PASS", f"Chrome cookie DB：{cookie_db}")
    else:
        report("FAIL", f"Chrome cookie DB 不存在：{cookie_db}")

    if os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        report("PASS", "桌面 keyring DBus 会话可见")
    else:
        report("WARN", "DBUS_SESSION_BUS_ADDRESS 不存在，secretstorage 可能回退失败")

    cookie_path = resolve_path(cfg.get(
        "cookie_file", "~/.local/state/mower-tb-triage/tb.cookie"))
    if os.path.lexists(cookie_path):
        info = os.lstat(cookie_path)
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISLNK(info.st_mode):
            report("FAIL", f"cookie 禁止使用软链：{cookie_path}")
        elif not stat.S_ISREG(info.st_mode):
            report("FAIL", f"cookie 路径不是普通文件：{cookie_path}")
        elif info.st_uid != os.getuid():
            report("FAIL", f"cookie 文件所有者不是当前用户：{cookie_path}")
        elif mode != 0o600:
            report("FAIL", f"cookie 权限必须为 0600，当前 {mode:04o}：{cookie_path}")
        else:
            report("PASS", f"cookie 已生成且权限为 0600：{cookie_path}")
    else:
        parent = nearest_existing_parent(os.path.dirname(cookie_path))
        if os.path.isdir(parent) and os.access(parent, os.W_OK | os.X_OK):
            report("WARN", f"cookie 尚未生成；父目录可写：{cookie_path}")
        else:
            report("FAIL", f"cookie 尚未生成且父目录不可写：{cookie_path}")

    log_root = resolve_path(cfg.get("log_root", "~/work/log/mower-tb-triage"))
    if os.path.lexists(log_root):
        if os.path.isdir(log_root) and os.access(log_root, os.W_OK | os.X_OK):
            report("PASS", f"日志目录可写：{log_root}")
        else:
            report("FAIL", f"日志根路径不是可写目录：{log_root}")
    else:
        log_parent = nearest_existing_parent(log_root)
        if os.path.isdir(log_parent) and os.access(log_parent, os.W_OK | os.X_OK):
            report("PASS", f"日志目录可创建：{log_root}")
        else:
            report("FAIL", f"日志目录父路径不是可写目录：{log_parent}")

    debug_candidates = (
        os.path.expanduser("~/.codex/skills/systematic-debugging/SKILL.md"),
        os.path.expanduser("~/.claude/skills/systematic-debugging/SKILL.md"),
    )
    found = next((path for path in debug_candidates if os.path.isfile(path)), None)
    if found:
        report("PASS", f"systematic-debugging 可用：{found}")
    else:
        report("FAIL", "未发现 systematic-debugging skill")

    print(f"\n[SUMMARY] failures={failures} warnings={warnings}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
