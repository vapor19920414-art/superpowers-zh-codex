#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TB「版本」对象发现与登记工具。

TB 的「版本」是 lookup 自定义字段（objectType=teambition.version），
没有公开的“列版本”API；但项目任务列表接口返回的 customfields value 里
带 title（版本号）与 meta.repositoryId，因此可以从项目已有任务反查
“已用过的版本 label→id”，并把新版本登记到 config.json，省去手工查 id。

子命令：
  list                列出项目任务里出现过的所有版本（标注是否已登记）
  register <label>    把某个版本号登记到 config.json（已存在且 id 不同需 --force 覆盖）
  sync                把项目里出现过的全部版本一次性登记到 config.json

用法示例：
  python3 scripts/tb_version.py list
  python3 scripts/tb_version.py list --json
  python3 scripts/tb_version.py register v0.0.8
  python3 scripts/tb_version.py sync
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tb_pull as tp  # noqa: E402

VERSION_FIELD_KEY = "version"
TASK_BATCH = 300  # 列表接口单批上限；达到上限时提示可能不全


def config_path(cfg):
    """返回实际生效的配置文件路径（与 load_config 相同优先级）。"""
    for rel in ("../config.json", "../config.example.json"):
        p = os.path.join(HERE, rel)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, "../config.json")


def discover_versions(cfg, s):
    """扫描项目任务，返回 {label: {"id", "description", "repository_id"}}。

    label 取任务 customfields 版本字段 value 的 title；title 缺失的条目
    无法映射版本号，按原始 id 记录到 _by_id，不进入返回 dict。
    """
    pid = cfg["project"]["pid"]
    ver_cf = cfg["customfields"][VERSION_FIELD_KEY]["id"]
    found = {}
    by_id = {}
    for is_done in (False, True):
        r = s.get(tp.base_url(cfg) + f"/api/projects/{pid}/tasks",
                  params={"isDone": str(is_done).lower(), "count": TASK_BATCH}, timeout=30)
        r.raise_for_status()
        payload = r.json()
        tasks = payload if isinstance(payload, list) else payload.get("result", payload.get("data", []))
        if len(tasks) >= TASK_BATCH:
            print(f"[warn] 单批任务达到 {TASK_BATCH} 上限（isDone={str(is_done).lower()}），"
                  f"版本清单可能不全。", file=sys.stderr)
        for t in tasks:
            for f in t.get("customfields") or []:
                if f.get("_customfieldId") != ver_cf:
                    continue
                for v in f.get("value") or []:
                    vid = v.get("_id")
                    if not vid:
                        continue
                    title = v.get("title")
                    if not title:
                        by_id.setdefault(vid, None)
                        continue
                    info = found.setdefault(title, {
                        "id": vid, "description": "", "repository_id": None})
                    if not info["description"]:
                        info["description"] = (v.get("description") or "")[:80]
                    if info["repository_id"] is None:
                        meta = v.get("meta") or {}
                        info["repository_id"] = meta.get("repositoryId")
    if by_id:
        print(f"[warn] {len(by_id)} 个版本值缺少 title，无法映射版本号（只能按 id 使用）。",
              file=sys.stderr)
    return found


def load_config_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_config_json(path, data):
    """原子写回 config.json，保留原文件权限。"""
    mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(prefix=".config-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
        os.chmod(path, mode)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def register_version_choice(cfg, label, vid, force=False):
    """把 label→id 写入 config.json 的 customfields.version.choices。

    返回 (ok, message)：ok=True 表示已写入；False 表示因冲突跳过（需 --force）。
    """
    path = config_path(cfg)
    data = load_config_json(path)
    choices = data["customfields"][VERSION_FIELD_KEY].setdefault("choices", {})
    old = choices.get(label)
    if old and old != vid and not force:
        return False, f"版本 {label} 已登记为 {old}，与发现值 {vid} 不一致；用 --force 覆盖"
    choices[label] = vid
    save_config_json(path, data)
    if old and old != vid:
        return True, f"版本 {label}: {old} -> {vid}（覆盖）"
    if old:
        return True, f"版本 {label} 已是 {vid}（无变化）"
    return True, f"版本 {label} -> {vid}"


def main():
    ap = argparse.ArgumentParser(
        description="TB 版本对象发现与登记：从项目任务反查已用版本并登记到 config.json")
    ap.add_argument("command", choices=("list", "register", "sync"))
    ap.add_argument("label", nargs="?", help="register 用的版本号，如 v0.0.8")
    ap.add_argument("--json", action="store_true", help="list 时输出 JSON")
    ap.add_argument("--force", action="store_true", help="register/sync 时覆盖已登记的不同 id")
    args = ap.parse_args()

    cfg = tp.load_config()
    s = tp.session(cfg)
    found = discover_versions(cfg, s)
    registered = (cfg.get("customfields", {}).get(VERSION_FIELD_KEY, {}).get("choices") or {})

    if args.command == "list":
        rows = []
        for label in sorted(found, key=str.lower):
            info = found[label]
            reg = registered.get(label)
            rows.append({
                "label": label, "id": info["id"], "description": info["description"],
                "repository_id": info["repository_id"],
                "registered": bool(reg), "registered_id": reg,
            })
        if args.json:
            json.dump(rows, sys.stdout, ensure_ascii=False, indent=2)
            print()
            return
        print(f"=== 项目已用版本（{len(rows)} 个）===")
        for r in rows:
            mark = "已登记" if r["registered"] else "未登记"
            print(f"  {r['label']:<10} {r['id']}  [{mark}]  {r['description']}")
        print("\n提示：tb_version.py register <版本号> 登记未登记版本；tb_version.py sync 全量登记。")
        return

    if args.command == "register":
        if not args.label:
            raise SystemExit("[error] register 需要 <label>，例如：tb_version.py register v0.0.8")
        if args.label not in found:
            avail = "、".join(sorted(found, key=str.lower)) or "（项目任务里未发现任何版本）"
            raise SystemExit(f"[error] 项目任务里没有版本 '{args.label}'。已发现：{avail}")
        ok, msg = register_version_choice(cfg, args.label, found[args.label]["id"], force=args.force)
        print(("[ok] " if ok else "[skip] ") + msg)
        return

    # sync
    added = 0
    for label in sorted(found, key=str.lower):
        ok, msg = register_version_choice(cfg, label, found[label]["id"], force=args.force)
        if ok:
            print(f"[ok] {msg}")
            added += 1
        else:
            print(f"[skip] {msg}")
    print(f"sync 完成：登记/更新 {added} 个版本（共发现 {len(found)} 个）。")


if __name__ == "__main__":
    main()
