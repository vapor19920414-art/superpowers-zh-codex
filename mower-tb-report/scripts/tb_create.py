#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在 TB「LXLT 缺陷库」创建缺陷：自动归入【缺陷】场景并填必填字段 + 可选挂日志附件。

为什么必须用本脚本（两个最容易踩的坑）：
  1. /bug/section/all 缺陷视图只展示【缺陷】场景（scenariofieldconfigId=…47ee）的任务；
     建在【任务】场景（…47e1）在缺陷视图里永远看不到。而场景在创建后无法通过更新接口
     修改（PUT 会忽略 _scenariofieldconfigId），只能删掉重建 —— 所以创建时必须选对。
  2. 【缺陷】场景有 6 个必填自定义字段（版本/测试人员/严重等级/缺陷模块/缺陷分类/设备序列号），
     漏填会导致缺陷不完整、视图里展示异常。

用法示例：
  # 1) 先看将创建什么（不真正创建）
  python3 scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
      --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
      --version v0.0.2 --time "2026-08-23 16:53" --dry-run

  # 2) 真正创建 + 挂日志附件（--attach 可多次）
  python3 scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
      --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
      --version v0.0.2 --time "2026-08-23 16:53" --severity Normal --module 业务软件 \
      --attach device_logs.tgz --attach 现场图.png

  # 描述直接给文本（不写文件）
  python3 scripts/tb_create.py --title "xxx" --desc-text "【现象】…" --receipt xxx.receipt.json \
      --device … --firmware … --version v0.0.2

  # 自定义测试人员/版本（支持名字；版本限 config 里登记的选项）
  python3 scripts/tb_create.py … --tester 佛印 --version v0.0.2

  # 附件失败后，只续传，不会重复创建任务
  python3 scripts/tb_create.py <原参数> --resume-attachments

  # SshFileDownloader 本地日志目录：自动上传关键日志包和完整 userdata.zip
  python3 scripts/tb_create.py <原参数> --log-dir /path/to/20260831_190603

  # 只想要直链/任务 id（不挂附件）
  python3 scripts/tb_create.py … 2>&1 | tail -3
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tb_pull as tp  # noqa: E402


def load_config():
    return tp.load_config()


def get_choice(cf_key, value, cfg):
    """把用户给的选项名解析为选项 id；查不到则报错列出可用选项。"""
    cf = cfg["customfields"][cf_key]
    choices = cf.get("choices") or {}
    if value in choices:
        return choices[value], value
    # 允许直接传 id
    if value in choices.values():
        return value, value
    raise SystemExit(
        f"[error] {cf.get('name', cf_key)} 没有选项 '{value}'。可用：{', '.join(choices)}"
    )


def resolve_tester(name, cfg, s):
    """按名字解析成员 _userId（测试人员字段取值）。支持直接传 _userId。"""
    pid = cfg["project"]["pid"]
    r = s.get(tp.base_url(cfg) + f"/api/projects/{pid}/members", timeout=15)
    r.raise_for_status()
    members = r.json()
    if not isinstance(members, list):
        members = members.get("result", members.get("data", []))
    for m in members:
        if m.get("name") == name or m.get("_userId") == name:
            return m["_userId"]
    hits = [m for m in members if name and name in (m.get("name") or "")]
    if len(hits) == 1:
        return hits[0]["_userId"]
    if len(hits) > 1:
        raise SystemExit(f"[error] 测试人员 '{name}' 匹配到多人，请用 _userId 指定。")
    raise SystemExit(
        f"[error] 找不到成员 '{name}'。可用成员示例：{', '.join(m.get('name', '?') for m in members[:8])}…"
    )


# 描述中必须出现的小节；缺任一即拒绝创建。
# 【复现步骤】是开发复现问题的最重要输入，务必写全（前置条件/操作/触发点/复现概率/预期vs实际）。
REQUIRED_SECTIONS = ("【现象】", "【复现步骤】", "【设备信息】")
RECEIPT_SCHEMA = 1
ATTACHMENT_POLICY = "key_and_userdata_v1"


def _json_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _expand_path(path):
    return os.path.abspath(os.path.expanduser(path))


def _create_userdata_zip(log_dir):
    """把 userdata/ 原子压缩到同级 userdata.zip，失败时不留下残包。"""
    target = os.path.join(log_dir, "userdata.zip")
    fd, tmp_base = tempfile.mkstemp(prefix=".userdata-", dir=log_dir)
    os.close(fd)
    os.remove(tmp_base)
    tmp_zip = tmp_base + ".zip"
    try:
        shutil.make_archive(tmp_base, "zip", root_dir=log_dir, base_dir="userdata")
        try:
            os.link(tmp_zip, target)
        except FileExistsError as e:
            raise RuntimeError(f"压缩期间 userdata.zip 已出现，拒绝覆盖：{target}") from e
        os.remove(tmp_zip)
    finally:
        for path in (tmp_base, tmp_zip):
            if os.path.exists(path):
                os.remove(path)
    print(f"[info] 已生成完整日志包：{target}")
    return target


def build_attachment_manifest(paths, log_dirs=(), prior_manifest=(), dry_run=False,
                              include_userdata=True):
    """返回可审计的附件清单；日志目录包含关键包和完整 userdata 包。"""
    out = []
    by_path = {}
    prior_by_path = {item.get("path"): item for item in prior_manifest}

    def add_file(path, cleanup_after_upload=False, recorded=None):
        absolute = _expand_path(path)
        if absolute in by_path:
            by_path[absolute]["cleanup_after_upload"] |= cleanup_after_upload
            return
        if recorded is None and not os.path.isfile(absolute):
            raise SystemExit(f"[error] 附件不存在或不是普通文件：{path}")
        if recorded is None:
            st = os.stat(absolute)
            item = {
                "path": absolute,
                "name": os.path.basename(absolute),
                "size": st.st_size,
                "mtime_ns": st.st_mtime_ns,
                "st_dev": st.st_dev,
                "st_ino": st.st_ino,
                "status": "pending",
            }
        else:
            item = dict(recorded)
        item["cleanup_after_upload"] = cleanup_after_upload
        out.append(item)
        by_path[absolute] = item

    for path in paths:
        add_file(path)
    for log_dir in log_dirs:
        absolute = _expand_path(log_dir)
        if not os.path.isdir(absolute):
            raise SystemExit(f"[error] --log-dir 不是目录：{log_dir}")
        with os.scandir(absolute) as entries:
            archives = sorted(
                entry.path for entry in entries
                if entry.is_file() and entry.name.lower().endswith((".tar.gz", ".tgz"))
            )
        if len(archives) != 1:
            names = "、".join(os.path.basename(path) for path in archives) or "无"
            raise SystemExit(
                f"[error] --log-dir 必须包含唯一的根目录 .tar.gz/.tgz 日志包：{log_dir}（当前：{names}）。\n"
                "        请先生成关键日志归档，或用 --attach 明确指定单个文件。"
            )
        if not include_userdata:
            print(f"[info] 旧收据沿用原附件策略：{os.path.basename(archives[0])}")
            add_file(archives[0])
            continue

        full_zip = os.path.join(absolute, "userdata.zip")
        userdata_dir = os.path.join(absolute, "userdata")
        prior = prior_by_path.get(full_zip)
        generated = bool(prior and prior.get("cleanup_after_upload"))
        if os.path.isfile(full_zip):
            pass
        elif generated:
            # 自动生成包在成功后会删除；复跑时沿用收据，避免再次压缩。
            pass
        elif prior:
            raise SystemExit(f"[error] 收据中的完整日志包已不存在：{full_zip}")
        elif not os.path.isdir(userdata_dir):
            raise SystemExit(f"[error] --log-dir 缺少 userdata.zip 或 userdata/：{log_dir}")
        elif dry_run:
            prior = {
                "path": full_zip,
                "name": "userdata.zip",
                "size": None,
                "mtime_ns": None,
                "status": "planned",
            }
            generated = True
        else:
            _create_userdata_zip(absolute)
            generated = True

        print(f"[info] 本地日志目录：{absolute} -> 关键包 {os.path.basename(archives[0])} + 完整包 userdata.zip")
        add_file(archives[0])
        add_file(full_zip, cleanup_after_upload=generated,
                 recorded=prior if generated else None)
    return out


def verify_generated_archive_identity(entry):
    """自动包被替换或修改后拒绝上传、拒绝删除。"""
    path = entry["path"]
    if os.path.basename(path) != "userdata.zip":
        raise RuntimeError(f"自动清理目标不是 userdata.zip：{path}")
    if not os.path.isfile(path) or os.path.islink(path):
        raise RuntimeError(f"自动生成的完整日志包不存在或类型已变化：{path}")
    st = os.stat(path, follow_symlinks=False)
    expected = tuple(entry.get(key) for key in ("st_dev", "st_ino", "size", "mtime_ns"))
    actual = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
    if None in expected or actual != expected:
        raise RuntimeError(f"自动生成的完整日志包身份已变化，拒绝操作：{path}")


def cleanup_generated_archives(manifest):
    """仅删除本次流程自动生成且已上传确认的 userdata.zip。"""
    for entry in manifest:
        if not entry.get("cleanup_after_upload"):
            continue
        path = entry["path"]
        if os.path.exists(path):
            verify_generated_archive_identity(entry)
            os.remove(path)
            print(f"[ok] 已删除自动生成的完整日志包：{path}")
        entry["cleanup_status"] = "removed"


def receipt_path_for(args):
    if args.receipt:
        return _expand_path(args.receipt)
    if args.desc:
        return _expand_path(args.desc) + ".tb-receipt.json"
    return None


def load_receipt(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise SystemExit(f"[error] 收据不可读取：{path}（{type(e).__name__}）")
    if not isinstance(data, dict) or data.get("schema") != RECEIPT_SCHEMA:
        raise SystemExit(f"[error] 收据格式不支持：{path}")
    return data


def write_receipt(path, data):
    """0600 原子落盘，避免创建成功但附件失败时丢失 task id。"""
    parent = os.path.dirname(path) or "."
    os.makedirs(parent, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tb-receipt-", dir=parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    os.chmod(path, 0o600)


def task_identity(task, cfg):
    project = cfg["project"]
    tid = task["_id"]
    uid = task.get("uniqueId")
    label = f"{project.get('uniqueIdPrefix', 'LXLT')}-{uid}" if uid else tid
    return {
        "id": tid,
        "label": label,
        "url": f"https://{cfg['domain']}/project/{project['pid']}/task/{tid}",
    }


def safe_error_label(exc):
    """收据只记录错误类型，避免把响应体、URL token 写入本地。"""
    return type(exc).__name__


def _section_body(note, sec):
    """取某小节标题后的正文（到下一小节标题或结尾）。"""
    import re
    m = re.search(re.escape(sec) + r"\s*\n(.*?)(?=\n【|\Z)", note, re.S)
    return m.group(1).strip() if m else ""


def build_note(desc_text, args):
    note = (desc_text or "").strip()
    if not note and not (args.device and args.firmware):
        raise SystemExit("[error] 需要 --desc/--desc-text，或至少提供 --device + --firmware（生成设备信息段）")
    # 若缺设备信息段但提供了 device/firmware，自动补
    if args.device and "【设备信息】" not in note:
        seg = "【设备信息】\n"
        seg += f"- 机器: {args.device}\n"
        if args.firmware:
            seg += f"- 固件: {args.firmware}\n"
        if args.time:
            seg += f"- 发生时间: {args.time}\n"
        note = (note + "\n\n" + seg).strip() if note else seg.strip()
    # 硬性必填校验（复现步骤尤其重要）
    missing = [s for s in REQUIRED_SECTIONS if s not in note]
    if missing:
        raise SystemExit(
            f"[error] 描述缺少必填小节：{'、'.join(missing)}。\n"
            f"        复现步骤必须写全（前置条件/操作步骤/触发点/复现概率/预期vs实际），"
            f"请参考 templates/问题描述模板.md 补全后重试。"
        )
    if not _section_body(note, "【复现步骤】"):
        raise SystemExit(
            "[error] 【复现步骤】为空：请写清前置条件、一步一步的操作（点到按钮/菜单路径/参数）、"
            "触发点、复现概率、预期vs实际，参考 templates/问题描述模板.md。"
        )
    if not _section_body(note, "【现象】"):
        raise SystemExit("[error] 【现象】为空：请一句话说清发生了什么、用户感知是什么。")
    return note


def apply_defaults_and_validate_versions(args, cfg):
    """现场 firmware 与 TB 自定义字段 version 是两个维度，禁止静默混用。"""
    dft = cfg.get("defaults", {})
    version_argument = args.version
    args.severity = args.severity or dft.get("severity", "Normal")
    args.module = args.module or dft.get("module", "业务软件")
    args.category = args.category or dft.get("category", "算法")
    args.type = args.type or dft.get("type", "功能")
    args.version = args.version or dft.get("version", "v0.0.2")
    args.tester = args.tester or dft.get("tester", "佛印")

    if not args.firmware:
        args.version_mapping = "not_applicable"
        return

    if not args.version_explicit or not version_argument:
        raise SystemExit(
            "[error] 已提供 --firmware（现场固件），必须显式提供 --version/--tb-version（TB 自定义字段版本）。\n"
            "        两者可以不同，但不得由 defaults.version 静默推断。"
        )

    expected = (cfg.get("firmware_tb_version_map") or {}).get(args.firmware)
    if expected and args.version != expected:
        raise SystemExit(
            f"[error] 固件 {args.firmware} 在 firmware_tb_version_map 中应对应 TB 版本 {expected}，"
            f"但命令给了 {args.version}。"
        )
    if expected:
        args.version_mapping = "config_mapped"
        print(f"[info] 版本映射已校验：现场固件 {args.firmware} -> TB 版本 {args.version}")
    else:
        args.version_mapping = "explicit_unmapped"
        print(
            f"[warn] 未配置现场固件 {args.firmware} 的 TB 版本映射；"
            f"按显式参数使用 TB 版本 {args.version}。"
        )


def build_customfields(args, cfg, s):
    out = []
    # 版本（lookup teambition.version）
    ver_id, _ = get_choice("version", args.version, cfg)
    out.append({"_customfieldId": cfg["customfields"]["version"]["id"], "type": "lookup",
                "objectType": "teambition.version", "value": [{"_id": ver_id}]})
    # 测试人员（lookup teambition.member）
    tester_id = resolve_tester(args.tester, cfg, s)
    out.append({"_customfieldId": cfg["customfields"]["tester"]["id"], "type": "lookup",
                "objectType": "teambition.member", "value": [{"_id": tester_id}]})
    # 严重等级（dropDown）
    sev_id, _ = get_choice("severity", args.severity, cfg)
    out.append({"_customfieldId": cfg["customfields"]["severity"]["id"], "type": "dropDown",
                "value": [{"_id": sev_id}]})
    # 缺陷模块（dropDown）
    mod_id, _ = get_choice("module", args.module, cfg)
    out.append({"_customfieldId": cfg["customfields"]["module"]["id"], "type": "dropDown",
                "value": [{"_id": mod_id}]})
    # 缺陷分类（commongroup）
    cat_id, _ = get_choice("category", args.category, cfg)
    out.append({"_customfieldId": cfg["customfields"]["category"]["id"], "type": "commongroup",
                "value": [{"_id": cat_id}]})
    # 设备序列号（text）
    if not args.device:
        raise SystemExit("[error] 缺少 --device（设备序列号是必填自定义字段）")
    out.append({"_customfieldId": cfg["customfields"]["serial"]["id"], "type": "text",
                "value": [{"title": args.device}]})
    # 缺陷类型（dropDown，可选但建议填）
    if args.type:
        typ_id, _ = get_choice("type", args.type, cfg)
        out.append({"_customfieldId": cfg["customfields"]["type"]["id"], "type": "dropDown",
                    "value": [{"_id": typ_id}]})
    return out


def build_task_body(args, cfg, note, customfields):
    p = cfg["project"]
    return {
        "content": args.title,
        "note": note,
        "_projectId": p["pid"],
        "_tasklistId": p["tasklistId"],
        "_stageId": p["stageId"],
        "_scenariofieldconfigId": p["scenario_defect"],  # 必须是【缺陷】场景
        "customfields": customfields,
    }


def create_task(cfg, s, body):
    p = cfg["project"]
    r = s.post(tp.base_url(cfg) + "/api/v2/tasks", json=body, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"创建失败 {r.status_code}: {r.text[:300]}")
    d = r.json()
    identity = task_identity(d, cfg)
    print(f"[ok] 已创建 {identity['label']}：{d.get('content')}")
    print(f"[ok] 直链: {identity['url']}")
    print(f"[ok] 缺陷视图应可见: https://{cfg['domain']}/project/{p['pid']}/bug/section/all")
    return d


def fetch_task_detail(s, cfg, tid):
    data = tp.api_get(s, cfg, f"/api/v2/tasks/{tid}")
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    if not isinstance(data, dict):
        raise RuntimeError("任务详情返回格式异常")
    return data


def _canonical_customfield_value(field):
    values = []
    for value in field.get("value") or []:
        if "_id" in value:
            values.append(("id", str(value["_id"])))
        elif "title" in value:
            values.append(("title", str(value["title"])))
        else:
            values.append(("json", json.dumps(value, ensure_ascii=False, sort_keys=True)))
    return tuple(sorted(values))


def verify_task(s, cfg, tid, body):
    """创建后回读缺陷场景和所有请求的自定义字段。"""
    task = fetch_task_detail(s, cfg, tid)
    errors = []
    if task.get("_scenariofieldconfigId") != body["_scenariofieldconfigId"]:
        errors.append("缺陷场景不匹配")

    actual = {f.get("_customfieldId"): f for f in task.get("customfields") or []}
    for expected in body["customfields"]:
        field_id = expected["_customfieldId"]
        field = actual.get(field_id)
        if not field:
            errors.append(f"缺少自定义字段 {field_id}")
            continue
        if field.get("type") != expected.get("type") or \
                _canonical_customfield_value(field) != _canonical_customfield_value(expected):
            errors.append(f"自定义字段值不匹配 {field_id}")
    if errors:
        raise RuntimeError("创建后校验失败：" + "；".join(errors))
    print("[ok] 创建后校验：缺陷场景与自定义字段一致")
    return task


def _attachment_name(file_info):
    return tp.safe_filename(file_info.get("name"), file_info.get("ext"))


def find_missing_attachments(s, cfg, tid, manifest):
    files = tp.collect_files(tp.fetch_activities(s, cfg, tid))
    missing = []
    for entry in manifest:
        matched = False
        for remote in files:
            if _attachment_name(remote) != entry["name"]:
                continue
            remote_size = remote.get("size")
            try:
                size_matches = remote_size is None or int(remote_size) == entry["size"]
            except (TypeError, ValueError):
                size_matches = False
            if size_matches:
                matched = True
                break
        if matched:
            entry["status"] = "uploaded"
        else:
            entry["status"] = "pending"
            missing.append(entry)
    return missing


def attach_files(args, cfg, s, tid, manifest):
    """上传未挂载的附件并作为一条评论挂到任务。"""
    if not manifest:
        return None, []
    tokens = []
    for entry in manifest:
        if entry.get("cleanup_after_upload"):
            verify_generated_archive_identity(entry)
        token, fname, ftype, size = tp.upload_attachment(s, cfg, tid, entry["path"])
        tokens.append(token)
        print(f"  [upload] {fname}（{size:,} bytes, {ftype}）")
    text = args.comment or "补充现场日志/截图，供排查。问题描述与初步分析见问题详情。"
    act = tp.post_comment(s, cfg, tid, text, tokens)
    c = act.get("content", {})
    files = c.get("files", []) if isinstance(c, dict) else []
    print(f"[ok] 评论已发布（附件 {len(files)} 个）")
    return act.get("_id"), files


def adopt_task(args, cfg, s, body):
    """仅为 POST 结果不明的收据人工绑定已确认任务，绝不自动猜测。"""
    task, _ = tp.find_task(s, cfg, args.adopt_task, "LXLT", cfg["project"]["pid"])
    task = fetch_task_detail(s, cfg, task["_id"])
    if task.get("_projectId") != body["_projectId"] or task.get("content") != body["content"]:
        raise SystemExit("[error] --adopt-task 与本次项目或标题不一致，拒绝绑定。")
    verify_task(s, cfg, task["_id"], body)
    return task


def main():
    ap = argparse.ArgumentParser(description="在 TB LXLT 缺陷库创建缺陷（缺陷场景 + 必填字段 + 可选附件）")
    ap.add_argument("--title", required=True, help="缺陷标题，如【建图】xxx")
    ap.add_argument("--desc", help="问题描述 markdown 文件（推荐，见 templates/问题描述模板.md）")
    ap.add_argument("--desc-text", help="问题描述直接给文本（与 --desc 二选一）")
    ap.add_argument("--device", help="设备序列号（必填，缺陷必填字段）")
    ap.add_argument("--firmware", help="固件版本，如 V1.3.8_RN2601_DEV_20260819-1019")
    ap.add_argument("--time", help="发生时间，如 2026-08-23 16:53")
    ap.add_argument("--severity", default=None, help="严重等级：blocker/Critical/Major/Normal/Enhancement")
    ap.add_argument("--module", default=None, help="缺陷模块：硬件/结构/SOC固件/MCU/业务软件/APP/感知算法/定位算法/规控算法/RGB图像/深度图像")
    ap.add_argument("--category", default=None, help="缺陷分类（commongroup），默认 算法")
    ap.add_argument("--type", default=None, help="缺陷类型：功能/界面/兼容/安全/性能/建议/其他")
    ap.add_argument("--version", "--tb-version", dest="version", default=None,
                    help="TB 自定义字段版本；给 --firmware 时必须显式传入")
    ap.add_argument("--tester", default=None, help="测试人员（名字或 _userId，默认取 config.defaults.tester）")
    ap.add_argument("--attach", action="append", default=[], help="附件文件路径（可多次），上传后挂到一条评论")
    ap.add_argument("--log-dir", action="append", default=[],
                    help="本地日志目录（可多次）；自动上传唯一关键包和完整 userdata.zip")
    ap.add_argument("--comment", help="附件评论文字（默认模板文案）")
    ap.add_argument("--receipt", help="创建收据路径；省略时使用 <描述文件>.tb-receipt.json")
    ap.add_argument("--resume-attachments", action="store_true",
                    help="只继续已有收据中未挂成功的附件，绝不重新创建任务")
    ap.add_argument("--adopt-task",
                    help="POST 结果不明时，人工确认后绑定已有 LXLT-N 或 task id；须配合 --resume-attachments")
    ap.add_argument("--dry-run", action="store_true", help="只打印将创建的 body，不真正创建")
    args = ap.parse_args()
    args.version_explicit = any(
        value in ("--version", "--tb-version")
        or value.startswith(("--version=", "--tb-version="))
        for value in sys.argv[1:]
    )

    if args.desc and args.desc_text:
        raise SystemExit("[error] --desc 与 --desc-text 只能二选一")
    desc_text = ""
    if args.desc:
        with open(args.desc, encoding="utf-8") as f:
            desc_text = f.read()
    elif args.desc_text:
        desc_text = args.desc_text

    if args.adopt_task and not args.resume_attachments:
        raise SystemExit("[error] --adopt-task 只能与 --resume-attachments 一起使用。")

    cfg = load_config()
    apply_defaults_and_validate_versions(args, cfg)
    s = tp.session(cfg)

    note = build_note(desc_text, args)
    customfields = build_customfields(args, cfg, s)
    body = build_task_body(args, cfg, note, customfields)
    path = receipt_path_for(args)
    if not args.dry_run and not path:
        raise SystemExit("[error] 使用 --desc-text 真创建时必须额外给 --receipt，避免丢失创建收据。")
    receipt = load_receipt(path) if path else None
    legacy_receipt = bool(receipt and not receipt.get("attachment_policy"))
    manifest = build_attachment_manifest(
        args.attach,
        args.log_dir,
        prior_manifest=(receipt or {}).get("attachments", ()),
        dry_run=args.dry_run,
        include_userdata=not legacy_receipt,
    )

    if args.dry_run:
        print("=== DRY RUN：将创建以下任务（未真正创建）===")
        print(json.dumps(body, ensure_ascii=False, indent=2))
        print(f"[info] 现场固件={args.firmware or '未提供'}；TB 版本={args.version}；"
              f"映射状态={args.version_mapping}")
        if manifest:
            print("[info] 将挂附件：" + "、".join(item["name"] for item in manifest))
        return

    fingerprint = _json_hash({
        "body": body,
        "attachments": [
            {key: item[key] for key in ("path", "name", "size", "mtime_ns")}
            for item in manifest
        ],
        "comment": args.comment or "",
    })
    if receipt:
        if receipt.get("request_fingerprint") != fingerprint:
            raise SystemExit("[error] 收据与当前标题/字段/附件不一致；为避免重复建单已停止。")
        if args.adopt_task:
            if receipt.get("task"):
                raise SystemExit("[error] 收据已有 task，不能再 --adopt-task。")
            task = adopt_task(args, cfg, s, body)
            receipt["task"] = task_identity(task, cfg)
            receipt["state"] = "created"
            receipt.pop("last_error", None)
            write_receipt(path, receipt)
        task_info = receipt.get("task")
        if not task_info:
            raise SystemExit(
                "[error] 上次 POST 结果不明，收据未记录 task；为避免重复建单不会重试创建。\n"
                "        请先在 TB 确认是否已建单，再用 --adopt-task LXLT-N --resume-attachments 绑定。"
            )
        if not args.resume_attachments:
            print(f"[info] 已有收据：{task_info['label']}，状态={receipt.get('state')}；未重新创建。")
            print("[info] 若需继续附件，显式加 --resume-attachments。")
            return
        manifest = receipt.get("attachments", manifest)
        tid = task_info["id"]
        print(f"[info] 继续已有任务 {task_info['label']} 的附件，绝不重新 POST。")
    else:
        if args.resume_attachments or args.adopt_task:
            raise SystemExit("[error] 未找到收据，不能使用 --resume-attachments/--adopt-task。")
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "attachment_policy": ATTACHMENT_POLICY,
            "request_fingerprint": fingerprint,
            "request": {
                "title": args.title,
                "firmware": args.firmware,
                "tb_version": args.version,
                "version_mapping": args.version_mapping,
            },
            "attachments": manifest,
            "state": "create_started",
        }
        write_receipt(path, receipt)
        try:
            task = create_task(cfg, s, body)
        except Exception as e:
            receipt["state"] = "create_unknown"
            receipt["last_error"] = safe_error_label(e)
            write_receipt(path, receipt)
            raise
        receipt["task"] = task_identity(task, cfg)
        receipt["state"] = "created"
        write_receipt(path, receipt)
        tid = task["_id"]

    try:
        verify_task(s, cfg, tid, body)
    except Exception as e:
        receipt["state"] = "verification_failed"
        receipt["last_error"] = safe_error_label(e)
        write_receipt(path, receipt)
        raise

    if not manifest:
        receipt["state"] = "complete"
        receipt.pop("last_error", None)
        write_receipt(path, receipt)
        print(f"[ok] 已完成，收据：{path}")
        return

    try:
        missing = find_missing_attachments(s, cfg, tid, manifest)
        if missing:
            comment_id, _ = attach_files(args, cfg, s, tid, missing)
            if comment_id:
                receipt["attachment_comment_id"] = comment_id
        remaining = find_missing_attachments(s, cfg, tid, manifest)
        if remaining:
            raise RuntimeError("附件回读后仍未全部可见")
    except Exception as e:
        receipt["state"] = "attachments_pending"
        receipt["last_error"] = safe_error_label(e)
        write_receipt(path, receipt)
        raise RuntimeError(f"附件未完成；已保留收据 {path}，请确认后用 --resume-attachments 继续。") from e

    write_receipt(path, receipt)
    try:
        cleanup_generated_archives(manifest)
    except Exception as e:
        receipt["state"] = "cleanup_pending"
        receipt["last_error"] = safe_error_label(e)
        write_receipt(path, receipt)
        raise RuntimeError(f"附件已上传，但自动生成的 userdata.zip 清理失败；收据：{path}") from e

    receipt["state"] = "complete"
    receipt.pop("last_error", None)
    write_receipt(path, receipt)
    print(f"[ok] 已完成，收据：{path}")


if __name__ == "__main__":
    main()
