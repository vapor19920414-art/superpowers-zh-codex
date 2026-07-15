---
name: english-commit-conventions
description: 英文 commit 与 changelog 规范——面向跨国团队/开源项目的 Conventional Commits 1.0.0 落地、Jira ticket 关联（如 SRT-986）、commitlint/husky/commitizen 英文配置、conventional-changelog 英文化。当用户要求生成英文 commit message、配置英文 commitlint/husky/commitizen、或面向跨国团队/开源项目需要英文 commit 规范时调用；用户未明确提出英文 commit 规范需求时不自动触发。
version: "1.0.0"
license: MIT
metadata:
  hermes:
    tags: [git, english]
---

# 英文 Git 提交规范（跨国团队 / 开源项目）

> 本规范与 `chinese-commit-conventions` 对称：type 前缀相同（英文），scope/subject/body 与配置文案改英文，并补充 Jira ticket 关联约定。内部项目用中文版，对外/跨国项目用本版。

## 1. Conventional Commits 1.0.0

基于 Conventional Commits 1.0.0 规范，全部使用英文。

### 类型（type）定义

| type       | 说明                          | 示例场景                          |
| ---------- | ----------------------------- | --------------------------------- |
| `feat`     | 新功能                        | add user registration module      |
| `fix`      | 修复缺陷                      | fix blank screen on login page    |
| `docs`     | 文档变更                      | update API reference              |
| `style`    | 代码格式（不影响逻辑）        | fix indentation, add semicolons   |
| `refactor` | 重构（非新功能、非修复）      | split oversized service class     |
| `perf`     | 性能优化                      | optimize list query on home page  |
| `test`     | 测试相关                      | add unit tests for user module    |
| `chore`    | 构建/工具/依赖变更            | upgrade webpack to v5             |
| `ci`       | 持续集成配置                  | tweak GitHub Actions pipeline     |
| `revert`   | 回滚提交                      | revert login refactor in v2.1.0   |
| `build`    | 构建系统/外部依赖             | update Cargo.toml dependencies    |

### 原则

- type、scope、subject、body 均使用英文
- subject 用祈使句、现在时（`add` 而非 `added`/`adds`）
- 跨国协作优先用英文 scope（与代码模块名一致，便于检索）

## 2. 英文 commit message 模板（含 Jira ticket）

```
<type>(<scope>): <subject> (<TICKET-ID>)

<body>

<footer>
```

### 完整示例

```
feat(auth): add SSO login for internal IdP (SRT-986)

- integrate corporate SAML IdP
- support auto-provisioning for first-time users
- fall back to password login when SSO unavailable

Refs: SRT-986
```

```
fix(order): prevent oversell under concurrent checkout (SRT-1124)

Race condition in stock deduction caused oversell during flash sales.
Switch to Redis distributed lock + DB optimistic lock.

Impact: order-service, stock-service
Verified: passed 500-concurrency stress test

Refs: SRT-1124, SRT-1130
```

## 3. Subject 行规范

### 格式

```
<type>(<scope>): <description> (<TICKET-ID>)
```

### 规则

- **type**: 必填，从类型表中选取
- **scope**: 选填，英文模块名（与代码目录/服务名一致）
  - 示例：`auth`、`order`、`payment`、`gateway`、`core`
- **description**: 必填，英文祈使句，不超过 50 个字符
  - 动宾短语：`add xxx` / `fix xxx` / `refactor xxx` / `optimize xxx`
  - 不加句号结尾
  - 首字母小写（Conventional Commits 惯例，配合 commitlint `subject-case: lower-case`）
- **TICKET-ID**: 跨国团队约定放 subject 末尾括号内，便于一眼追溯
  - 格式 `(<PROJKEY>-<num>)`，如 `(SRT-986)`
  - 也可放 footer（见第 6 节），团队二选一统一即可

### 好的示例

```
feat(perms): add RBAC-based fine-grained access control (SRT-204)
fix(payment): resolve WeChat Pay callback signature failure (SRT-318)
perf(list): virtualize large table rendering (SRT-415)
refactor(gateway): split monolith gateway into microservices (SRT-502)
```

### 反面示例

```
# 以下写法应避免
fix: fixed a bug
feat: update code
chore: some changes
Fix(Auth): Add SSO.        # 大写开头、加句号、scope 大写
feat: add login SRT-986   # ticket 缺括号，难辨识
```

## 4. Body 编写规范

Body 用英文详细说明动机、方案和影响。

### 编写要点

- 说明 **why**（背景/原因）
- 说明 **how**（技术方案摘要）
- 说明 **impact**（受影响模块/接口）
- 每行不超过 72 个字符
- 正文与标题之间空一行

### Body 模板

```
<background and reason>

Approach:
- <key point 1>
- <key point 2>

Impact: <affected modules or services>
```

## 5. Breaking Changes 标注

不兼容变更必须在 footer 或 type 后标注。

### 格式一：footer 标注

```
feat(api): restructure user info response (SRT-986)

Change flat response to nested structure. Frontend must update field
access paths accordingly.

BREAKING CHANGE: /api/user/info response shape changed
- avatar moved into profile object
- removed deprecated nickname field, use displayName
```

### 格式二：type 后加感叹号

```
feat(api)!: restructure user info response (SRT-986)
```

### 团队约定

- 数据库表结构变更 -> 必须标注 BREAKING CHANGE
- 公共 API 参数/返回值变更 -> 必须标注
- 配置文件格式变更 -> 必须标注
- 标注时须写明迁移方法或升级步骤

## 6. Jira ticket 关联（重点）

跨国团队通过 ticket id 追溯需求/缺陷，常见两种放法，团队统一其一：

### 放法 A：subject 末尾括号（推荐，一眼可见）

```
feat(auth): add SSO login for internal IdP (SRT-986)
```

### 放法 B：footer 关联（subject 保持简洁）

```
feat(auth): add SSO login for internal IdP

- integrate corporate SAML IdP
- support auto-provisioning

Refs: SRT-986
```

### 多 ticket 关联

```
Refs: SRT-986, SRT-987
Closes: SRT-990
```

### 与 GitHub Issue 并存（开源 + 内部 Jira 双轨）

```
feat(auth): add SSO login for internal IdP (SRT-986)

- integrate corporate SAML IdP

Closes #128
Refs: SRT-986
```

> 约定：`Closes #N` 触发 GitHub 自动关闭；`Refs: SRT-xxx` 仅关联不自动关闭，供 Jira 侧 smart-commit 抓取。

## 7. Changelog 自动生成配置（英文 section）

### 安装 conventional-changelog

```bash
npm install -D conventional-changelog-cli conventional-changelog-conventionalcommits
```

### package.json 脚本

```json
{
  "scripts": {
    "changelog": "conventional-changelog -p conventionalcommits -i CHANGELOG.md -s",
    "changelog:all": "conventional-changelog -p conventionalcommits -i CHANGELOG.md -s -r 0",
    "release": "standard-version"
  }
}
```

### .versionrc.js 英文配置

```javascript
module.exports = {
  types: [
    { type: 'feat',     section: 'Features' },
    { type: 'fix',      section: 'Bug Fixes' },
    { type: 'perf',     section: 'Performance Improvements' },
    { type: 'refactor', section: 'Code Refactoring' },
    { type: 'docs',     section: 'Documentation' },
    { type: 'test',     section: 'Tests' },
    { type: 'build',    section: 'Build System' },
    { type: 'chore',    section: 'Chores', hidden: true },
    { type: 'ci',       section: 'Continuous Integration', hidden: true },
    { type: 'style',    section: 'Styles', hidden: true },
    { type: 'revert',   section: 'Reverts' }
  ],
  commitUrlFormat: '{{host}}/{{owner}}/{{repository}}/commit/{{hash}}',
  compareUrlFormat: '{{host}}/{{owner}}/{{repository}}/compare/{{previousTag}}...{{currentTag}}'
}
```

## 8. commitlint 英文配置

### 安装

```bash
npm install -D @commitlint/cli @commitlint/config-conventional
```

### commitlint.config.js

```javascript
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [2, 'always', [
      'feat', 'fix', 'docs', 'style', 'refactor',
      'perf', 'test', 'build', 'chore', 'ci', 'revert'
    ]],
    'type-case': [2, 'always', 'lower-case'],
    'type-empty': [2, 'never'],
    'subject-empty': [2, 'never'],
    'subject-case': [2, 'always', 'lower-case'],
    'subject-max-length': [2, 'always', 72],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [1, 'always', 100],
    'footer-max-line-length': [1, 'always', 100],
    // 可选：强制 subject 末尾带 (SRT-xxx) ticket
    // 'subject-pattern': [2, 'always', / \([A-Z]+-\d+\)$/],
  },
  prompt: {
    messages: {
      type: 'Select the type of change:',
      scope: 'Denote the scope (optional):',
      subject: 'Write a short, imperative tense description:',
      body: 'Provide a longer description (optional, use "|" for newlines):',
      breaking: 'List any breaking changes (optional):',
      footer: 'List any Issue or Jira refs (e.g. SRT-986, #123):',
      confirmCommit: 'Confirm the commit?'
    }
  }
}
```

> `subject-pattern` 行默认注释。开启后将强制 subject 必须以 `(SRT-xxx)` 结尾，适合要求每个 commit 都挂 ticket 的团队；开源贡献者无 ticket 时需关闭此规则，故默认不启用。

## 9. husky + lint-staged 集成

### 安装与初始化

```bash
npm install -D husky lint-staged
npx husky init
```

### 配置 commit-msg 钩子

```bash
# .husky/commit-msg
npx --no -- commitlint --edit "$1"
```

### 配置 pre-commit 钩子

```bash
# .husky/pre-commit
npx lint-staged
```

### lint-staged 配置（package.json）

```json
{
  "lint-staged": {
    "*.{js,ts,jsx,tsx,vue}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{css,scss,less}": [
      "stylelint --fix",
      "prettier --write"
    ],
    "*.md": [
      "prettier --write"
    ]
  }
}
```

### 交互式提交（可选）

```bash
npm install -D commitizen cz-conventional-changelog

# package.json 中添加
{
  "config": {
    "commitizen": {
      "path": "cz-conventional-changelog"
    }
  },
  "scripts": {
    "commit": "cz"
  }
}
```

运行 `npm run commit` 即可进入英文交互式提交引导。

## 10. 团队规范检查清单

### 提交前自查

- [ ] type 是否正确选择（feat/fix/docs/...）
- [ ] scope 是否为英文模块名且与代码一致
- [ ] subject 是否为英文祈使句、小写开头、≤50 字符
- [ ] subject 末尾是否去掉了句号
- [ ] Jira ticket 是否按团队约定放置（subject 末尾 or footer）
- [ ] body 是否说明了 why / how / impact
- [ ] 不兼容变更是否标注了 BREAKING CHANGE
- [ ] 一次提交是否只做了一件事（原子性）

### 跨国协作额外注意

- 时区/语言：body 用英文，避免俚语、缩写须首次出现时展开（如 `IdP (Identity Provider)`）
- ticket 优先：每个 commit 尽量挂 ticket，便于 Jira smart-commit 自动关联
- 文化中立：subject/body 保持客观陈述，不带情绪化措辞

### 常见问题

**Q: ticket 该放 subject 还是 footer？**
A: 团队统一即可。subject 末尾（`feat(auth): add SSO (SRT-986)`）可一眼追溯，推荐；若 subject 已较长或开源贡献者无 ticket，放 footer `Refs: SRT-986`。

**Q: 开源贡献者没有 Jira ticket 怎么办？**
A: 关闭 `subject-pattern` 规则，footer 用 GitHub Issue（`Closes #128`）即可。内部成员提交时再带 `SRT-xxx`。

**Q: scope 用英文还是中文？**
A: 对外项目一律英文，与代码模块名一致，便于跨语言团队检索。

**Q: 多人协作如何保证规范一致？**
A: 靠工具而非自觉。配置 husky + commitlint，不符合规范的提交在本地被拦截；CI 侧再加一道 `commitlint --from origin/main --to HEAD` 检查。
