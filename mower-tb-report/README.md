# mower-tb-report 使用说明

测试同学**现场复现问题后上报 TB** 的一键工具：登设备拉日志 → 按规范模板写问题描述 → 在 **LXLT 缺陷库**创建缺陷（自动归入【缺陷】场景并填必填字段）→ 挂日志附件 → 做初步分析。

> 自包含：既能作为 Claude Code 技能一句话调用，也能脱离 Claude Code 直接跑脚本。整包可拷给同事。

---

## ① 快速上手（30 秒跑通）

```bash
cd mower-tb-report

# 1. 装依赖
pip install requests cryptography secretstorage

# 2. 复制配置并改默认值（仅一个 Chrome profile 时会自动回退）
cp config.example.json config.json

# 3. Chrome 登录 https://tb.orbbec.com/ 后，生成 cookie
python3 scripts/tb_cookie.py          # 看到「关键字段齐全：True」即成功

# 4. 拉设备日志（当天，全关键节点）
bash scripts/pull_device_logs.sh 2026-08-23 ./device_logs_20260823

# 5. 先预览要建的缺陷（不真正创建）
python3 scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
    --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
    --version v0.0.2 --time "2026-08-23 16:53" --dry-run

# 6. 真正创建 + 挂日志附件
python3 scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
    --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
    --version v0.0.2 --attach device_logs_20260823.tgz
```

跑通后，缺陷会出现在 TB 的 `/bug/section/all` 视图。下面是细节。

---

## ② 为什么必须用这个工具（踩坑记录）

| 坑 | 后果 | 本工具怎么避免 |
|----|------|----------------|
| 建在【任务】场景 | 缺陷 API 里有、直链能打开，但 **`/bug/section/all` 缺陷视图永远看不到**；且场景创建后不可改，只能删掉重建 | `tb_create.py` 固定写死【缺陷】场景（`scenario_defect`） |
| 漏填缺陷必填字段 | 缺陷不完整、视图展示异常 | 自动填 6 个必填字段（版本/测试人员/严重等级/缺陷模块/缺陷分类/设备序列号） |
| 手工拼 customfields 格式 | 创建报错或字段不生效 | 脚本已封装正确格式 |

---

## ③ 配置（`config.json`）

把 `config.example.json` 复制为 `config.json` 后按需改。脚本读取顺序：`config.json` → `config.example.json`。

| 字段 | 说明 | 默认值 | 多数人要改吗 |
|------|------|--------|------------|
| `chrome_profile` | Chrome profile 名（决定从哪个 Chrome 取 cookie） | `Profile 1` | **常需改**：你的可能是 `Default` / `Profile 2` |
| `chrome_base` | Chrome 用户数据根 | `~/.config/google-chrome` | Chromium 用户改 `~/.config/chromium` |
| `log_root` | 日志下载根目录 | `/home/tudou/work/log` | 按你的目录改 |
| `defaults.tester` | 默认测试人员（名字或 `_userId`） | `佛印` | 改成本人 |
| `defaults.module/severity/type` | 缺陷默认字段 | 业务软件 / Normal / 功能 | 按习惯改 |
| `firmware_tb_version_map` | 可选的“现场固件 → TB 版本字段”白名单 | 空 | 有可靠映射再登记；未登记时仍须显式传 `--version` |

> `--profile` 明确指定时绝不猜测；未指定且配置的 profile 不存在、机器上又只发现一个 profile 时，`tb_cookie.py` 本次自动回退并打印警告。其余情况会列出可用 profile，要求人工选择。

---

## ④ 命令手册

### `tb_cookie.py` —— 生成鉴权 cookie
```bash
python3 scripts/tb_cookie.py                    # 用 config 里的 profile
python3 scripts/tb_cookie.py --profile Default  # 临时换 profile
```
cookie 有效期约数小时～一天，失效（跑命令报 401）就重跑。

### `pull_device_logs.sh` —— 从设备拉日志
```bash
bash scripts/pull_device_logs.sh                                # 今天，默认 4 节点
bash scripts/pull_device_logs.sh 2026-08-23 ./dl                 # 指定日期
bash scripts/pull_device_logs.sh 2026-08-23 ./dl mission_controller_node broker_node map_service_node   # 指定节点
```
自动含最近的 coredump。设备地址 `10.5.5.1`（需先接入设备所在局域网，`ping -c2 10.5.5.1` 通再跑）。

### `tb_create.py` —— 创建缺陷（核心）
```bash
# 预览（推荐先跑；现场固件和 TB 版本字段是两个值）
python3 scripts/tb_create.py --title "TITLE" --desc 描述.md --device SN --firmware FW --version TB_VERSION --time T --dry-run

# 创建（默认：严重 Normal / 模块 业务软件 / 分类 算法 / 类型 功能 / 测试人员=config.defaults.tester）
python3 scripts/tb_create.py --title "TITLE" --desc 描述.md --device SN --firmware FW --version TB_VERSION --time T

# 创建 + 挂附件（--attach 可多次）
python3 scripts/tb_create.py --title "TITLE" --desc 描述.md --device SN --firmware FW --version TB_VERSION \
    --attach device_logs_20260823.tgz --attach 现场图.png

# SshFileDownloader 本地日志目录（根目录唯一 .tar.gz/.tgz 会自动作为附件）
LOG_DIR=/work/work_new/RL2601/tuya/TB/SshFileDownloader-20260828/file/20260831_190603
python3 scripts/tb_create.py --title "TITLE" --desc "$LOG_DIR/E11后面板恢复规控异常_描述.md" \
    --device SN --firmware FW --version TB_VERSION --log-dir "$LOG_DIR"

# 覆盖字段 / 描述走文本
python3 scripts/tb_create.py … --severity Major --module 感知算法 --type 性能 --tester 土豆
python3 scripts/tb_create.py … --desc-text "【现象】…" --receipt ./xxx.tb-receipt.json
```
参数速查：

| 参数 | 必填 | 说明 |
|------|------|------|
| `--title` | ✅ | 标题，如 `【建图】xxx` |
| `--desc` / `--desc-text` | ✅ 二选一 | 问题描述（推荐 `--desc 文件`，模板见 `templates/问题描述模板.md`） |
| `--device` | ✅ | 设备序列号（必填自定义字段） |
| `--firmware` | 建议 | 现场固件版本；给了它就必须同时显式给 `--version/--tb-version` |
| `--time` | 建议 | 发生时间 |
| `--severity` | | blocker/Critical/Major/Normal/Enhancement |
| `--module` | | 硬件/结构/SOC固件/MCU/业务软件/APP/感知算法/定位算法/规控算法/RGB图像/深度图像 |
| `--category` | | 缺陷分类（commongroup） |
| `--type` | | 功能/界面/兼容/安全/性能/建议/其他 |
| `--version` / `--tb-version` | 给了 `--firmware` 时 ✅ | TB 自定义字段版本，须是 config 登记的选项；不能由默认值静默代填 |
| `--tester` | | 测试人员（名字或 `_userId`） |
| `--attach` | | 附件路径，可多次 |
| `--log-dir` | | 本地日志目录，可多次；根目录须恰有一个 `.tar.gz`/`.tgz` 日志包，脚本只挂该归档，不会上传整份原始目录 |
| `--comment` | | 附件评论文字（默认模板文案） |
| `--receipt` | `--desc-text` 真创建时 ✅ | 创建收据路径；使用 `--desc` 时默认写为 `<描述文件>.tb-receipt.json` |
| `--resume-attachments` | | 只继续收据内未完成附件，绝不重新创建任务 |
| `--adopt-task` | | POST 结果不明时，人工确认已有 TB 后配合 `--resume-attachments` 绑定 `LXLT-N`/task id |
| `--dry-run` | | 只预览不创建 |

**收据与断点续传**：真创建会先以 `0600` 原子写入收据，POST 成功后立即记录 task id，随后回读校验缺陷场景和自定义字段，再上传并回读附件。再次执行同一参数时默认只提示已有任务，不会再 POST；附件失败后确认收据对应的任务，使用原命令加 `--resume-attachments` 继续。若 POST 超时且 task id 未知，先到 TB 人工确认，再显式使用 `--adopt-task LXLT-N --resume-attachments`，脚本不会自动猜测或重复建单。

**本地下载目录**：例如 `SshFileDownloader.../file/20260831_190603` 常同时含原始 `userdata/` 和已整理的“关键日志”归档。传 `--log-dir` 时只扫描该目录第一层，且只接受唯一 `.tar.gz`/`.tgz`；没有或存在多个归档会拒绝，避免误传数百 MiB 原始日志、配置或地图数据。

**成功输出**：
```
[ok] 已创建 LXLT-49：…
[ok] 直链: https://tb.orbbec.com/project/6a86a99a05fe46110bd2cefe/task/…
[ok] 缺陷视图应可见: https://tb.orbbec.com/project/6a86a99a05fe46110bd2cefe/bug/section/all
```

### `tb_pull.py` —— 列缺陷 / 发评论（复用 tb-triage）
```bash
python3 scripts/tb_pull.py --lib LXLT list                      # 列 LXLT 缺陷
python3 scripts/tb_pull.py --lib LXLT comment LXLT-49 -t "文字" -a 文件   # 发评论+附件
```

---

## ⑤ 问题描述格式（`templates/问题描述模板.md`）

**必填小节：【现象】【复现步骤】【设备信息】**——缺任一 `tb_create.py` 会拒绝创建。
**【复现步骤】必须写全五要素**：前置条件（机器/地图/APP 状态）→ 操作步骤（一步步、点到按钮/菜单/参数）→ 触发点（哪一步后问题出现）→ 复现概率（必现/偶现，n/m）→ 预期 vs 实际。

```
【现象】
- 一句话说清"发生了什么、用户感知是什么"

【复现步骤】
- 前置条件：
  1. 机器状态（如：已完成建图并保存 / 停在桩上 / 电量）
  2. 地图状态（如：已有 2 区域 + 1 禁区）
  3. APP 环境（版本/平台）
- 操作步骤：
  1. 具体操作（点到按钮/菜单路径）
  2. 具体操作（带参数，如：删除禁区 A）
  3. …直到问题出现
- 触发点：点击保存后，APP 报「指令执行超时」
- 复现概率：必现（3/3）
- 预期 vs 实际：预期保存成功退出；实际保存超时卡死

【设备信息】
- 机器: RL601CK20ENS267E0001
- 固件: V1.3.8_RN2601_DEV_20260819-1019
- 发生时间: 2026-08-23 16:53

【日志证据】（可选但强烈建议）
- 16:53:47 [NavApiLifecycleGuard] timed out waiting for exclusive nav operation: …

【初步分析】（可选）
- 根因推测 + 依据 + 置信度

【期望行为】
- 问题不发生时应如何
```

---

## ⑥ 分享给同事

**打包**（排除你的个人 cookie / 配置）：
```bash
cd /path/to
tar czf mower-tb-report.tgz --exclude='scripts/.tb_cookie' --exclude='config.json' --exclude='__pycache__' mower-tb-report
```
**对方三步上手**：
1. 解压后 `cd mower-tb-report && pip install requests cryptography secretstorage`
2. `cp config.example.json config.json`，改 `chrome_profile`、`log_root`、`defaults.tester`
3. Chrome 登录 tb.orbbec.com → `python3 scripts/tb_cookie.py` → 开跑

> Claude Code：把目录拷到 `~/.claude/skills/`。Codex：将同一目录软链接到 `~/.codex/skills/mower-tb-report`，重启/新开会话后即可发现。

---

## ⑦ 排错速查

| 现象 | 处理 |
|------|------|
| `401 鉴权失败` / cookie 过期 | Chrome 重登 tb.orbbec.com → 重跑 `tb_cookie.py` |
| `找不到 cookie DB` | 未显式指定 profile 且仅有一个时会自动回退；否则改 `chrome_profile`，或 `--base` 指定 Chrome 数据根 |
| `创建失败 400` | 先 `--dry-run` 看 body；确认 `--device` 给了、`--module` 等在选项里 |
| 缺陷在 `/bug/section/all` 看不到 | 确认是 `tb_create.py` 建的（固定缺陷场景）；直链能开但视图没有=场景不对 |
| 连不上设备 | `ping -c2 10.5.5.1`，先接入设备所在局域网 |
| 附件没挂上/命令中断 | 查看同目录 `.tb-receipt.json`；确认 task 后用**原参数**加 `--resume-attachments`，不要重新执行创建命令 |

---

## ⑧ 文件结构

```
mower-tb-report/
├── SKILL.md                  # Claude Code 技能编排（给 AI 看）
├── README.md                 # 本文件（给人看）
├── config.example.json       # 配置模板 → 复制为 config.json
├── .gitignore                # 排除个人 cookie / pyc
├── templates/
│   └── 问题描述模板.md         # 问题描述规范格式
└── scripts/
    ├── tb_create.py          # 创建缺陷（核心）：缺陷场景 + 必填字段 + 附件
    ├── tb_cookie.py          # 解密 Chrome cookie → .tb_cookie
    ├── tb_pull.py            # 列缺陷 / 发评论（复用）
    ├── tb_draft.py           # 分析报告 → 评论草稿（复用）
    └── pull_device_logs.sh   # 设备日志 → 本地
```
