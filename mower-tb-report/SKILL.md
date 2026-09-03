---
name: mower-tb-report
description: 测试同学现场复现问题后一键上报 TB 缺陷：登设备拉日志 → 按规范模板写问题描述 → 在 LXLT 缺陷库创建缺陷（自动归入【缺陷】场景并填必填字段）→ 挂日志附件 → 做初步分析。当用户提到——报缺陷、上报 TB、建缺陷、提缺陷、创建TB问题、在TB上新增问题、把这个问题记录到TB、拉设备日志后建TB、LXLT缺陷库、/bug/section/all 看不到——都必须使用本技能。和 mower-tb-triage（拉已有缺陷日志）、mower-device-access（只登设备看日志）、mower-log-analysis（深入根因分析）互补：本技能是「创建/上报方向」。
---

# 割草机缺陷上报（拉日志 → 写描述 → 建 TB 缺陷 → 初析）

本技能把「现场复现问题后上报到 TB」串成一条可复用链路，面向**测试同学**：

```
登设备拉日志  →  按模板写问题描述  →  tb_create.py 建缺陷（缺陷场景+必填字段）  →  挂日志附件  →  初步分析
```

底层脚本与 `mower-tb-triage` 同源（cookie 鉴权），整包可拷给同事。

---

## 0. 输入契约

| 要素 | 说明 | 缺失时处理 |
|------|------|-----------|
| **缺陷库** | 默认 `LXLT`（RL2601-罗西里项目测试缺陷管理库，pid `6a86a99a05fe46110bd2cefe`） | 用户没指定就默认 LXLT |
| **问题描述** | 标题 + 描述（现象/复现步骤/设备信息…） | 引导用户提供；模板见 `templates/问题描述模板.md` |
| **设备日志** | 现场从设备拉，或 SshFileDownloader 本地下载目录 | 设备不在线则要求日志文件/目录；目录须含唯一关键归档及 `userdata.zip` 或 `userdata/` |

---

## 1. 权限边界

- **可写**：本技能目录（`config.json`、下载/打包的日志）、`log_root`。
- **创建缺陷到 TB**：已打通且**对外不可逆**（团队可见）。创建前先 `--dry-run` 给用户看标题/描述/字段，确认后再真正创建。
- 发评论/附件：`tb_create.py --attach` 自动完成；文字默认模板文案，可用 `--comment` 改。真创建会落 `0600` 收据，遇到附件失败默认不重建任务，只能由用户确认后显式 `--resume-attachments`。
- `--log-dir` 同时上传关键包和完整 `userdata.zip`；目录只有 `userdata/` 时**自动生成关键包**并**自动压缩**（设备 mtime=0 会钳位到 1980，不再崩溃），上传并回读确认后删除自动生成包。已有 `userdata.zip` 不删除，上传失败时保留自动生成包供续传。
- **版本自动登记**：`tb_create.py` 传未登记的 `--version` 时，会从项目任务自动反查 label→id 并写入 config.json（本技能目录，可写）；TB 无“列版本”API，只能发现“已用过的版本”，全新版本需先在 TB 创建版本对象。
- 旧收据继续使用收据内原附件清单，不自动追加完整包，避免破坏既有任务的 fingerprint 与断点续传。

---

## 2. 核心知识（务必先读，三个最容易踩的坑）

### 2.1 场景决定可见性 —— 必须建在【缺陷】场景

`/bug/section/all` 缺陷视图**只展示【缺陷】场景**（`scenariofieldconfigId=…47ee`）的任务。
建在【任务】场景（`…47e1`）的缺陷：API 列表里有、直链能打开，但**缺陷视图永远看不到**。

- **场景在创建后无法修改**（`PUT /api/v2/tasks/{tid}` 会忽略 `_scenariofieldconfigId`），只能删掉重建。
- 所以**创建时必须选对场景** —— `tb_create.py` 已固定用 `scenario_defect`，不要手工用其它方式建。
- 判断某任务是否可见：查任务详情 `_scenariofieldconfigId == 6a86a99a533b9c6279ec47ee`。

### 2.2 【缺陷】场景有 6 个必填自定义字段

版本（lookup 整机版本）、测试人员（lookup 成员）、严重等级（下拉）、缺陷模块（下拉）、缺陷分类（commongroup）、设备序列号（text）。`tb_create.py` 会自动填，但：
- `--device` 必填（设备序列号 = 必填字段）。
- 选项名来自 config `customfields.*.choices`；**版本**未登记时会自动从项目任务反查并登记（见 3.3 与 `tb_version.py`），其它字段未登记仍报错并列出可用项。
- **现场 `--firmware` 与 TB 的 `--version/--tb-version` 是不同字段**。只要填写现场固件，就必须显式填写已登记的 TB 版本；若配置了 `firmware_tb_version_map`，两者还必须匹配。不可用 `defaults.version` 猜测。

### 2.3 设备日志位置（10.5.5.1）

```
/userdata/log/<node>/{daily,boot}/
  daily/<node>_YYYY-MM-DD.log     # 按天滚动（大日志有 .1.log .2.log 分卷）
  boot/boot_YYYYMMDD_HHMMSS_*.log # 每次开机一份
/userdata/log/coredump/core-*     # 崩溃（mtime=崩溃时间）
/userdata/config/version          # 固件版本
```
常用节点：`mission_controller_node`（任务/建图/导航租约/锁）、`broker_node`（启动/指令）、`map_service_node`（地图几何）、`shell_node`（复位/电量）、`mcu_communication_node`（MCU 异常码）、`tuya_communication_node`（APP 通道）、`hmi`（按键）。
⚠️ 别用 `find / -xdev`（日志在独立 `/userdata` 挂载）。

---

## 3. 工作流

### 3.0 前置：cookie（首次或 401 时）

```bash
# Chrome 先登录 https://tb.orbbec.com/，然后：
python3 <skill>/scripts/tb_cookie.py          # 输出「关键字段齐全：True」即成功
```

未显式传 `--profile` 时，若配置 profile 不存在且本机只发现一个可用 profile，脚本会打印警告并仅对本次回退；`--profile` 明确指定时绝不自动替换。

### 3.1 拉设备日志（现场）

```bash
# 全节点某天（默认今天，自动含 coredump）
bash <skill>/scripts/pull_device_logs.sh 2026-08-23 ./device_logs_20260823

# 只拉关键节点
bash <skill>/scripts/pull_device_logs.sh 2026-08-23 ./dl mission_controller_node broker_node map_service_node
```

### 3.2 写问题描述（规范格式）

复制 `templates/问题描述模板.md` 为 `描述.md` 填写。**必填小节：【现象】【复现步骤】【设备信息】**——缺任一 `tb_create.py` 会拒绝创建。
**【复现步骤】是开发复现的最重要输入，必须写全五要素**：
1. **前置条件**：机器/地图/APP 环境状态（如「已完成建图并保存、停在桩上、APP v1.2.3」）；
2. **操作步骤**：一步一步、点到具体按钮/菜单路径、带关键参数（如「地图编辑 → 删除禁区 A → 保存地图」）；
3. **触发点**：哪一步之后问题出现；
4. **复现概率**：必现/偶现（n/m 次）；
5. **预期 vs 实际**：应发生什么 vs 实际发生什么。
建议填：【日志证据】（关键节点+时间+日志行）、【初步分析】、【期望行为】。
标题规范：`【模块】一句话现象，含关键信息（时间/操作）`，如 `【地图编辑】重定位中删除禁区并保存地图，APP指令执行超时，无法取消/退出编辑`。

### 3.3 创建缺陷（先 dry-run，确认后真建）

```bash
# 预览（不真正创建）
python3 <skill>/scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
    --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
    --version v0.0.2 --time "2026-08-23 16:53" --dry-run

# 真正创建（默认：严重 Normal / 模块 业务软件 / 分类 算法 / 类型 功能 / 版本 v0.0.2 / 测试人员=config.defaults.tester）
python3 <skill>/scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
    --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
    --version v0.0.2 --time "2026-08-23 16:53"

# 创建 + 挂日志附件（--attach 可多次）
python3 <skill>/scripts/tb_create.py --title "【建图】xxx" --desc 描述.md \
    --device RL601CK20ENS267E0001 --firmware "V1.3.8_RN2601_DEV_20260819-1019" \
    --version v0.0.2 --attach device_logs_20260823.tgz --attach 现场图.png

# 本地 SshFileDownloader 目录：上传唯一关键日志归档 + 完整 userdata.zip
LOG_DIR=/work/work_new/RL2601/tuya/TB/SshFileDownloader-20260828/file/20260831_190603
python3 <skill>/scripts/tb_create.py --title "【规控算法】xxx" \
    --desc "$LOG_DIR/E11后面板恢复规控异常_描述.md" \
    --device RL601CK20ENS267E0009 --firmware 1.3.9 --version v0.0.2 \
    --log-dir "$LOG_DIR"

# 覆盖默认字段 / 描述走 --desc-text
python3 <skill>/scripts/tb_create.py … --severity Major --module 感知算法 --type 性能 --tester 土豆 --version v0.0.2
python3 <skill>/scripts/tb_create.py … --desc-text "【现象】…" --receipt ./xxx.tb-receipt.json
```

真创建时，`--desc` 默认生成 `<描述文件>.tb-receipt.json`：POST 成功立即记录 task id，回读验证缺陷场景/自定义字段，再上传并回读附件。**同一收据再次运行默认不会再 POST**；附件失败后先让用户确认收据里的 TB，再使用原参数加 `--resume-attachments`。POST 结果不明时，先人工在 TB 确认，再用 `--adopt-task LXLT-N --resume-attachments` 绑定；不得自动猜测或重复建单。

脚本成功输出：`LXLT-{n}`、直链、缺陷视图地址（`/bug/section/all`）和收据路径。

### 3.4 验证可见性（可选）

```bash
# 查任务详情，确认 _scenariofieldconfigId == 缺陷场景 id
#（tb_create.py 固定写死 scenario_defect，正常不会错；出问题先查这步）
```

### 3.5 初步分析（本技能内轻量做）

测试同学级别初析 = 从【日志证据】里找"第一处异常"和"机制"：
1. 在拉回的日志里按时间线定位异常起点（`grep -nE "level (ERROR|FATAL)|timed out|failed to|exception"`）；
2. 关联用户操作时间点 → 异常日志时间点；
3. 写【初步分析】小节（根因推测 + 依据 + 置信度）。
深入根因（多轮对抗分析、修复建议）交给 **mower-log-analysis** 技能，结论再发回 TB 评论（`tb_pull.py --lib LXLT comment`）。

---

## 4. 脚本说明

| 脚本 | 职责 | 关键点 |
|------|------|--------|
| `scripts/tb_create.py` | **创建缺陷**（核心） | 固定【缺陷】场景 + 自动填 6 必填字段 + 创建后回读校验 + 收据断点续传；`--log-dir` 同传关键包和完整包，`--dry-run` 预览 |
| `scripts/tb_cookie.py` | 解密 Chrome cookie → `.tb_cookie` | Chrome 149 / cookie DB v24；显式 profile 严格，配置失效且仅一个 profile 时自动回退 |
| `scripts/tb_pull.py` | 列缺陷 / 发评论（复用） | `--lib LXLT list` 列缺陷；`--lib LXLT comment LXLT-n -t … -a …` 发评论+附件 |
| `scripts/tb_version.py` | TB 版本发现 / 登记 | `list` 列项目已用版本；`register <label>` 登记；`sync` 全量登记；`tb_create.py` 遇未登记版本自动调用 |
| `scripts/tb_draft.py` | 分析报告 → 评论草稿（复用） | 切分五段（根因/机制/证据/置信度/修复） |
| `scripts/pull_device_logs.sh` | 设备日志 → 本地 | 免密 SSH 10.5.5.1；按日期/节点；含 coredump |

---

## 5. 接口知识（脚本已封装，排错时用）

- **创建**：`POST /api/v2/tasks`，body `{content, note, _projectId, _tasklistId, _stageId, _scenariofieldconfigId, customfields}`。customfields 值格式：lookup 用 `{"_id":…}`，dropDown/commongroup 用 `{"_id":…}`，text 用 `{"title":…}`。
- **成员解析**：`GET /api/projects/{pid}/members` → `name` + `_userId`（测试人员取值用 `_userId`）。
- **场景配置**：`GET /api/scenariofieldconfigs/{id}` → 必填字段与选项定义。
- **附件**：① `POST /api/awos/upload-token`（body `{scope:"task:<tid>",category:"attachment",fileName,fileType,fileSize}`，scope 必须是 `task:<tid>` 完整串）→ ② AWS SigV4 PutObject → ③ `POST /api/v2/tasks/{tid}/activities` body `{content,attachments:[],fileTokens:[token],dingFiles:[],renderMode:"text",isOnlyNotifyMentions:false,mentions:{},mentionedTeams:[],mentionedGroups:[],isDingtalkPM:true}`（字段必须带全）。
- **更新任务**：`PUT /api/v2/tasks/{tid}`（改 note/content 需要带 `note` 字段否则报 NoContent）；**改场景无效**。标记完成：`PUT /api/tasks/{tid}` body `{"isDone":true}`。

---

## 6. 收尾 / 分享

- 建完缺陷把直链发给用户，提示刷新 `/bug/section/all` 确认可见。
- 分享给同事：整目录拷走（排除 `scripts/.tb_cookie`、`config.json`），对方 `cp config.example.json config.json` 改 `chrome_profile`/`log_root` 后即可用。
- Codex 注册：`ln -s <skill目录> ~/.codex/skills/mower-tb-report`；新开会话后由 `mower-tb-report` 名称/语义自动发现。
