#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Teambition（tb.orbbec.com）拉割草机缺陷：列缺陷 / 拉单个缺陷的详情+真实评论+下载非视频附件。

子命令：
  list    列缺陷（uniqueId / 标题 / 附件数 / 状态 / 更新时间）
  defect  拉指定缺陷：拉 activities 拿真实评论 + 附件，默认只下载非视频附件，按 项目名/前缀-编号 保存

依赖：requests。cookie 由 tb_cookie.py 生成。

用法示例：
  python3 tb_pull.py --lib DLT list
  python3 tb_pull.py --lib DLT list --json
  python3 tb_pull.py defect DLT-29
  python3 tb_pull.py defect DLT-29 --include-video  # 仅在用户明确确认后使用
  python3 tb_pull.py defect DMT-292 --out ~/work/log/mower-tb-triage
"""
import argparse
import json
import os
import re
import stat
import sys
import tempfile
from urllib.parse import urljoin, urlsplit

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_ENV = "MOWER_TB_CONFIG"
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
VIDEO_EXTENSIONS = {
    "3g2", "3gp", "avi", "flv", "m2ts", "m4v", "mkv", "mov", "mp4",
    "mpeg", "mpg", "mts", "ogv", "vob", "webm", "wmv",
}
HOSTNAME_RE = re.compile(
    r"(?=.{1,253}\Z)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)"
    r"(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\Z"
)


def load_config():
    paths = []
    if os.environ.get(CONFIG_ENV):
        paths.append(os.path.expanduser(os.environ[CONFIG_ENV]))
    paths.extend((os.path.join(SKILL_DIR, "config.json"),
                  os.path.join(SKILL_DIR, "config.example.json")))
    for p in paths:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    return {}


def resolve_path(path, base=SKILL_DIR):
    path = os.path.expanduser(path)
    if not os.path.isabs(path):
        path = os.path.join(base, path)
    return os.path.abspath(path)


def cookie_file(cfg):
    return resolve_path(cfg.get(
        "cookie_file", "~/.local/state/mower-tb-triage/tb.cookie"))


def session(cfg):
    cp = cookie_file(cfg)
    if not os.path.lexists(cp):
        print(f"[error] cookie 不存在：{cp}\n        先跑：python3 {os.path.join(SCRIPT_DIR, 'tb_cookie.py')}", file=sys.stderr)
        sys.exit(1)

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = None
    try:
        fd = os.open(cp, flags)
        info = os.fstat(fd)
        mode = stat.S_IMODE(info.st_mode)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError("cookie 路径不是普通文件")
        if info.st_uid != os.getuid():
            raise ValueError("cookie 文件所有者不是当前用户")
        if mode != 0o600:
            raise ValueError(f"cookie 权限必须为 0600，当前 {mode:04o}")
        with os.fdopen(fd, encoding="utf-8") as f:
            fd = None
            cookie = f.read().strip()
    except (OSError, ValueError) as exc:
        print(f"[error] cookie 文件不安全：{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        if fd is not None:
            os.close(fd)

    if not cookie:
        print(f"[error] cookie 文件为空：{cp}", file=sys.stderr)
        sys.exit(1)

    s = requests.Session()
    # 不放入 Cookie Jar，避免 requests 的 domain cookie 自动覆盖子域。
    # 仅 api_get 对 config.domain 的单次请求显式注入；附件请求永不携带。
    s._tb_cookie_header = cookie
    return s


def resolve_pid(cfg, lib, pid):
    if pid:
        return pid
    proj = cfg.get("projects", {})
    if lib in proj:
        value = str(proj[lib].get("pid", "")).strip()
        if value and not value.startswith("REPLACE_WITH_"):
            return value
        print(f"[error] {lib} 的 project ID 尚未配置，请填写 config.json", file=sys.stderr)
        sys.exit(1)
    print(f"[error] 未知库 '{lib}'，可用：{list(proj.keys())}（或用 --pid 指定）", file=sys.stderr)
    sys.exit(1)


def normalize_hostname(value, field):
    if not isinstance(value, str):
        raise ValueError(f"{field} 必须是主机名字符串")
    host = str(value).strip().lower()
    if not HOSTNAME_RE.fullmatch(host):
        raise ValueError(f"{field} 含非法主机名：{host!r}")
    return host


def base_url(cfg):
    return "https://" + normalize_hostname(
        cfg.get("domain", "tb.orbbec.com"), "domain")


def api_get(s, cfg, path, **params):
    if not path.startswith("/"):
        print("[error] TB API path 必须以 / 开头", file=sys.stderr)
        sys.exit(1)
    try:
        url = base_url(cfg) + path
        r = s.get(url, params=params, timeout=30,
                  allow_redirects=False,
                  headers={"Cookie": s._tb_cookie_header})
    except (requests.RequestException, ValueError) as e:
        print(f"[error] TB 请求失败：{type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(1)
    if r.status_code in REDIRECT_STATUSES:
        print(f"[error] TB API 返回未授权重定向 HTTP {r.status_code}，已拒绝跟随", file=sys.stderr)
        sys.exit(1)
    if r.status_code == 401:
        print("[error] 401 鉴权失败——cookie 过期，请重跑 tb_cookie.py", file=sys.stderr)
        sys.exit(1)
    try:
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        print(f"[error] TB 返回 HTTP {r.status_code}：{e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"[error] TB 返回内容不是有效 JSON：{e}", file=sys.stderr)
        sys.exit(1)


def fetch_tasks(s, cfg, pid, status="open"):
    params = {"count": 300}
    if status == "open":
        params["isDone"] = "false"
    elif status == "done":
        params["isDone"] = "true"
    data = api_get(s, cfg, f"/api/projects/{pid}/tasks", **params)
    # 实测：该端点直接返回 list
    return data if isinstance(data, list) else data.get("result", data.get("data", []))


def fetch_activities(s, cfg, tid, count=100):
    data = api_get(s, cfg, f"/api/v2/tasks/{tid}/activities", count=count)
    return data.get("result", data) if isinstance(data, dict) else data


def fetch_project(s, cfg, pid):
    """读取项目名称和缺陷编号前缀，用于生成稳定且无冲突的本地目录。"""
    data = api_get(s, cfg, f"/api/projects/{pid}")
    if isinstance(data, dict) and isinstance(data.get("result"), dict):
        return data["result"]
    return data if isinstance(data, dict) else {}


def project_identity(cfg, project, lib, pid):
    """API 元数据优先，配置项回退，返回 (项目名, 缺陷前缀)。"""
    projects = cfg.get("projects", {})
    entry = projects.get(lib, {}) if lib else {}
    if not entry:
        for code, candidate in projects.items():
            if str(candidate.get("pid", "")).strip() == str(pid):
                lib, entry = code, candidate
                break

    name = str(project.get("name") or entry.get("label") or lib or pid).strip()
    prefix = str(
        project.get("uniqueIdPrefix") or entry.get("prefix") or lib or ""
    ).strip().upper()
    return name, prefix


# ---------- list ----------

def cmd_list(args):
    cfg = load_config()
    s = session(cfg)
    pid = resolve_pid(cfg, args.lib, args.pid)
    project = fetch_project(s, cfg, pid)
    project_name, prefix = project_identity(cfg, project, args.lib, pid)
    if args.status == "all":
        tasks = fetch_tasks(s, cfg, pid, "open") + fetch_tasks(s, cfg, pid, "done")
    else:
        tasks = fetch_tasks(s, cfg, pid, args.status)
    tasks.sort(key=lambda t: (t.get("uniqueId") or 0))

    if args.json:
        json.dump(tasks, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    print(f"=== {project_name}（{prefix or pid}，{len(tasks)} 条，status={args.status}）===")
    print(f"{'ID':10} {'附件':>4} {'状态':4} {'更新':12} 标题")
    for t in tasks:
        uid = t.get("uniqueId", "")
        label = f"{prefix}-{uid}" if prefix and uid else str(uid)
        done = "完成" if t.get("isDone") else "进行"
        upd = (t.get("updated") or "")[:10] or "-"
        print(f"{label:10} {str(t.get('attachmentsCount', 0)):>4} {done:4} {upd:12} {(t.get('content') or '')[:50]}")


# ---------- defect ----------

def find_task(s, cfg, ident, fallback_lib=None, fallback_pid=None):
    """ident 支持：DLT-29 / 29（需 --lib）/ task _id。返回 (task, lib, pid)。"""
    ident = str(ident).strip()
    m = re.match(r"^([A-Z]+)-(\d+)$", ident)
    if m:
        lib = m.group(1)
        pid = resolve_pid(cfg, lib, fallback_pid)
        return _search_unique(s, cfg, lib, int(m.group(2)), pid), lib, pid
    if ident.isdigit() and fallback_lib:
        pid = resolve_pid(cfg, fallback_lib, fallback_pid)
        return _search_unique(s, cfg, fallback_lib, int(ident), pid), fallback_lib, pid
    # 当作 _id：需要 pid（--pid 优先，否则按 --lib 解析）
    pid = fallback_pid or resolve_pid(cfg, fallback_lib, None)
    for t in fetch_tasks(s, cfg, pid, "open") + fetch_tasks(s, cfg, pid, "done"):
        if t.get("_id") == ident:
            return t, fallback_lib, pid
    print(f"[error] 找不到 task _id={ident}", file=sys.stderr)
    sys.exit(1)


def _search_unique(s, cfg, lib, num, pid_override=None):
    pid = resolve_pid(cfg, lib, pid_override)
    for st in ("open", "done"):
        for t in fetch_tasks(s, cfg, pid, st):
            if t.get("uniqueId") == num:
                return t
    print(f"[error] 找不到 {lib}-{num}", file=sys.stderr)
    sys.exit(1)


def safe_filename(name, ext):
    name = str(name or "file")
    name = re.sub(r"[\\/\x00-\x1f\x7f]+", "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name or name in {".", ".."}:
        name = "file"
    ext = re.sub(r"[^A-Za-z0-9._-]+", "_", str(ext or "")).strip("._")
    if ext and not name.lower().endswith("." + ext.lower()):
        name = f"{name}.{ext}"
    return name[:220].rstrip(" .") or "file"


def contained_path(root, name):
    root = os.path.realpath(os.path.abspath(root))
    dest = os.path.realpath(os.path.abspath(os.path.join(root, name)))
    if os.path.commonpath((root, dest)) != root:
        raise ValueError(f"附件路径越界：{name!r}")
    return dest


def attachment_hosts(cfg):
    hosts = {normalize_hostname(cfg.get("domain", "tb.orbbec.com"), "domain")}
    configured = cfg.get("attachment_hosts", [])
    if not isinstance(configured, list):
        raise ValueError("attachment_hosts 必须是主机名数组")
    for host in configured:
        hosts.add(normalize_hostname(host, "attachment_hosts"))
    return hosts


def validate_download_url(url, allowed_hosts):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("附件 URL 必须是带主机名的 HTTPS 地址")
    if parsed.hostname.lower() not in allowed_hosts:
        raise ValueError(f"附件主机未列入 attachment_hosts：{parsed.hostname}")


def download(url, dest, allowed_hosts):
    fd, tmp = tempfile.mkstemp(prefix=".tb-download-", dir=os.path.dirname(dest))
    os.close(fd)
    try:
        current_url = url
        for _ in range(4):
            validate_download_url(current_url, allowed_hosts)
            # 附件请求不复用 TB API Session，避免 Set-Cookie 进入 Cookie Jar
            # 后被自动带到同父域的附件主机。
            with requests.get(current_url, timeout=120, stream=True, allow_redirects=False) as r:
                if r.status_code in REDIRECT_STATUSES:
                    location = r.headers.get("Location")
                    if not location:
                        raise requests.HTTPError(
                            f"HTTP {r.status_code} 重定向缺少 Location", response=r)
                    current_url = urljoin(current_url, location)
                    continue
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(65536):
                        if chunk:
                            f.write(chunk)
                break
        else:
            raise requests.TooManyRedirects("附件下载重定向超过 3 次")
        size = os.path.getsize(tmp)
        os.replace(tmp, dest)
        return size
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def unique_path(dest):
    if not os.path.exists(dest):
        return dest
    base, e = os.path.splitext(dest)
    n = 1
    while os.path.exists(f"{base}_{n}{e}"):
        n += 1
    return f"{base}_{n}{e}"


def collect_files(activities):
    """从 activities 抽取所有附件文件（action=activity.comment.attachments 的 content.files[]）。"""
    files = []
    for a in activities:
        if a.get("action") != "activity.comment.attachments":
            continue
        for f in (a.get("content") or {}).get("files") or []:
            files.append(f)
    return files


def is_video_attachment(file_meta):
    """按 MIME 类型优先、扩展名兜底识别视频附件。"""
    mime_type = str(file_meta.get("mimeType") or "").strip().lower()
    if mime_type.startswith("video/"):
        return True

    ext = str(file_meta.get("ext") or "").strip().lower().lstrip(".")
    if ext in VIDEO_EXTENSIONS:
        return True

    name_ext = os.path.splitext(str(file_meta.get("name") or ""))[1]
    return name_ext.lower().lstrip(".") in VIDEO_EXTENSIONS


def attachment_meta(file_meta, safe_name=None):
    """生成不含下载地址和短期鉴权信息的附件摘要。"""
    return {
        "name": safe_name or file_meta.get("name"),
        "ext": file_meta.get("ext"),
        "mimeType": file_meta.get("mimeType"),
        "size": file_meta.get("size"),
    }


def is_sensitive_meta_key(key):
    normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
    return (normalized.endswith(("url", "uri", "href", "link")) or
            "token" in normalized or "cookie" in normalized or
            "authorization" in normalized)


def redact_sensitive(value):
    """递归移除附件 URL、token、cookie 等短期鉴权字段。"""
    if isinstance(value, dict):
        return {
            key: redact_sensitive(item)
            for key, item in value.items()
            if not is_sensitive_meta_key(key)
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    return value


def safe_error(exc):
    """返回不含请求 URL、query token 或响应正文的错误摘要。"""
    response = getattr(exc, "response", None)
    status_code = getattr(response, "status_code", None)
    if status_code is not None:
        return f"{type(exc).__name__}(HTTP {status_code})"
    return type(exc).__name__


def write_json_atomic(path, data):
    fd, tmp = tempfile.mkstemp(prefix=".tb-meta-", dir=os.path.dirname(path), text=True)
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


def cmd_defect(args):
    cfg = load_config()
    s = session(cfg)
    allowed_hosts = attachment_hosts(cfg)
    task, lib, pid = find_task(s, cfg, args.id, args.lib, args.pid)
    project = fetch_project(s, cfg, pid)
    project_name, prefix = project_identity(cfg, project, lib, pid)
    tid = task["_id"]
    uid = task.get("uniqueId")
    raw_label = f"{prefix}-{uid}" if (prefix and uid) else (args.id if not uid else str(uid))
    label = safe_filename(raw_label, None)
    project_dir_name = safe_filename(project_name, None)
    print(f"=== {label}：{task.get('content', '')} ===")

    activities = fetch_activities(s, cfg, tid)
    comments = [a for a in activities if a.get("action") == "activity.comment.attachments"]
    files = collect_files(activities)

    if args.out:
        out_root = resolve_path(args.out, os.getcwd())
    else:
        out_root = resolve_path(cfg.get("log_root", "~/work/log/mower-tb-triage"))
    project_dir = contained_path(out_root, project_dir_name)
    dest_dir = contained_path(project_dir, label)
    os.makedirs(project_dir, mode=0o700, exist_ok=True)
    os.makedirs(dest_dir, mode=0o700, exist_ok=True)

    downloaded = []
    deferred_videos = []
    failed = []
    for f in files:
        fname = safe_filename(f.get("name"), f.get("ext"))
        if is_video_attachment(f) and not args.include_video:
            deferred_videos.append(attachment_meta(f, fname))
            size = f.get("size")
            size_text = f"{size:,} bytes" if isinstance(size, int) else "大小未知"
            print(f"  [skip-video] {fname}（{size_text}，等待用户确认）")
            continue
        dest = unique_path(contained_path(dest_dir, fname))
        url = f.get("url", "")
        try:
            sz = download(url, dest, allowed_hosts)
        except Exception as e:
            # token 可能过期 → 刷新 activities，按附件摘要唯一匹配 url
            print(f"  [retry] {fname} 下载失败（{type(e).__name__}），刷新 token 重试...")
            url = _refresh_url(s, cfg, tid, f)
            if not url:
                print(f"  [fail] {fname}：刷新后无唯一可用 url")
                failed.append({"name": fname, "error": "refresh_url_missing_or_ambiguous"})
                continue
            try:
                sz = download(url, dest, allowed_hosts)
            except Exception as e2:
                error = safe_error(e2)
                print(f"  [fail] {fname}：{error}")
                failed.append({"name": fname, "error": error})
                continue
        downloaded.append({"name": fname, "path": os.path.relpath(dest, out_root), "size": sz})
        print(f"  [ok] {fname}（{sz:,} bytes）")

    meta = {
        "id": label, "title": task.get("content"), "note": task.get("note"),
        "uniqueId": uid, "_id": tid,
        "isDone": task.get("isDone"), "updated": task.get("updated"),
        "project": {"id": pid, "name": project_name, "prefix": prefix},
        "attachmentsCount_cache": task.get("attachmentsCount"),
        "comments": [{"action": a.get("action"), "created": a.get("created"),
                      "content": redact_sensitive(a.get("content"))} for a in comments],
        "files": [attachment_meta(f) for f in files],
        "downloaded": downloaded,
        "deferred_videos": deferred_videos,
        "failed": failed,
        "dir": dest_dir,
    }
    meta_path = os.path.join(dest_dir, f"{label}_meta.json")
    write_json_atomic(meta_path, meta)

    print(f"\n[ok] 日志目录：{dest_dir}")
    print(f"[ok] 元信息：{meta_path}")
    print(f"[ok] 评论 {len(comments)} 条 / 附件 {len(files)} 个 / 下载 {len(downloaded)} 个")
    if deferred_videos:
        print(f"[confirm] {len(deferred_videos)} 个视频附件默认未下载；"
              "请先取得用户明确同意，再使用 --include-video。")
    if failed:
        print(f"[partial] 有 {len(failed)} 个附件下载失败；请先处理失败项，暂不进入日志分析。",
              file=sys.stderr)
        return 2
    if downloaded:
        print(f"     下一步：用 systematic-debugging 分析 {dest_dir}")
    return 0


def _refresh_url(s, cfg, tid, original):
    try:
        urls = set()
        for a in fetch_activities(s, cfg, tid):
            for f in (a.get("content") or {}).get("files") or []:
                if all(f.get(key) == original.get(key)
                       for key in ("name", "ext", "size", "mimeType")):
                    url = f.get("url")
                    if isinstance(url, str) and url.strip():
                        urls.add(url)
        return urls.pop() if len(urls) == 1 else None
    except Exception:
        return None


def main():
    cfg = load_config()
    libs = list(cfg.get("projects", {}).keys()) or ["DLT", "DMT"]
    ap = argparse.ArgumentParser(description="从 Teambition 拉割草机缺陷（list / defect）")
    ap.add_argument("--lib", choices=libs, help=f"缺陷库：{libs}")
    ap.add_argument("--pid", help="直接指定 project ID（覆盖 --lib）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="列缺陷")
    pl.add_argument("--status", choices=["open", "done", "all"], default="open")
    pl.add_argument("--json", action="store_true", help="输出原始 JSON")
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser("defect", help="拉单个缺陷：详情 + 真实评论 + 下载非视频附件")
    pd.add_argument("id", help="缺陷标识，如 DLT-29（或纯数字配 --lib，或 task _id）")
    pd.add_argument("--out", help="下载根目录（默认 config.log_root）")
    pd.add_argument(
        "--include-video", action="store_true",
        help="下载视频附件；仅在用户明确确认后使用，脚本本身不会解析视频流")
    pd.set_defaults(func=cmd_defect)

    args = ap.parse_args()
    if not args.lib and not args.pid:
        args.lib = "DLT"
    return args.func(args) or 0


if __name__ == "__main__":
    raise SystemExit(main())
