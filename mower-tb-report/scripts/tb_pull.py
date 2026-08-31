#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 Teambition（tb.orbbec.com）拉割草机缺陷：列缺陷 / 拉单个缺陷 / 给缺陷发评论+附件。

子命令：
  list    列缺陷（uniqueId / 标题 / 附件数 / 状态 / 更新时间）
  defect  拉指定缺陷：拉 activities 拿真实评论 + 附件，下载附件（日志）到 {out}/{ID}/，写 {ID}_meta.json
  comment 给缺陷发评论（文字 + 可选附件）。附件经 awos/MinIO 上传后以 fileTokens 挂到评论。

依赖：requests。cookie 由 tb_cookie.py 生成。

用法示例：
  python3 tb_pull.py --lib DLT list
  python3 tb_pull.py list --lib DLT --json
  python3 tb_pull.py defect DLT-29
  python3 tb_pull.py defect DMT-292 --out /home/tudou/work/log
  # 发评论
  python3 tb_pull.py comment DLT-29 --text "见附件"
  python3 tb_pull.py comment DLT-29 --text "完整报告见附件" -a /home/tudou/work/log/DLT-29/DLT-29_分析报告.md
  python3 tb_pull.py comment DLT-29 --text-file 摘要.md -a 报告.md -a 现场图.png
"""
import argparse, datetime, hashlib, hmac, json, mimetypes, os, re, sys
import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    for rel in ("../config.json", "../config.example.json"):
        p = os.path.join(SCRIPT_DIR, rel)
        if os.path.exists(p):
            with open(p) as f:
                return json.load(f)
    return {}


def cookie_file(cfg):
    return os.path.join(SCRIPT_DIR, cfg.get("cookie_file", ".tb_cookie"))


def session(cfg):
    cp = cookie_file(cfg)
    if not os.path.exists(cp):
        print(f"[error] cookie 不存在：{cp}\n        先跑：python3 {os.path.join(SCRIPT_DIR, 'tb_cookie.py')}", file=sys.stderr)
        sys.exit(1)
    s = requests.Session()
    s.headers["Cookie"] = open(cp).read().strip()
    return s


def resolve_pid(cfg, lib, pid):
    if pid:
        return pid
    proj = cfg.get("projects", {})
    if lib in proj:
        return proj[lib]["pid"]
    print(f"[error] 未知库 '{lib}'，可用：{list(proj.keys())}（或用 --pid 指定）", file=sys.stderr)
    sys.exit(1)


def base_url(cfg):
    return "https://" + cfg.get("domain", "tb.orbbec.com")


def api_get(s, cfg, path, **params):
    r = s.get(base_url(cfg) + path, params=params, timeout=30)
    if r.status_code == 401:
        print("[error] 401 鉴权失败——cookie 过期，请重跑 tb_cookie.py", file=sys.stderr)
        sys.exit(1)
    r.raise_for_status()
    return r.json()


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


# ---------- list ----------

def cmd_list(args):
    cfg = load_config()
    s = session(cfg)
    pid = resolve_pid(cfg, args.lib, args.pid)
    if args.status == "all":
        tasks = fetch_tasks(s, cfg, pid, "open") + fetch_tasks(s, cfg, pid, "done")
    else:
        tasks = fetch_tasks(s, cfg, pid, args.status)
    tasks.sort(key=lambda t: (t.get("uniqueId") or 0))

    if args.json:
        json.dump(tasks, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return

    lib = args.lib or pid
    print(f"=== {lib} 缺陷（{len(tasks)} 条，status={args.status}）===")
    print(f"{'ID':10} {'附件':>4} {'状态':4} {'更新':12} 标题")
    for t in tasks:
        uid = t.get("uniqueId", "")
        label = f"{args.lib}-{uid}" if args.lib and uid else str(uid)
        done = "完成" if t.get("isDone") else "进行"
        upd = (t.get("updated") or "")[:10] or "-"
        print(f"{label:10} {str(t.get('attachmentsCount', 0)):>4} {done:4} {upd:12} {(t.get('content') or '')[:50]}")


# ---------- defect ----------

def find_task(s, cfg, ident, fallback_lib=None, fallback_pid=None):
    """ident 支持：DLT-29 / 29（需 --lib）/ task _id。返回 (task, lib)。"""
    ident = str(ident).strip()
    m = re.match(r"^([A-Z]+)-(\d+)$", ident)
    if m:
        return _search_unique(s, cfg, m.group(1), int(m.group(2))), m.group(1)
    if ident.isdigit() and fallback_lib:
        return _search_unique(s, cfg, fallback_lib, int(ident)), fallback_lib
    # 当作 _id：需要 pid（--pid 优先，否则按 --lib 解析）
    pid = fallback_pid or resolve_pid(cfg, fallback_lib, None)
    for t in fetch_tasks(s, cfg, pid, "open") + fetch_tasks(s, cfg, pid, "done"):
        if t.get("_id") == ident:
            return t, None
    print(f"[error] 找不到 task _id={ident}", file=sys.stderr)
    sys.exit(1)


def _search_unique(s, cfg, lib, num):
    pid = resolve_pid(cfg, lib, None)
    for st in ("open", "done"):
        for t in fetch_tasks(s, cfg, pid, st):
            if t.get("uniqueId") == num:
                return t
    print(f"[error] 找不到 {lib}-{num}", file=sys.stderr)
    sys.exit(1)


def safe_filename(name, ext):
    name = (name or "file").strip()
    ext = (ext or "").strip().lstrip(".")
    if ext and not name.lower().endswith("." + ext.lower()):
        return f"{name}.{ext}"
    return name


def download(s, url, dest):
    with s.get(url, timeout=120, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
    return os.path.getsize(dest)


def unique_path(dest):
    if not os.path.exists(dest):
        return dest
    base, e = os.path.splitext(dest)
    n = 1
    while os.path.exists(f"{base}_{n}{e}"):
        n += 1
    return f"{base}_{n}{e}"


def _split_name_ext(filename):
    """从 'xxx.zip' 拆出 (name='xxx', ext='zip')；无扩展名则 ext=''。"""
    base, dotext = os.path.splitext(filename or "")
    if dotext:
        return base, dotext.lstrip(".")
    return filename or "file", ""


def _normalize_attachment(att):
    """归一化 content.attachments[] 的 work(项目文件库) 附件到与 content.files[] 一致的结构。
    work 附件字段为 fileName/downloadUrl（无独立 ext/size），需拆名/补字段。"""
    fname = att.get("fileName") or att.get("name") or "file"
    name, ext = _split_name_ext(fname)
    return {
        "name": name,
        "ext": ext or (att.get("ext") or ""),
        "url": att.get("downloadUrl") or att.get("url") or "",
        "size": att.get("size"),
        "mimeType": att.get("mimeType"),
        "_source": "attachment(work)",
    }


def collect_files(activities):
    """从 activities 抽取所有附件，统一归一化为 {name, ext, url, size, mimeType}，按 url 去重。
    两种来源：
      - content.files[]：action=activity.comment.attachments 的标准附件（字段 name/ext/url/size）；
      - content.attachments[]：普通评论(activity.comment)引用的项目文件库 work 附件（字段 fileName/downloadUrl）。
    后者此前被遗漏——测试员常把整车日志传到文件库后在评论里引用，必须同时收集。"""
    files = []
    seen = set()
    for a in activities:
        c = a.get("content") or {}
        if not isinstance(c, dict):
            continue
        for f in c.get("files") or []:
            f = dict(f)
            f.setdefault("_source", "files")
            key = f.get("url") or f.get("_id")
            if key in seen:
                continue
            seen.add(key)
            files.append(f)
        for att in c.get("attachments") or []:
            nf = _normalize_attachment(att)
            key = nf.get("url") or att.get("_id")
            if key in seen:
                continue
            seen.add(key)
            files.append(nf)
    return files


def cmd_defect(args):
    cfg = load_config()
    s = session(cfg)
    task, lib = find_task(s, cfg, args.id, args.lib, args.pid)
    tid = task["_id"]
    uid = task.get("uniqueId")
    label = f"{lib}-{uid}" if (lib and uid) else (args.id if not uid else str(uid))
    print(f"=== {label}：{task.get('content', '')} ===")

    activities = fetch_activities(s, cfg, tid)
    comments = [a for a in activities if a.get("action") == "activity.comment.attachments"]
    files = collect_files(activities)

    out_root = args.out or cfg.get("log_root", "/home/tudou/work/log")
    dest_dir = os.path.join(out_root, label)
    os.makedirs(dest_dir, exist_ok=True)

    downloaded = []
    for f in files:
        fname = safe_filename(f.get("name"), f.get("ext"))
        dest = unique_path(os.path.join(dest_dir, fname))
        url = f.get("url", "")
        try:
            sz = download(s, url, dest)
        except Exception as e:
            # token 可能过期 → 刷新 activities 重取同 (name,ext) 的 url
            print(f"  [retry] {fname} 下载失败（{type(e).__name__}），刷新 token 重试...")
            url = _refresh_url(s, cfg, tid, f.get("name"), f.get("ext"))
            if not url:
                print(f"  [fail] {fname}：刷新后仍无可用 url")
                continue
            try:
                sz = download(s, url, dest)
            except Exception as e2:
                print(f"  [fail] {fname}：{e2}")
                continue
        downloaded.append({"name": fname, "path": os.path.relpath(dest, out_root), "size": sz})
        print(f"  [ok] {fname}（{sz:,} bytes）")

    meta = {
        "id": label, "title": task.get("content"), "note": task.get("note"),
        "uniqueId": uid, "_id": tid,
        "attachmentsCount_cache": task.get("attachmentsCount"),
        "comments": [{"action": a.get("action"), "created": a.get("created"),
                      "content": a.get("content")} for a in comments],
        "files": [{"name": f.get("name"), "ext": f.get("ext"),
                   "mimeType": f.get("mimeType"), "size": f.get("size")} for f in files],
        "downloaded": downloaded,
        "dir": dest_dir,
    }
    meta_path = os.path.join(dest_dir, f"{label}_meta.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n[ok] 日志目录：{dest_dir}")
    print(f"[ok] 元信息：{meta_path}")
    print(f"[ok] 评论 {len(comments)} 条 / 附件 {len(files)} 个 / 下载 {len(downloaded)} 个")
    if downloaded:
        print(f"     下一步：用 mower-log-analysis 分析 {dest_dir}")


def _refresh_url(s, cfg, tid, name, ext):
    try:
        for f in collect_files(fetch_activities(s, cfg, tid)):
            if f.get("name") == name and f.get("ext") == ext:
                return f.get("url")
    except Exception:
        return None
    return None


# ---------- comment ----------

def _guess_filetype(path):
    mime, _ = mimetypes.guess_type(path)
    return mime or "application/octet-stream"


def _s3_put(cred, region, up, bucket, key, data, content_type):
    """AWS SigV4 PutObject 到 MinIO。关键：host header 带 :443。"""
    now = datetime.datetime.utcnow()
    amzdate = now.strftime("%Y%m%dT%H%M%SZ")
    ds = now.strftime("%Y%m%d")
    ph = hashlib.sha256(data).hexdigest()
    host = "tb.orbbec.com:443"
    cd = up.get("ContentDisposition", "")
    ch = (f"content-disposition:{cd}\ncontent-type:{content_type}\nhost:{host}\n"
          f"x-amz-content-sha256:{ph}\nx-amz-date:{amzdate}\n"
          f"x-amz-security-token:{cred['sessionToken']}\n")
    sh = "content-disposition;content-type;host;x-amz-content-sha256;x-amz-date;x-amz-security-token"
    canon = f"PUT\n/{bucket}/{key}\n\n{ch}\n{sh}\n{ph}"
    crh = hashlib.sha256(canon.encode()).hexdigest()
    scope = f"{ds}/{region}/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amzdate}\n{scope}\n{crh}"

    def sg(k, m):
        return hmac.new(k, m.encode(), hashlib.sha256).digest()

    k = sg(("AWS4" + cred["secretAccessKey"]).encode(), ds)
    k = sg(k, region); k = sg(k, "s3"); k = sg(k, "aws4_request")
    sig = hmac.new(k, sts.encode(), hashlib.sha256).hexdigest()
    auth = (f"AWS4-HMAC-SHA256 Credential={cred['accessKeyId']}/{scope}, "
            f"SignedHeaders={sh}, Signature={sig}")
    headers = {"Authorization": auth, "content-disposition": cd, "content-type": content_type,
               "x-amz-content-sha256": ph, "x-amz-date": amzdate,
               "x-amz-security-token": cred["sessionToken"]}
    resp = requests.put(f"https://{host}/{bucket}/{key}", headers=headers, data=data, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"S3 PUT 失败 {resp.status_code}: {resp.text[:200]}")


def upload_attachment(s, cfg, tid, filepath):
    """上传一个文件到 awos/MinIO，返回 (token, fileName, fileType, fileSize)。

    流程：POST /api/awos/upload-token（scope 必须是 "task:<tid>"）→ SigV4 PutObject。
    scope 写错（如 "task"）会让 token 无效、后续发评论报"参数有误:fileTokens"。
    """
    data = open(filepath, "rb").read()
    size = len(data)
    fname = os.path.basename(filepath)
    ftype = _guess_filetype(filepath)
    base = base_url(cfg)
    H = {"Content-Type": "application/json", "Origin": base, "Referer": f"{base}/"}
    r = s.post(f"{base}/api/awos/upload-token",
               json={"scope": f"task:{tid}", "category": "attachment",
                     "fileName": fname, "fileType": ftype, "fileSize": size},
               headers=H, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(f"upload-token 失败 {r.status_code}: {r.text[:200]}")
    tk = r.json()
    cred = tk["sdk"]["credentials"]
    up = tk["upload"]
    region = tk["sdk"]["region"]
    _s3_put(cred, region, up, up["Bucket"], up["Key"], data, ftype)
    return tk["token"], fname, ftype, size


def post_comment(s, cfg, tid, text, file_tokens=None):
    """发评论（文字 + 可选附件 tokens），返回新 activity。

    POST /api/v2/tasks/{tid}/activities，body 必须带全字段（attachments/dingFiles/
    mentions/isDingtalkPM 等缺一可能被校验拒）。
    """
    base = base_url(cfg)
    H = {"Content-Type": "application/json", "Origin": base, "Referer": f"{base}/"}
    body = {"content": text or "", "attachments": [], "fileTokens": file_tokens or [],
            "dingFiles": [], "renderMode": "text", "isOnlyNotifyMentions": False,
            "mentions": {}, "mentionedTeams": [], "mentionedGroups": [], "isDingtalkPM": True}
    r = s.post(f"{base}/api/v2/tasks/{tid}/activities", json=body, headers=H, timeout=15)
    if r.status_code >= 400:
        raise RuntimeError(f"发评论失败 {r.status_code}: {r.text[:300]}")
    return r.json()


def cmd_comment(args):
    cfg = load_config()
    s = session(cfg)
    task, lib = find_task(s, cfg, args.id, args.lib, args.pid)
    tid = task["_id"]
    uid = task.get("uniqueId")
    label = f"{lib}-{uid}" if (lib and uid) else args.id
    print(f"=== {label}：{task.get('content', '')} ===")

    text = ""
    if args.text_file:
        text = open(args.text_file, encoding="utf-8").read()
    if args.text:
        text = (text + "\n\n" + args.text) if text else args.text
    if not text and not args.attach:
        print("[error] 至少提供 --text/--text-file 或 --attach 之一", file=sys.stderr)
        sys.exit(1)

    # 预览（不可逆，先打印将发什么）
    preview = text.replace("\n", " ")
    print(f"[预览] 文字({len(text)}字)：{preview[:80]}{'…' if len(preview) > 80 else ''}")
    print(f"[预览] 附件：{args.attach or '无'}")

    tokens = []
    for p in (args.attach or []):
        if not os.path.exists(p):
            print(f"[error] 附件不存在：{p}", file=sys.stderr)
            sys.exit(1)
        token, fname, ftype, size = upload_attachment(s, cfg, tid, p)
        tokens.append(token)
        print(f"  [upload] {fname}（{size:,} bytes, {ftype}）")

    act = post_comment(s, cfg, tid, text, tokens)
    c = act.get("content", {})
    files = c.get("files", []) if isinstance(c, dict) else []
    print(f"\n[ok] 评论已发布（_id={act.get('_id')}，附件 {len(files)} 个）")
    for f in files:
        print(f"   📎 {f.get('name')}.{f.get('ext')}（{f.get('size', 0):,} bytes）")


def main():
    cfg = load_config()
    libs = list(cfg.get("projects", {}).keys()) or ["DLT", "DMT"]
    ap = argparse.ArgumentParser(description="从 Teambition 拉割草机缺陷（list / defect / comment）")
    ap.add_argument("--lib", choices=libs, help=f"缺陷库：{libs}")
    ap.add_argument("--pid", help="直接指定 project id（覆盖 --lib）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pl = sub.add_parser("list", help="列缺陷")
    pl.add_argument("--status", choices=["open", "done", "all"], default="open")
    pl.add_argument("--json", action="store_true", help="输出原始 JSON")
    pl.set_defaults(func=cmd_list)

    pd = sub.add_parser("defect", help="拉单个缺陷：详情 + 真实评论 + 下载日志")
    pd.add_argument("id", help="缺陷标识，如 DLT-29（或纯数字配 --lib，或 task _id）")
    pd.add_argument("--out", help="下载根目录（默认 config.log_root）")
    pd.set_defaults(func=cmd_defect)

    pc = sub.add_parser("comment", help="给缺陷发评论（文字 + 可选附件）")
    pc.add_argument("id", help="缺陷标识，如 DLT-29（或纯数字配 --lib，或 task _id）")
    pc.add_argument("-t", "--text", help="评论文字")
    pc.add_argument("--text-file", help="从文件读评论文字")
    pc.add_argument("-a", "--attach", action="append", help="附件路径（可多次指定多个）")
    pc.set_defaults(func=cmd_comment)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
