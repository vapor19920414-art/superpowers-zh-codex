# headroom 在 Codex CLI 的安装与配置（含 cc-switch 多 Provider 协同）

> 本文档记录 headroom（上下文优化 / Token 节流层）在 Codex CLI 上的落地方式，覆盖 MCP 工具层与 Proxy 自动压缩层两套机制，并给出 DeepSeek / 火山 ark / ChatGPT Codex 官方三种认证方式下的配置参考，以及与 cc-switch 多 Provider 切换协同的存活方案。

## 文档信息

| 项 | 值 |
|----|-----|
| 创建日期 | 2026-07-14 |
| 版本 | v1.1 |
| 适用范围 | Codex CLI + headroom 0.26.0（MCP server 1.28.0）+ cc-switch |
| 关联配置 | `~/.codex/config.toml`、`~/.codex/auth.json`、`~/.cc-switch/cc-switch.db` |
| 关联文档 | `~/.codex/AGENTS.md`（Token 治理章节）、`~/.codex/skills/compressing-large-context/SKILL.md` |

---

## 一、背景与定位

`~/.codex/AGENTS.md` 规定使用 Headroom MCP 做上下文 Token 节流，并将 `token-audit`、`token-compress` 语义映射到实际 MCP 工具。实际落地工具为 **headroom**（`chopratejas/headroom`），通过 MCP 协议向 Codex 暴露按需压缩能力。

用户同时使用 cc-switch 在多个 Provider 间切换（火山 ark / DeepSeek / ChatGPT 官方），切换会改写 `config.toml` 与 `auth.json`，因此 headroom 配置必须以"切换存活"的方式落地，否则每次切换后丢失。

本文档目标：给出一份可复制、可维护、与 cc-switch 协同的配置手册。

---

## 二、headroom 架构：两层机制

headroom 提供两层能力，**两者的 Provider 兼容性与风险等级不同**，务必区分：

| 层级 | 启动方式 | 作用 | Provider 依赖 | 风险 |
|------|----------|------|--------------|------|
| **① MCP 工具层** | `headroom mcp serve`（stdio MCP） | 按需调用 `headroom_compress` / `headroom_retrieve` / `headroom_stats` 压缩大输出、统计节省 | **无**（与 Provider 解耦） | 零风险 |
| **② Proxy 自动压缩层** | `headroom proxy`（本地 HTTP 代理 8787） | 拦截全流量，自动压缩历史轮次 / 工具输出 | 有（需 backend 适配） | 高（改 base_url，与 cc-switch 冲突） |

**工具对照表**（headroom MCP 工具 ↔ AGENTS.md 语义）：

| headroom MCP 工具 | 对应 AGENTS.md | 作用 |
|---|---|---|
| `headroom_compress` | token-compress | 压缩大文件 / 长日志，节省上下文窗口 |
| `headroom_retrieve` | （配套取回） | 按 hash 取回原始未压缩内容（需 Proxy 在线） |
| `headroom_stats` | token-audit | 统计压缩次数、节省 token、效率百分比 |

> **推荐结论**：默认只用 **① MCP 工具层**，全 Provider 通用、零风险、与 cc-switch 友好。② Proxy 层作为高级选项，仅 API Key 模式 Provider 可用，且不建议与 cc-switch 多 Provider 切换同时使用（见第六章）。

---

## 三、Provider 认证方式与兼容性矩阵

Codex CLI 的认证信息存于 `~/.codex/auth.json`，cc-switch 按 Provider 类型写入不同结构：

### 3.1 三种认证方式

**方式一：API Key 模式（DeepSeek / 火山 ark）**

`auth.json` 结构：
```json
{
  "OPENAI_API_KEY": "sk-xxxxxxxxxxxx"
}
```
- DeepSeek：key 形如 `sk-xxx`，base_url `https://api.deepseek.com/v1`
- 火山 ark：key 形如 `ark-xxx`，base_url `https://ark.cn-beijing.volces.com/api/coding/v3`

**方式二：OAuth 订阅模式（ChatGPT Codex 官方）**

通过 `codex login` 走 ChatGPT 账号 OAuth，`auth.json` 结构：
```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": {
    "id_token": "eyJ...",
    "access_token": "eyJ...",
    "refresh_token": "rt.1....",
    "account_id": "b4a15c71-..."
  },
  "last_refresh": "2026-07-11T11:04:24Z"
}
```
- base_url 走 Codex 内置官方 endpoint（`https://chatgpt.com/backend-api/codex`），无需自定义 `model_providers`。
- token 由 Codex 自动刷新。

### 3.2 headroom 两层机制 × 三种认证 兼容性矩阵

| 认证方式 | ① MCP 工具层 | ② Proxy 自动压缩层 | 说明 |
|----------|:----------:|:----------------:|------|
| DeepSeek（API Key） | ✅ 可用 | ✅ 可用（anyllm/openai backend） | 全功能 |
| 火山 ark（API Key） | ✅ 可用 | ✅ 可用（anyllm/openai backend） | 全功能 |
| ChatGPT 官方（OAuth） | ✅ 可用 | ❌ 不可用 | Proxy 仅支持 API Key backend，无法代理 OAuth 订阅流 |

> 结论：**MCP 工具层是唯一全 Provider 通用的方案**，OAuth 订阅模式只能用 MCP 工具层。

---

## 四、安装 headroom

### 4.1 安装

headroom 为 Python 脚本，安装到 `~/.local/bin/headroom`：

```bash
# 方式一：pip 安装（推荐）
pip install --user headroom

# 方式二：官方安装脚本（如提供）
# curl -fsSL https://raw.githubusercontent.com/chopratejas/headroom/main/install.sh | bash
```

### 4.2 验证

```bash
headroom --version          # 期望输出: headroom, version 0.26.0
which headroom              # 期望: /home/<user>/.local/bin/headroom
headroom mcp --help         # 查看 MCP 子命令
```

### 4.3 验证 MCP server 可独立启动（标准 stdio 握手）

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' \
  | timeout 10 headroom mcp serve 2>/dev/null | head -1
```
期望返回包含 `"serverInfo":{"name":"headroom","version":"1.28.0"}` 的 JSON。

---

## 五、方案 A：MCP 工具层配置（★ 推荐，全 Provider 通用）

### 5.1 原理

`headroom mcp serve` 是标准 stdio MCP server，与 Provider 完全解耦。Codex 通过 `config.toml` 的 `[mcp_servers]` 加载，启动后自动暴露 `headroom_compress` / `headroom_retrieve` / `headroom_stats` 三个工具。

### 5.2 配置方式选择

| 方式 | 写入位置 | cc-switch 切换是否存活 | 推荐度 |
|------|----------|:--------------------:|:-----:|
| 直接写 config.toml | `[mcp_servers.headroom]` | ❌ 切换 Provider 会被覆盖 | ✗ |
| 注册到 cc-switch mcp_servers 表 | `~/.cc-switch/cc-switch.db` | ✅ 切换自动注入 | ★ |

> **必须用 cc-switch 注册方式**。直接写 config.toml 在下次切换 Provider 时会被 cc-switch 覆盖丢失（这是当前已知的坑）。

### 5.3 方式一：注册到 cc-switch（推荐）

cc-switch 数据库有专用 `mcp_servers` 表，字段含 `enabled_codex`。注册后，cc-switch 在生成任何 Provider 的 `config.toml` 时都会自动合并 `enabled_codex=1` 的 MCP 配置。

**步骤 A：通过 cc-switch GUI 添加（最稳）**

1. 打开 cc-switch 应用
2. 进入「MCP 服务管理」/「MCP Servers」面板
3. 新增 MCP server，填入：
   - 名称：`headroom`
   - 命令：`/home/<user>/.local/bin/headroom`
   - 参数：`mcp serve`
4. 勾选「启用 Codex」（enabled_codex）
5. 保存，切换一次 Provider 触发生效

**步骤 B：通过 sqlite 直写（兜底，需谨慎）**

> server_config 格式以 cc-switch GUI 实际生成为准；以下为标准 MCP 配置对象。

```bash
# 备份
cp ~/.cc-switch/cc-switch.db ~/.cc-switch/cc-switch.db.bak.$(date +%Y%m%d_%H%M%S)

# 写入（command 用绝对路径）
sqlite3 ~/.cc-switch/cc-switch.db <<'SQL'
INSERT INTO mcp_servers (name, server_config, description, enabled_codex)
VALUES (
  'headroom',
  '{"command":"/home/<user>/.local/bin/headroom","args":["mcp","serve"]}',
  'headroom 上下文优化 MCP（token-compress / token-audit）',
  1
);
SQL

# 验证
sqlite3 ~/.cc-switch/cc-switch.db "SELECT id,name,enabled_codex FROM mcp_servers;"
```

注册后，在 cc-switch 中**切换一次 Provider**（或重启 cc-switch），让其把 headroom 注入 `config.toml`。

### 5.4 方式二：直接写 config.toml（仅临时验证用）

> 仅用于快速验证，**不要长期依赖**，cc-switch 切换会丢失。

```bash
cp ~/.codex/config.toml ~/.codex/config.toml.bak.$(date +%Y%m%d_%H%M%S)
```

在 `~/.codex/config.toml` 的 `[mcp_servers]` 段下添加：
```toml
[mcp_servers.headroom]
command = "/home/<user>/.local/bin/headroom"
args = ["mcp", "serve"]
```

### 5.5 验证 MCP 工具层

```bash
# 1. TOML 语法校验（Python 3.11+ 使用 tomllib；Python 3.10 使用 tomli）
python3 -c "import tomli; d=tomli.load(open('$HOME/.codex/config.toml','rb')); print(d['mcp_servers']['headroom'])"

# 2. 重启 Codex CLI，检查工具是否加载
#    Codex 中工具命名形如 mcp__headroom__headroom_compress
#    可让 Codex 调用 headroom_stats 验证
```

### 5.6 retrieve 工具的本地缓存与 Proxy 回退

`headroom_compress` 会将原文保存到 MCP 本地缓存，默认有效期为 1 小时。`headroom_retrieve` 优先从本地缓存按 hash 读取，因此在未启动 Proxy 时，仍可取回本 MCP 会话压缩过的内容。

以下场景才需要 Proxy：
- 取回由 Proxy 自动压缩产生的 hash；
- 本地缓存失效后，尝试从 Proxy 缓存回退；
- 使用方案 B 的全流量自动压缩。

启动 Proxy（用于 Proxy 压缩或作为 retrieve 回退）：
```bash
headroom proxy --no-ccr-inject-tool &   # 后台运行，不注入 retrieve 工具到流量
```

### 5.7 `compressing-large-context` Skill 与 AGENTS 规则

`~/.codex/skills/compressing-large-context/SKILL.md` 是 Headroom MCP 的语义触发规则，不是由 `AGENTS.md` 显式调用的函数。

| 组件 | 生效时机 | 职责 |
|------|----------|------|
| `compressing-large-context` Skill | 新建 Codex 会话后，根据用户任务语义匹配 | 对长日志、大源码、大型 diff、广泛检索和 JSON 使用「限缩输出 → 压缩 → 按 hash 定向取回」流程 |
| `~/.codex/AGENTS.md` | 每个会话始终生效 | 以 500 行源码、300 行日志或命令输出等阈值兜底，要求调用真实 Headroom MCP 工具 |

Skill 的触发依据是 `SKILL.md` frontmatter 中的 `description`。用户请求如「分析 1,000 行编译日志」「全仓搜索后定位问题」「检查大型 diff」会在任务开始时匹配该 Skill；也可在请求中写 `$compressing-large-context` 明确启用。

AGENTS 规则不会加载 Skill，而是在执行过程中遇到超过阈值的工具输出时继续提供兜底约束。两者都属于 MCP 按需压缩，不等同于 Proxy 的全流量自动压缩。创建或修改 Skill 后，应新建 Codex 会话使其进入自动匹配候选列表。

---

## 六、方案 B：自动压缩 Proxy 层（仅 API Key 模式，高级选项）

> ⚠️ 此方案会修改 Codex 的 `base_url` 指向本地 Proxy，**与 cc-switch 多 Provider 切换直接冲突**。仅当固定使用单一 API Key Provider 且需要全流量自动压缩时考虑。

### 6.1 原理

headroom Proxy 监听本地端口（默认 8787），作为 Codex 与真实 API 之间的中间人，自动压缩历史轮次与工具输出。支持 OpenAI 兼容客户端：

```
Codex (base_url=http://127.0.0.1:8787/v1)
        │
        ▼
  headroom proxy (backend=anyllm, anyllm-provider=openai)
        │  使用环境变量里的真实 upstream + key 转发
        ▼
  真实 API (DeepSeek / ark / ...)
```

### 6.2 backend 选择

headroom Proxy 的 backend 选项：
```
--backend TEXT           anthropic | bedrock | openrouter | anyllm | litellm-<provider>
                         (默认 anthropic，OpenAI 兼容用 anyllm)
--anyllm-provider TEXT   openai | mistral | groq | ollama ... (默认 openai)
```

DeepSeek / 火山 ark 均为 OpenAI 兼容，统一用：
- `HEADROOM_BACKEND=anyllm`
- `HEADROOM_ANYLLM_PROVIDER=openai`

### 6.3 配置步骤（以 DeepSeek 为例）

**步骤 1：启动 Proxy（进程环境变量配真实 upstream）**

```bash
# 真实 upstream 与 key 通过环境变量传入 Proxy 进程
export HEADROOM_BACKEND=anyllm
export HEADROOM_ANYLLM_PROVIDER=openai
export OPENAI_BASE_URL=https://api.deepseek.com/v1      # 真实 upstream
export OPENAI_API_KEY=sk-你的DeepSeek密钥                # 真实 key

headroom proxy --port 8787
```

**步骤 2：修改 Codex config.toml（base_url 指向 Proxy）**

```toml
model_provider = "deepseek"
[model_providers.deepseek]
name = "DeepSeek"
base_url = "http://127.0.0.1:8787/v1"   # ← 指向本地 Proxy，非真实地址
wire_api = "chat"
requires_openai_auth = true
```

`auth.json` 的 `OPENAI_API_KEY` 可填占位值（Codex 本地校验用，真实 key 由 Proxy 持有）：
```json
{ "OPENAI_API_KEY": "placeholder-via-headroom-proxy" }
```

### 6.4 限制与风险

| 限制 | 说明 |
|------|------|
| OAuth 订阅不可用 | ChatGPT 官方走 OAuth，Proxy 的 anyllm backend 仅支持 API Key，无法代理 |
| 与 cc-switch 冲突 | cc-switch 切换会覆盖 base_url，Proxy 配置失效；需关闭 cc-switch 自动切换 |
| wire_api 限制 | Proxy 转发 OpenAI chat completions；若 Provider 仅支持 responses API 需验证兼容性 |
| 调试复杂 | 流量经中间人，排障需看 Proxy 日志（`headroom proxy --log-file`） |

> **建议**：除非确有全流量压缩需求，否则优先用方案 A（MCP 工具层）。Proxy 层不要与 cc-switch 同时使用。

---

## 七、cc-switch 多 Provider 协同

### 7.1 cc-switch 工作机制

cc-switch（`/usr/bin/cc-switch`，配置 `~/.cc-switch/`）管理多个 Provider profile，存储于 `cc-switch.db` 的 `providers` 表。切换 Provider 时，cc-switch 用所选 profile 的 `settings_config` 生成 `~/.codex/config.toml`，并用 `auth` 字段生成 `~/.codex/auth.json`。

关键点：
- **`config.toml` 是每次切换全量重写**的（基于 profile 模板 + 通用配置）
- **`mcp_servers` 表是全局的**，`enabled_codex=1` 的记录会被合并进每个 Provider 生成的 config.toml
- 因此 headroom MCP 配置必须注册到 `mcp_servers` 表，才能跨 Provider 切换存活

### 7.2 三种 Provider profile 配置参考

cc-switch 中每个 Codex Provider 的 `settings_config` 含 `auth`、`config`、`modelCatalog` 三部分。以下为三种认证方式的 config 片段参考（脱敏）：

**Profile 1：火山 ark（API Key + responses API）**
```toml
sandbox_mode = "danger-full-access"
approval_policy = "never"
model_provider = "custom"
model = "glm-latest"
[model_providers.custom]
name = "ark_agentplan"
base_url = "https://ark.cn-beijing.volces.com/api/coding/v3"
wire_api = "responses"
requires_openai_auth = true
```
auth: `{ "OPENAI_API_KEY": "ark-xxx" }`

**Profile 2：DeepSeek（API Key + chat API）**
```toml
sandbox_mode = "danger-full-access"
approval_policy = "never"
model_provider = "deepseek"
model = "deepseek-chat"
[model_providers.deepseek]
name = "DeepSeek"
base_url = "https://api.deepseek.com/v1"
wire_api = "chat"
requires_openai_auth = true
```
auth: `{ "OPENAI_API_KEY": "sk-xxx" }`

**Profile 3：ChatGPT Codex 官方（OAuth 订阅）**
```toml
sandbox_mode = "danger-full-access"
approval_policy = "never"
# 不指定 model_provider，走 Codex 内置官方认证
model = "gpt-5-codex"
```
auth:
```json
{
  "auth_mode": "chatgpt",
  "OPENAI_API_KEY": null,
  "tokens": { "id_token": "...", "access_token": "...", "refresh_token": "...", "account_id": "..." },
  "last_refresh": "..."
}
```
> OAuth 订阅通过 `codex login` 获取，cc-switch 中标记为 `provider_type=official`。

### 7.3 headroom 配置存活方案（核心）

确保 headroom MCP 在任意 Provider 切换后仍存在的标准流程：

1. **注册到 mcp_servers 表**（见 5.3），设 `enabled_codex=1`
2. **不要**手动在 config.toml 写 `[mcp_servers.headroom]`（会被覆盖）
3. 在 cc-switch 中切换一次任意 Provider，触发合并注入
4. 验证 `config.toml` 已含 `[mcp_servers.headroom]`

```bash
# 验证切换后 headroom 仍在
grep -A3 '\[mcp_servers.headroom\]' ~/.codex/config.toml
```

### 7.4 cc-switch 相关设置项说明

`~/.cc-switch/settings.json` 中与认证切换相关的项：

| 设置项 | 含义 | 建议 |
|--------|------|------|
| `preserveCodexOfficialAuthOnSwitch` | 切换时是否保留 Codex 官方 OAuth auth | 用官方订阅时建议 true |
| `currentProviderCodex` | 当前启用的 Codex Provider ID | 由 cc-switch 维护 |
| `commonConfigConfirmed` | 通用配置（含 MCP）确认 | true |

---

## 八、验证清单

完成配置后，按序验证：

- [ ] `headroom --version` 输出 0.26.0
- [ ] `headroom mcp serve` 握手返回 serverInfo
- [ ] cc-switch `mcp_servers` 表含 headroom 且 `enabled_codex=1`
- [ ] 切换 Provider 后 `config.toml` 仍含 `[mcp_servers.headroom]`
- [ ] 使用 `tomllib`（Python 3.11+）或 `tomli`（Python 3.10）校验 TOML 合法
- [ ] Codex 重启后工具列表含 `mcp__headroom__headroom_*`
- [ ] 调用 `headroom_stats` 返回压缩统计（无报错）
- [ ] `auth.json` 认证方式与当前 Provider 匹配（API Key / OAuth）

---

## 九、故障排查与回退

### 9.1 常见问题

| 现象 | 原因 | 处理 |
|------|------|------|
| 切换 Provider 后 headroom 工具消失 | 直接写了 config.toml，未注册 mcp_servers 表 | 按 5.3 注册到 cc-switch |
| `headroom_retrieve` 报错 | Proxy 未运行 | `headroom proxy &` 或改用 compress/stats |
| Codex 启动报 MCP 加载失败 | command 路径错误 / 权限不足 | 用绝对路径，`chmod +x` |
| toml 解析失败 | 手动编辑破坏格式 | 用备份恢复 |
| ChatGPT 官方下无法用 Proxy | OAuth 不支持 anyllm backend | 改用 MCP 工具层（方案 A） |

### 9.2 回退

```bash
# 回退 config.toml
ls ~/.codex/config.toml.bak.* | tail -1 | xargs -I{} cp {} ~/.codex/config.toml

# 回退 cc-switch 数据库
ls ~/.cc-switch/cc-switch.db.bak.* | tail -1 | xargs -I{} cp {} ~/.cc-switch/cc-switch.db

# 移除 headroom MCP 注册
sqlite3 ~/.cc-switch/cc-switch.db "DELETE FROM mcp_servers WHERE name='headroom';"
```

### 9.3 排查命令

```bash
# 查看 headroom MCP 实际暴露的工具
python3 - <<'PY'
import subprocess,json
p=subprocess.Popen(["headroom","mcp","serve"],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
p.stdin.write(json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}})+"\n");p.stdin.flush();p.stdout.readline()
p.stdin.write(json.dumps({"jsonrpc":"2.0","method":"notifications/initialized"})+"\n");p.stdin.flush()
p.stdin.write(json.dumps({"jsonrpc":"2.0","id":2,"method":"tools/list"})+"\n");p.stdin.flush()
import time;time.sleep(0.3)
print([t["name"] for t in json.loads(p.stdout.readline())["result"]["tools"]])
p.terminate()
PY

# 查看 cc-switch 当前 Provider 与 mcp 注册
sqlite3 ~/.cc-switch/cc-switch.db "SELECT name,is_current FROM providers WHERE app_type='codex';"
sqlite3 ~/.cc-switch/cc-switch.db "SELECT name,enabled_codex FROM mcp_servers;"
```

---

## 附录 A：完整 config.toml 示例（ark + headroom MCP 工具层）

```toml
sandbox_mode = "danger-full-access"
approval_policy = "never"
trust_level = "fully-trusted"
model_provider = "custom"
model = "glm-latest"
model_reasoning_effort = "high"
disable_response_storage = true

[mcp_servers.headroom]
command = "/home/<user>/.local/bin/headroom"
args = ["mcp", "serve"]

[model_providers.custom]
name = "ark_agentplan"
base_url = "https://ark.cn-beijing.volces.com/api/coding/v3"
wire_api = "responses"
requires_openai_auth = true

[projects."/home/<user>/work/your-project"]
trust_level = "trusted"
```

## 附录 B：headroom 环境变量速查

| 环境变量 | 作用 | 默认 |
|----------|------|------|
| `HEADROOM_BACKEND` | Proxy backend | anthropic |
| `HEADROOM_ANYLLM_PROVIDER` | anyllm 后端的 Provider | openai |
| `HEADROOM_HOST` / `HEADROOM_PORT` | Proxy 监听地址 | 127.0.0.1 / 8787 |
| `HEADROOM_MODE` | 优化模式 token/cache | token |
| `OPENAI_BASE_URL` | 真实 upstream（Proxy 转发目标） | - |
| `OPENAI_API_KEY` | 真实 key（Proxy 持有） | - |

---

## 变更记录

| 日期 | 版本 | 内容 |
|------|------|------|
| 2026-07-14 | v1.1 | 补充 Skill 自动发现与 AGENTS 阈值兜底的分工；更正 retrieve 的本地缓存行为；补充 Python 3.10 TOML 校验方式 |
| 2026-07-14 | v1.0 | 初版：安装、MCP 工具层、Proxy 层、三种认证、cc-switch 协同 |
