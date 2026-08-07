# Superpowers 中文 Codex / Claude 增强维护版

这是一个面向 Codex CLI 与 Claude Code 的个人维护仓库。仓库以 Superpowers 方法论和中文增强版 Skills 为基础，加入 Codex 兼容层、本地策略恢复机制，并将 iCode 作为 Git 子模块保留，便于持续跟踪其上游演进。

> 本仓库不是 `obra/superpowers`、`jnMetaCode/superpowers-zh` 或 `ayukyo/icode-skill` 的官方发行版。上游项目的问题、使用方式与许可证请以上游仓库为准。

## 上游关系

| 项目 | 本仓库中的角色 | 集成方式 |
|------|----------------|----------|
| [obra/superpowers](https://github.com/obra/superpowers) | 原始软件开发方法论与核心 Skills 来源 | 通过中文增强版同步并持续对照上游 |
| [jnMetaCode/superpowers-zh](https://github.com/jnMetaCode/superpowers-zh) | 中文翻译及中国特色 Skills 的主要基础 | 作为当前 Skills 集合的主要来源 |
| [ayukyo/icode-skill](https://github.com/ayukyo/icode-skill) | 六阶段工作流与质量机制参考 | 以 `icode-skill/` Git 子模块固定版本，并选择性吸收平台通用机制 |

本仓库对 iCode 的吸收以机制复用为主，例如审查收敛、证据新鲜度、多 Git 根覆盖和防偷懒约束；这不等同于在 Codex 中完整复刻 `/icode` 命令体系。

## 主要增强

- 兼容 Codex CLI 与 Claude Code 的 Skill 自动触发方式。
- 明确 commit、worktree、测试和子代理操作的用户授权边界。
- 代码审查覆盖 staged、unstaged、untracked 以及嵌套 Git 根。
- 验证证据与当前改动绑定，避免使用过期结果宣称完成。
- 通过可恢复 policy overlay 保存本地策略，检测上游漂移并安全失败。
- 保留中文代码评审、中文提交规范和中文文档排版等本地化 Skills。

## 仓库结构

```text
.
├── */SKILL.md                       # 可自动触发的 Skills
├── icode-skill/                     # iCode Git 子模块
├── overlays/codex-local-policy.patch
├── scripts/apply-local-skill-overlays
├── scripts/skills-codex-patch.py
└── doc/                             # 安装、触发机制和吸收记录
```

## 获取仓库

首次克隆时必须同时初始化子模块。将 `<repository-url>` 替换为本仓库在 GitHub 页面显示的 Clone URL：

```bash
git clone --recurse-submodules <repository-url> ~/.claude/skills
```

如果已经完成普通克隆，再补充初始化子模块：

```bash
git -C ~/.claude/skills submodule update --init --recursive
```

`~/.codex/skills` 可以指向同一份 Skills 源目录，使 Codex CLI 与 Claude Code 共享文件：

```bash
ln -s ~/.claude/skills ~/.codex/skills
```

执行前请确认 `~/.codex/skills` 不存在，避免覆盖已有目录或链接。

## 更新与恢复本地策略

拉取仓库及子模块更新：

```bash
git -C ~/.claude/skills pull --ff-only
git -C ~/.claude/skills submodule update --init --recursive
```

重新安装或升级 `superpowers-zh` 后，运行兼容恢复脚本，并确认 policy overlay 已应用：

```bash
python3 ~/.claude/skills/scripts/skills-codex-patch.py
~/.claude/skills/scripts/apply-local-skill-overlays --check
```

恢复脚本会先做替换与 overlay 预检；发现未知上游漂移时会停止并要求人工审查，不会强制覆盖。

## 进一步阅读

- [Codex Skills 触发机制与维护指南](doc/codex-skills-trigger-guide.md)
- [iCode 机制吸收记录](doc/icode-mechanism-absorption.md)
- [iCode 使用指南](doc/icode-usage-guide.md)
- [superpowers-zh 全局安装追溯](doc/superpowers-zh-global-setup.md)

## 许可证与致谢

本仓库采用 [MIT License](LICENSE)，并在许可证文件中保留主要上游版权声明。`icode-skill/` 是独立 Git 子模块，其内容及许可证由对应上游仓库维护。

感谢 Jesse Vincent 与 Superpowers 贡献者、jnMetaCode 与 superpowers-zh 贡献者，以及 ayukyo 与 iCode 贡献者提供的开源工作。
