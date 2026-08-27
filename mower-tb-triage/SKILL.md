---
name: mower-tb-triage
description: Use when 用户要求从 tb.orbbec.com 或 Teambition 的 DLT/DMT/LXLT 等割草机缺陷库列问题、拉缺陷详情、评论或日志附件，或基于这些材料分诊缺陷；不用于普通代码缺陷或其他工单系统。
---

# 割草机 TB 缺陷拉取与分诊

从 tb.orbbec.com 读取割草机项目缺陷及附件，用 `systematic-debugging` 重建证据链并生成可持续修订的本地分析报告。脚本只封装读取和草稿处理，不提供 TB 评论回写。

**必需子技能：** 下载材料后使用 `systematic-debugging` 完成根因调查、候选区分和证据分级。

**按需参考：** 开始读取附件、生成/修订报告或从报告转入修复前，必须阅读 [references/analysis-workflow.md](references/analysis-workflow.md)。需要隔离代码工作区时使用 `using-git-worktrees`；复杂修复先使用 `writing-plans`。

---

## 0. 输入契约

| 要素 | 说明 | 缺失时处理 |
|------|------|-----------|
| **缺陷库** | 如 `DLT`、`DMT`、`LXLT`；映射来自 `config.projects` | 用户指定；默认 `DLT` |
| **缺陷标识** | 如 `DLT-29`，或纯 uniqueId `29`（配 `--lib`） | 先 `list` 查 |

---

## 1. 权限边界

- **允许**：按用户指定的 `config.projects` 项目范围执行 TB 只读查询；向 `config.log_root` 下载非视频附件并写元信息、分析报告和草稿。
- **凭据隔离**：cookie 只写 `config.cookie_file`，权限必须为 `0600`；不得读取、打印、复制或提交其值。
- **附件域隔离**：TB cookie 只绑定 `config.domain`；附件 URL 的主机必须是 TB 域名或经人工核对后加入 `attachment_hosts`，外部附件主机不携带 TB cookie。
- **不自动发评论到 TB**：发评论的 POST 接口尚未抓包确认，且属对外发布动作；只生成本地草稿，人工核对后粘贴。
- **禁止扩大范围**：未获用户明确授权时，不批量下载附件，不探测其他 project ID，不修改 TB 状态。
- **附件按需加载门禁**：下载完成不等于获准全量读取。先列清单、大小、类型、时间范围和压缩包成员，只围绕当前假设读取最小日志片段；禁止递归全文读取、整包灌入上下文或直接 `cat` 大日志。
- **视频确认门禁**：发现视频时只登记文件名、MIME、大小等元信息，禁止自动下载、播放、抽帧、转码或解析；本地已有视频也不代表已获本次读取授权。
- **报告确认门禁**：分析报告交给用户检查前不得修改业务代码。用户质疑结论或补充事实时，更新同一份报告并保留增量记录；只有用户明确认可报告并要求修复后才能进入代码修改。
- **工作区复用门禁**：若分析已绑定 worktree，后续修复必须校验并复用报告中的同一 worktree；禁止静默创建第二个工作区或改到主工作区。
- **工作区生命周期门禁**：只读分析默认不创建 worktree；仅在用户明确要求隔离，或获准修复且当前工作区不适合直接修改时创建，并在报告记录“本任务创建/既有工作区”。交付前审计本任务创建的 worktree：仅当工作树干净、分支无独有提交、预期成果已进入目标仓库时，用 `git worktree remove` 和 `git branch -d` 收尾；否则保留并报告原因。多仓项目必须按报告列出的业务子仓从内到外逐层审计，顶层干净不代表嵌套仓干净。禁止批量 `prune`、删除既有/归属不明 worktree，或用强制删分支绕过检查。

---

## 2. 工作流

```
1. doctor   （首次部署）      tb_doctor.py        → 只读检查环境
2. cookie   （首次或失效时）  tb_cookie.py        → 生成私有 cookie
3. 列缺陷                     tb_pull.py list      → 选目标
4. 拉材料                     tb_pull.py defect    → 按 项目名/前缀-编号 保存
5. 清单与取证                  按需读取              → 不全量加载日志/压缩包
   视频确认（按需）            先询问用户            → 明确同意后才下载/读取
6. 分析      （systematic-debugging）               → {ID}_分析报告.md
7. 用户复核                    原地增量更新报告       → 明确认可前不改代码
8. 修复分流  （按需）          完整/快速              → 复用同一 worktree
9. 草稿      （可选）          tb_draft.py           → 可粘贴评论
10. 收尾      （交付前）        worktree 生命周期审计  → 清理本任务无残留工作区
```

具体命令（`<skill-dir>` 为当前 `SKILL.md` 所在目录；清理 ROS 注入的 `PYTHONPATH` 后使用隔离 Python）：

```bash
# 1) 环境检查（不访问 TB）
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_doctor.py

# 2) cookie（首次或 401 时；值不会打印）
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_cookie.py

# 3) 列缺陷
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py --lib DLT list
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py --lib DLT list --status all
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py --lib LXLT list

# 4) 拉单个缺陷：详情 + 真实评论 + 下载非视频附件
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py defect DLT-29
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py defect LXLT-31

# 用户明确同意下载该视频后才可执行；该参数只下载，不解析视频流
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_pull.py defect DLT-29 --include-video

# 5) 分析：先读 references/analysis-workflow.md，再使用 systematic-debugging
# 按需分析 {log_root}/{项目名}/DLT-29/，输出并持续更新 DLT-29_分析报告.md。

# 6) 草稿（可选）：把报告切分成可粘贴评论
env -u PYTHONPATH PYTHONNOUSERSITE=1 ~/.local/share/mower-tb-triage/venv/bin/python <skill-dir>/scripts/tb_draft.py <log-root>/<项目名>/DLT-29/DLT-29_分析报告.md --out <log-root>/草稿.md
```

`defect` 从 `/api/projects/{pid}` 提取项目名和 `uniqueIdPrefix`，把材料保存到 `{config.log_root}/{项目名}/{前缀}-{uniqueId}/`，并写 `{前缀}-{uniqueId}_meta.json`。不得退化为纯数字目录；API 字段缺失时才使用 `config.projects` 的 `label`/`prefix` 回退。视频附件默认进入 `deferred_videos`，不下载。元信息保留项目身份、标题、note、评论和附件摘要，但移除结构化 URL/URI/href、token、cookie 等鉴权字段；评论正文作为证据原样保留，不做字符串级脱敏。

遇到视频时，先向用户报告视频数量、文件名和已知体积，并询问是否下载及需要查看的范围。只有明确同意后才能使用 `--include-video`。即使获准下载，也禁止默认解析完整视频流或批量生成全片联系表；优先按用户指定的时间点/现象抽取最少帧。只有用户明确要求完整视频分析时，才扩大读取范围。

日志和压缩包也受按需门禁约束：先做文件/成员清单和大小统计，再根据缺陷时间、节点及候选机制筛选；每次只取能证实或排除一个假设的最小片段，并在报告中记录扩展读取的理由。用户要求“全部看一下”、附件数量很少或文件已经下载，均不构成把全部内容加载进上下文的理由。

Codex CLI 不使用 `/icode log|start|fast`。等价自然语言是：

- “在 worktree 中分析 LXLT-11，先出报告”——只分析并绑定工作区；
- “报告没问题，按完整流程在原 worktree 修复”——跨模块、协议/状态机、安全相关或边界不清；
- “报告没问题，按快速流程在原 worktree 修复”——单模块、边界明确、沿用现有实现且预计不超过 5 个相关文件。

两种修复模式都必须先取得报告认可，并复用报告记录的工作区。复杂度不确定时走完整流程；两者均不自动 commit、push、部署、改 TB 状态或发评论。

用户明确授权 commit 时，每个属于当前 TB 缺陷的原子提交都必须在 subject 末尾附缺陷标识，格式为 `(<PREFIX>-<ID>)`，例如 `fix(<scope>): <summary> (LXLT-70)`。提交语言及其余格式沿用目标 Git 根的历史和相应 commit convention；跨多个 Git 根时分别提交并携带同一标识，无关改动不得带入或复用该标识。

---

## 3. 脚本说明

| 脚本 | 职责 | 关键点 |
|------|------|--------|
| `scripts/tb_doctor.py` | 只读环境检查 | 检查 Python、依赖、配置、Chrome profile、keyring、私有路径和 `systematic-debugging` |
| `scripts/tb_cookie.py` | 解密 Chrome cookie → 私有 cookie 文件 | Chrome 149 / cookie DB v24 方案；原子写入并强制 `0600` |
| `scripts/tb_pull.py` | 拉缺陷 | `list` 列缺陷；`defect <ID>` 拉详情+评论+非视频附件；`--include-video` 仅在用户确认后使用 |
| `scripts/tb_draft.py` | 报告 → 评论草稿骨架 | 切分根因/机制/证据/置信度/修复，顶部标注待人工精炼 |
| `config.example.json` | 可分享配置模板 | project ID 使用占位值；复制为忽略跟踪的 `config.json` 后填写 |

---

## 4. 接口知识（脚本已封装，备查 / 排错时用）

- **列缺陷**：`GET /api/projects/{pid}/tasks?isDone=false&count=300` → 直接返回数组；字段 `_id`/`uniqueId`/`content`/`note`/`attachmentsCount`/`isDone`。
- **项目身份**：`GET /api/projects/{pid}` → `name` 用作项目目录，`uniqueIdPrefix` 与 task `uniqueId` 组成缺陷目录；配置中的 `label`/`prefix` 仅作缺字段回退。
- **`commentsCount` 是陈旧缓存**（常显示 0）；真实评论/附件走 `GET /api/v2/tasks/{tid}/activities`，结果在 `result` 字段，评论是 `action=activity.comment.attachments` 类型的 activity，附件在其 `content.files[]`。
- **附件下载**：`content.files[].url` 可能内嵌短期 token。脚本逐跳校验 HTTPS 和 `attachment_hosts`，且只向 TB 域发送 TB cookie；token 过期时重新拉 activities 刷新 URL 后重试。视频默认不进入下载流程。

---

## 5. 收尾

- 分析完一个缺陷后，先把报告交给用户复核；确认无误后再进入修复。可按需用 `tb_draft.py` 出草稿，连同报告一起交回。
- 多个缺陷的草稿可追加到同一文件（`--out`），形成类似 `logs_auto/DLT_评论草稿.md` 的合集。
- 明确区分：TB/API 请求成功、附件下载成功、日志根因证据、设备物理结果；前两项不能证明后两项。
- 交付前执行 worktree 生命周期审计。只处理报告标记为“本任务创建”的工作区；先核对 `git status --short`、目标分支差异和独有提交，再按生命周期门禁清理或报告保留原因。不得把 `git worktree prune` 当作常规批量收尾。
- TB 评论默认不回写是为了避免把尚待复核的结论发布到外部系统，同时当前 POST/鉴权/幂等契约尚未验证。未来若增加回写，必须是独立显式动作：先展示最终评论全文和目标缺陷，逐次取得确认，不自动重试，并保存 TB 返回的评论标识；不得由分析或修复完成自动触发。
