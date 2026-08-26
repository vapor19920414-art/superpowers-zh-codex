#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 systematic-debugging 产出的分析报告，切分生成「TB 评论草稿」骨架。

草稿格式对齐 logs_auto/DLT_评论草稿.md 的五字段：根因 / 机制 / 证据 / 置信度 / 修复。
报告按本技能约定组织（## 0 结论摘要 / ## 2 事件时间线 / ## 3 跨模块链路 / ## 5 修复方案），
本脚本做机械切分映射；**它不重新总结**——精炼由人工（或 Claude）完成。
输出顶部会标注「待人工精炼」。

用法：
  python3 tb_draft.py ~/work/log/mower-tb-triage/<项目名>/DLT-9/DLT-9_分析报告.md
  python3 tb_draft.py ~/work/log/mower-tb-triage/<项目名>/DLT-9       # 传目录，自动找报告
  python3 tb_draft.py DLT-9_分析报告.md --out 草稿.md                 # 追加到草稿文件
"""
import argparse
import os
import re
import sys


def find_report(path):
    path = os.path.expanduser(path)
    if os.path.isdir(path):
        # 目录内直接找
        for f in sorted(os.listdir(path)):
            if "分析报告" in f and f.endswith(".md"):
                return os.path.join(path, f)
        # 往下一层
        for f in sorted(os.listdir(path)):
            sub = os.path.join(path, f)
            if os.path.isdir(sub):
                for ff in os.listdir(sub):
                    if "分析报告" in ff and ff.endswith(".md"):
                        return os.path.join(sub, ff)
        return None
    return path if os.path.isfile(path) else None


def split_sections(text):
    """按 `## N.` 切大节，返回 {num: (title, body)}。"""
    secs, matches = {}, list(re.finditer(r'^##\s+(\d+)\.?\s*(.*)$', text, re.M))
    for i, m in enumerate(matches):
        num = int(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        secs[num] = (title, text[start:end].strip())
    return secs


def clean_prose(body):
    """去掉代码块、表格行、引用/子标题标记，返回散文。"""
    out, in_code, blank = [], False, False
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or s.startswith("|"):
            continue
        if not s:
            if not blank:
                out.append("")
                blank = True
            continue
        s = re.sub(r'^>\s?', '', s)            # 去引用标记
        s = re.sub(r'^#{3,}\s*', '', s)        # ### 子标题降为散文
        if s:
            out.append(s)
            blank = False
    return "\n".join(out).strip()


def numbered_points(body):
    """提取 ##0 的编号要点（支持跨行续接）。"""
    pts, cur = [], []
    for ln in body.splitlines():
        m = re.match(r'^\s*(\d+)[.、)]\s*(.*)$', ln)
        if m:
            if cur:
                pts.append(" ".join(cur).strip())
            cur = [m.group(2)]
        elif cur and ln.strip():
            cur.append(ln.strip())
    if cur:
        pts.append(" ".join(cur).strip())
    return [re.sub(r'\*\*', '', p).strip() for p in pts if p]


def find_point(points, *kws):
    for p in points:
        if any(k in p for k in kws):
            return p
    return None


def strip_label(p):
    """去掉要点开头冗余的标签前缀（字段名已在外层给出）。"""
    return re.sub(r"^(根因|置信度|机理|机制|修复方向?|建议)[：:]\s*", "", p).strip()


def evidence_lines(body, maxn=2):
    """##2 第一个代码块里含时间戳的行。"""
    in_code, buf = False, []
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith("```"):
            if in_code:
                break
            in_code = True
            continue
        if in_code and s and re.search(r'\d{1,2}:\d{2}', s):
            buf.append(s)
    return buf[:maxn]


def conclusion_lines(body, maxn=2):
    """##2 里 `>` 引用的对照结论（最精炼的定性句）。"""
    out = []
    for ln in body.splitlines():
        s = ln.strip()
        if s.startswith(">") and not s.startswith(">```"):
            t = s.lstrip("> ").strip()
            if len(t) > 8:
                out.append(t)
    return out[:maxn]


def truncate(s, n):
    s = s.strip()
    return s if len(s) <= n else s[:n].rstrip() + "…"


def build_draft(report_path, text):
    # 缺陷 ID + 标题：优先正文首行，其次文件名
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    m = re.search(r'#\s*([A-Z]+-\d+)\s*分析报告[：:]\s*(.*)', first)
    if m:
        did, title = m.group(1), m.group(2).strip()
    else:
        fn = os.path.basename(report_path)
        mm = re.search(r'([A-Z]+-\d+)', fn)
        did = mm.group(1) if mm else os.path.basename(os.path.dirname(report_path))
        title = fn.replace("_分析报告.md", "")

    secs = split_sections(text)
    s0 = secs.get(0, ("", ""))[1]
    s2 = secs.get(2, ("", ""))[1]
    s3 = secs.get(3, ("", ""))[1]
    s5 = secs.get(5, ("", ""))[1]

    pts = numbered_points(s0)
    root_pt = find_point(pts, "根因")
    exclude_pt = find_point(pts, "不是", "非")
    conf_pt = find_point(pts, "置信度", "残余")

    root = root_pt or (pts[0] if pts else "")
    if exclude_pt and exclude_pt != root_pt:
        root = (root + " " + exclude_pt).strip()
    root = strip_label(root)

    bits = []
    bits.extend(conclusion_lines(s2))
    bits.extend(f"`{l}`" for l in evidence_lines(s2))
    evidence = "；".join(bits)

    confidence = strip_label(conf_pt) if conf_pt else "（见报告「最终共识 & 残余不确定性」）"
    mechanism = clean_prose(s3)
    fix = clean_prose(s5)

    rows = [
        f"## 【{did}】{title}",
        "",
        f"> ⚠ 本段由 tb_draft 自动从 `{os.path.basename(report_path)}` 切分生成，粘贴 TB 前请人工精炼核对。",
        "",
        f"**根因**：{truncate(root, 500)}" if root else "**根因**：（见报告第 0 节）",
        "",
        f"**机制**：{truncate(mechanism, 600)}" if mechanism else "**机制**：（见报告第 3 节）",
        "",
        f"**证据**：{truncate(evidence, 400)}" if evidence else "**证据**：（见报告第 2 节）",
        "",
        f"**置信度**：{truncate(confidence, 300)}",
        "",
        f"**修复**：{truncate(fix, 500)}" if fix else "**修复**：（见报告第 5 节）",
        "",
    ]
    return "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description="从分析报告切分生成 TB 评论草稿骨架")
    ap.add_argument("report", help="报告 .md，或缺陷目录（自动找 *_分析报告.md）")
    ap.add_argument("--out", help="追加到此草稿文件；省略则打印 stdout")
    args = ap.parse_args()

    rp = find_report(args.report)
    if not rp:
        print(f"[error] 找不到报告：{args.report}", file=sys.stderr)
        sys.exit(1)
    with open(rp, encoding="utf-8") as f:
        text = f.read()
    draft = build_draft(rp, text)

    if args.out:
        out = os.path.abspath(os.path.expanduser(args.out))
        os.makedirs(os.path.dirname(out), mode=0o700, exist_ok=True)
        with open(out, "a", encoding="utf-8") as f:
            f.write("\n---\n\n" + draft + "\n")
        os.chmod(out, 0o600)
        print(f"[ok] 已追加到 {out}")
    else:
        print(draft)


if __name__ == "__main__":
    main()
