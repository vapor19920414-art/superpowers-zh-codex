# mower-tb-triage 使用说明

从 **tb.orbbec.com（Teambition）** 拉取 DLT/DMT/LXLT 等割草机项目缺陷的标题、描述、评论和日志附件，使用 `systematic-debugging` 做按需、证据驱动分析，并生成可持续修订的报告和可粘贴的 TB 评论草稿。

> 自包含：既能作为 Claude Code 技能一句话调用，也能脱离 Claude Code 直接跑脚本。整包可拷给同事。

---

## ① 快速上手

```bash
cd mower-tb-triage

# 1. 建立隔离环境并安装依赖（Ubuntu 缺 python3-venv 时也可用）
uv venv --seed --python /usr/bin/python3 --no-python-downloads ~/.local/share/mower-tb-triage/venv
uv pip install --python ~/.local/share/mower-tb-triage/venv/bin/python -r requirements.txt

# 2. 复制私有配置，填写 DLT/DMT/LXLT 等 project ID
cp config.example.json config.json

# 3. 只读检查环境
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_doctor.py

# 4. Chrome 登录 https://tb.orbbec.com/ 后，生成私有 cookie
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_cookie.py

# 5. 列缺陷
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib DLT list

# 6. 拉某个缺陷的日志
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect DLT-29
```

`tb_doctor.py` 不访问 TB；`list` 只读取缺陷列表；`defect` 只会把非视频附件写入 `log_root`，视频默认只登记元信息。

附件下载后不会自动全文加载：先清点文件/压缩包成员，再围绕时间、节点和候选根因读取最小日志片段。视频无论是否已下载，都必须先确认读取范围。

---

## ② 配置（`config.json`）

把 `config.example.json` 复制为 `config.json` 后按需改。脚本读取顺序：`config.json` → `config.example.json`。

| 字段 | 说明 | 默认值 | 多数人要改吗 |
|------|------|--------|------------|
| `chrome_profile` | Chrome profile 名（决定从哪个 Chrome 取 cookie） | `Default` | 其他 profile 按本机调整 |
| `chrome_base` | Chrome 用户数据根 | `~/.config/google-chrome` | Chromium 用户改 `~/.config/chromium` |
| `domain` | Teambition 域名 | `tb.orbbec.com` | 否 |
| `attachment_hosts` | 经人工核对后允许下载附件的额外主机名；TB 域自动允许 | `[]` | 附件实际使用外部对象存储时才改 |
| `cookie_file` | cookie 私有存储路径 | `~/.local/state/mower-tb-triage/tb.cookie` | 通常不用改 |
| `log_root` | 日志下载根目录 | `~/work/log/mower-tb-triage` | 按你的目录改 |
| `projects.DLT.pid` | RL2601 测试缺陷库 id | 占位值 | **必须填写** |
| `projects.DMT.pid` | ER2601 测试问题库 id | 占位值 | **必须填写** |
| `projects.LXLT.pid` | RL2601 罗西里项目测试缺陷库 id | 占位值 | 使用该项目时填写 |
| `projects.<库>.label/prefix` | API 缺少项目名或编号前缀时的回退值 | 按项目配置 | 建议填写 |

> `config.json`、cookie 和下载日志都属于本机私有状态，不得提交或打包分享。

---

## ③ 命令手册

所有命令在 `mower-tb-triage/` 目录下执行。`--lib` 从 `config.projects` 选择缺陷库（如 DLT/DMT/LXLT），`--pid` 可直接指定 project ID 覆盖。

### `tb_doctor.py` —— 只读检查部署环境
```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_doctor.py
```
检查 Python 与依赖、配置、Chrome cookie DB、桌面 keyring、cookie 权限、日志目录和 `systematic-debugging`。它不读取 cookie 内容，也不访问 TB。

### `tb_cookie.py` —— 生成鉴权 cookie
```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_cookie.py
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_cookie.py --profile 'Profile 2'
```
**预期输出**：
```
[ok] 解出 10 条 -> ~/.local/state/mower-tb-triage/tb.cookie（9 字段 / 1308 字节）
[ok] 关键字段齐全：True
```
> cookie 有效期约数小时～一天，失效（跑命令报 401）就重跑本命令。

### `tb_pull.py list` —— 列缺陷
```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib DLT list
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib DLT list --status all
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib DLT list --json
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib LXLT list
```
**预期输出**：
```
=== DLT 缺陷（31 条，status=open）===
ID         附件 状态 更新        标题
DLT-1        0 进行 2026-07-17  【开始割草】建图完成之后点击割草，APP 一直显示导航中...
DLT-2        0 进行 2026-07-16  【开始割草】点击开始割草，车不动...
```
> 列表里的「附件」列（`attachmentsCount`）是**陈旧缓存**，常显示 0；真实附件数以 `defect` 输出为准。

### `tb_pull.py defect` —— 拉单个缺陷（默认不下载视频）
```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect DLT-29
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect DMT-292
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect LXLT-31
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py --lib DLT defect 29
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect DLT-29 --out /tmp
# 仅在用户明确确认后下载视频；此参数不会解析视频流
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_pull.py defect DLT-29 --include-video
```
脚本流程：解析缺陷 → 提取项目 `name`/`uniqueIdPrefix` → 拉真实评论/附件 → 下载非视频附件、登记视频 → 写 `{项目名}/{前缀-编号}/{前缀-编号}_meta.json`。
**预期输出**：
```
=== DLT-29：【必现】对跨区通道中的非草地进行避障... ===
  [skip-video] RL2601_15.mp4（8,780,430 bytes，等待用户确认）
  [ok] logs_2026.07.21 (1).zip（750,465 bytes）
  [ok] 1784624631895.tar.gz（2,957,025 bytes）
[ok] 评论 2 条 / 附件 3 个 / 下载 2 个
[confirm] 1 个视频附件默认未下载；请先取得用户明确同意，再使用 --include-video。
     下一步：用 systematic-debugging 分析 <log_root>/<项目名>/DLT-29
```
`{ID}_meta.json` 含：标题 / note 描述 / 真实评论原文 / 附件清单 + 本地路径；未下载视频另记在 `deferred_videos`。附件主机必须进入白名单；外部主机不会收到 TB cookie，结构化 URL/URI/href、token 和 cookie 字段也不会写入元信息或错误输出。评论正文作为证据原样保留，不做字符串级脱敏。

视频门禁：默认不下载、播放、抽帧、转码或解析视频；即使本地已有同名视频，也要先向用户报告文件名和体积并确认本次读取范围。获准后优先按指定时间点抽取最少帧，禁止自动解析完整视频流或生成全片联系表。

### `tb_draft.py` —— 报告 → 评论草稿
```bash
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_draft.py DLT-9_分析报告.md
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_draft.py <log-root>/<项目名>/DLT-9
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python scripts/tb_draft.py DLT-9_分析报告.md --out 草稿.md
```
按「根因 / 机制 / 证据 / 置信度 / 修复」五字段切分报告，对齐 `logs_auto/DLT_评论草稿.md` 格式。
**预期输出**（节选）：
```
## 【DLT-9】地图偶现显示很小 + 点割草报"出界"，实际车在地图内
> ⚠ 本段由 tb_draft 自动从 `DLT-9_分析报告.md` 切分生成，粘贴 TB 前请人工精炼核对。
**根因**：建图保存后 SLAM 进入不稳定态...
**置信度**：根因结论（定位坐标系错误导致出界）= 高...
```
> ⚠ `tb_draft` 只做**机械切分**，不重新总结——粘贴 TB 前务必人工核对润色。

---

## ④ 完整工作流（拉 → 分析 → 复核 → 修复/草稿）

```
tb_doctor.py        只读检查本机环境
      │
tb_cookie.py        生成私有 cookie（首次/失效时）
      │
tb_pull.py list     浏览缺陷，选定 ID
      │
tb_pull.py defect   下载到 {log_root}/{项目名}/{前缀-编号}/ + 写元信息
      │
附件清单/按需取证   不全量加载日志、压缩包或视频
      │
systematic-debugging 分析日志 → {项目名}/{ID}/{ID}_分析报告.md
      │
用户复核           追问时原地更新同一报告
      │
完整/快速修复       报告获认可后复用同一 worktree
      │
tb_draft.py         报告 → 可粘贴评论草稿（人工润色后发 TB）
```

Codex CLI 没有 `/icode` 自定义命令，可用自然语言：

- “在 worktree 中分析 LXLT-11，先出报告；不要改代码。”
- “我对报告有疑问：……，更新原报告。”
- “报告没问题，按完整流程在原 worktree 修复。”
- “报告没问题，按快速流程在原 worktree 修复。”

完整流程用于跨模块、协议/状态机、安全相关或预计超过 5 个文件的改动；快速流程只用于边界明确的单模块最小修改。不确定时走完整流程。

---

## ⑤ 产物与目录约定

| 产物 | 位置 |
|------|------|
| 下载的日志附件 | `{log_root}/{项目名}/{前缀-编号}/` |
| 元信息（项目/标题/评论/附件清单） | `{log_root}/{项目名}/{前缀-编号}/{前缀-编号}_meta.json` |
| 分析报告 | `{log_root}/{项目名}/{前缀-编号}/{前缀-编号}_分析报告.md` |

---

## ⑥ 回写说明（重要）

本工具**只生成评论草稿，不自动发评论到 TB**。原因：① 发评论的 POST、鉴权、幂等和失败重试契约尚未抓包验证；② 评论会改变外部协作状态；③ 分析结论可能因用户复核继续变化，自动发布会污染工单历史。

流程：`tb_draft.py` 出草稿 → 人工核对润色 → 手动粘贴到 TB 缺陷评论。

若后续增加回写，应作为独立显式命令：默认 dry-run，先展示目标缺陷和评论全文，每次发布前单独确认，禁止由分析/修复完成自动触发，也不做隐式重试。

---

## ⑦ 分享给同事

**打包**（必须排除本机私有配置、cookie 和缓存）：
```bash
tar czf mower-tb-triage.tgz \
  --exclude='mower-tb-triage/config.json' \
  --exclude='mower-tb-triage/scripts/.tb_cookie' \
  --exclude='*/__pycache__' \
  --exclude='*.pyc' \
  --exclude='mower-tb-triage/.venv' \
  mower-tb-triage
```
**对方三步上手**：
1. 解压后创建 venv，并按 `requirements.txt` 安装依赖。
2. 复制 `config.example.json` 为 `config.json`，填写各项目的 project ID、`label`/`prefix`、profile 和日志目录；若附件使用外部对象存储，人工核对域名后加入 `attachment_hosts`。
3. Chrome 登录 tb.orbbec.com，依次运行 `tb_doctor.py`、`tb_cookie.py` 和只读 `list`。

**Claude Code + Codex CLI 共用部署：** 把实际目录放在 `~/.claude/skills/mower-tb-triage`，再建立：

```bash
ln -s ~/.claude/skills/mower-tb-triage ~/.codex/skills/mower-tb-triage
```

重新启动 Codex 会话后，用 `codex exec "列出你的 skills，确认 mower-tb-triage 的路径"` 验证发现结果。不要让 `~/.codex/skills/mower-tb-triage` 和源目录形成循环软链。

---

## ⑧ 排错速查

| 现象 | 处理 |
|------|------|
| `401 鉴权失败` / cookie 过期 | Chrome 重登 tb.orbbec.com → 重跑 `tb_cookie.py` |
| `[error] 找不到 cookie DB` | 改 `chrome_profile`；或 `--base` 指定 Chrome 数据根（如 `~/.config/chromium`） |
| `keyring 取密钥失败` | 多数会自动回退仍可用；若失败确认 `secretstorage` 已装、在图形登录会话里跑 |
| 纯数字缺陷 ID 匹配到错误库 | 显式使用 `--lib DLT defect 29`；不指定时默认按 DLT 查找 |
| 产物落入纯数字目录 | 使用新版脚本；确认项目 API 返回 `name`/`uniqueIdPrefix`，或在 `config.projects` 配置 `label`/`prefix` |
| 找不到某缺陷 | 用 `list --status all` 看是否已完成；确认 uniqueId 正确 |
| 附件下载失败 | token 过期会自动刷新重试一次；仍失败检查网络/cookie |
| `附件主机未列入 attachment_hosts` | 核对 URL 主机确属受信任对象存储后，只把该主机名加入 `attachment_hosts` |
| 视频显示 `[skip-video]` | 正常门禁；先征得用户明确同意，再用 `--include-video` 下载，随后按确认范围读取 |

---

## ⑨ 文件结构

```
mower-tb-triage/
├── SKILL.md              # Claude Code 技能编排（给 AI 看）
├── README.md             # 本文件（给人看）
├── references/
│   └── analysis-workflow.md # 按需日志分析、报告迭代和 worktree 复用约束
├── requirements.txt      # 隔离 Python 环境依赖
├── config.example.json   # 配置模板 → 复制为 config.json
├── .gitignore            # 排除私有配置、cookie、venv 和 pyc
└── scripts/
    ├── tb_doctor.py      # 只读检查部署环境
    ├── tb_cookie.py      # 解密 Chrome cookie → 私有状态目录
    ├── tb_pull.py        # 拉缺陷：list / defect
    └── tb_draft.py       # 报告 → 评论草稿骨架
```
