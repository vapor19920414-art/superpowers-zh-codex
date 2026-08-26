#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参数化解密 Chrome 的 Teambition 鉴权 Cookie，供 tb_pull.py 使用。

Chrome 149 / cookie DB v24 方案（已验证稳定）：
  密钥 = PBKDF2-HMAC-SHA1(keyring "Chrome Safe Storage" 原文, salt='saltysalt', iter=1, dklen=16)
  解密 = AES-128-CBC(IV=16 空格) over encrypted_value[3:]（去掉 'v11' 前缀）
  明文前 32 字节是 domain 的 SHA256 哈希，跳过；再去 PKCS7 填充。

用法：
  python3 tb_cookie.py                       # 用 config 里的 profile/domain
  python3 tb_cookie.py --profile Default     # 换 Chrome profile
  python3 tb_cookie.py --domain tb.orbbec.com --out /tmp/tb.cookie

前置：先在 Chrome 里登录 https://<domain>/。系统 python 需 cryptography + secretstorage。
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_ENV = "MOWER_TB_CONFIG"


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


def get_keyring_pass():
    try:
        import secretstorage
        bus = secretstorage.dbus_init()
        for it in secretstorage.search_items(bus, {"application": "chrome"}):
            if it.get_label() == "Chrome Safe Storage":
                return it.get_secret()
    except Exception as e:
        print(f"[warn] keyring 取密钥失败，回退 'peanuts'：{e!r}", file=sys.stderr)
    return b"peanuts"


def decrypt_cookie(ev, key, skip32):
    if len(ev) <= 3 or ev[:3] not in (b"v10", b"v11"):
        raise ValueError("不支持的 Chrome cookie 加密格式")
    d = Cipher(algorithms.AES(key), modes.CBC(b" " * 16), backend=default_backend()).decryptor()
    pt = d.update(ev[3:]) + d.finalize()      # 去 'v11' 前缀，AES-128-CBC
    if skip32:
        if len(pt) < 32:
            raise ValueError("cookie 明文短于 DB v24 domain hash")
        pt = pt[32:]                          # 跳过 32 字节 domain SHA256（DB v24+）
    if not pt:
        raise ValueError("cookie 明文为空")
    pad = pt[-1]
    if not 1 <= pad <= 16 or pt[-pad:] != bytes([pad]) * pad:
        raise ValueError("cookie PKCS7 padding 无效")
    pt = pt[:-pad]
    return pt


def list_profiles(base):
    out = []
    if os.path.isdir(base):
        for d in os.listdir(base):
            full = os.path.join(base, d)
            if os.path.isdir(full) and (d == "Default" or d.startswith("Profile")):
                out.append(d)
    return sorted(out)


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser(description="解密 Chrome cookie -> 私有 cookie 文件（供 tb_pull.py 用）")
    ap.add_argument("--profile", default=cfg.get("chrome_profile", "Default"), help="Chrome profile 名（默认 %(default)s）")
    ap.add_argument("--domain", default=cfg.get("domain", "tb.orbbec.com"))
    ap.add_argument("--base", default=os.path.expanduser(cfg.get("chrome_base", "~/.config/google-chrome")),
                    help="Chrome 用户数据根目录")
    ap.add_argument("--out", default=None, help="输出文件（默认读取配置 cookie_file）")
    args = ap.parse_args()

    src = os.path.join(args.base, args.profile, "Cookies")
    if not os.path.exists(src):
        print(f"[error] 找不到 cookie DB：{src}", file=sys.stderr)
        print(f"        请先在 Chrome 登录 https://{args.domain}/，并确认 profile 名。", file=sys.stderr)
        avail = list_profiles(args.base)
        print(f"        可用 profile：{avail or '（未在 ' + args.base + ' 下找到任何 Chrome profile）'}", file=sys.stderr)
        print(f"        提示：用 --profile 指定，或 --base 指定 Chrome 数据根（如 ~/.config/chromium）。", file=sys.stderr)
        sys.exit(1)

    out = resolve_path(args.out or cfg.get(
        "cookie_file", "~/.local/state/mower-tb-triage/tb.cookie"))

    key = hashlib.pbkdf2_hmac("sha1", get_keyring_pass(), b"saltysalt", 1, 16)
    fd, tmp = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    con = None
    try:
        # 保留 mkstemp 的 0600 权限，并确保复制/连接失败也删除临时库。
        shutil.copyfile(src, tmp)
        con = sqlite3.connect(tmp)
        try:
            ver = con.execute("select value from meta where key='version'").fetchone()
        except Exception:
            ver = None
        skip32 = bool(ver) and int(ver[0]) >= 24
        print(f"[info] cookie DB version={ver} skip32={skip32} profile={args.profile}")
        # host 匹配：tb.orbbec.com / .tb.orbbec.com / .orbbec.com
        domain = args.domain
        hosts = [domain, "." + domain, "." + domain.split(".", 1)[-1]] if "." in domain else [domain]
        qmarks = ",".join("?" * len(hosts))
        rows = con.execute(
            f"select host_key, name, encrypted_value from cookies "
            f"where host_key in ({qmarks}) order by host_key, name", hosts
        ).fetchall()
    finally:
        if con is not None:
            con.close()
        os.remove(tmp)

    got, errors = {}, []
    for host, name, ev in rows:
        if ev[:3] not in (b"v10", b"v11"):
            continue
        try:
            val = decrypt_cookie(ev, key, skip32).decode("utf-8")
        except Exception as e:
            errors.append((host, name, type(e).__name__))
            continue
        # 优先精确 host
        if name not in got or host == domain:
            got[name] = (val, host)
    if errors:
        print("[warn] 解密失败（部分 cookie 跳过）：", errors, file=sys.stderr)

    WANT = ["TB_ACCESS_TOKEN", "sl-session", "teambition_private_sid",
            "teambition_private_sid.sig", "teambition_lang", "TB_TENANT_TYPE", "TB_GTA"]
    pairs, seen = [], set()
    for n in WANT + [x for x in got if x not in WANT]:
        if n in got and n not in seen and got[n][0].strip():
            seen.add(n)
            pairs.append(f"{n}={got[n][0]}")
    header = "; ".join(pairs)
    required = ("TB_ACCESS_TOKEN", "sl-session", "teambition_private_sid")
    ok = all(k in got and got[k][0].strip() for k in required)
    if not ok:
        print("[error] 关键鉴权字段缺失，保留已有 cookie 不变；请在 Chrome 重新登录后重跑。",
              file=sys.stderr)
        return 1

    out_dir = os.path.dirname(out)
    os.makedirs(out_dir, mode=0o700, exist_ok=True)
    fd, tmp_out = tempfile.mkstemp(prefix=".tb-cookie-", dir=out_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(header)
        os.chmod(tmp_out, 0o600)
        os.replace(tmp_out, out)
    finally:
        if os.path.exists(tmp_out):
            os.remove(tmp_out)
    os.chmod(out, 0o600)

    print(f"[ok] 解出 {len(got)} 条 -> {out}（{len(pairs)} 字段 / {len(header)} 字节）")
    print("[ok] 关键字段齐全：True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
