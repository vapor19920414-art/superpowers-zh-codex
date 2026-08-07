#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
superpowers-zh 重装后恢复 Codex 兼容措辞。
idempotent：已应用的改动会跳过，可安全重复执行。

背景：superpowers-zh 安装会覆盖 SKILL.md 为官方原版（含 /xxx 死锁措辞或
Claude Code 专属工具名）。本脚本先恢复 7 个 skill 的历史 Codex 兼容措辞，
再调用 skills 仓库内 policy overlay，恢复已审查的授权、测试、review 与验证规则。

用法：python3 ~/.claude/skills/scripts/skills-codex-patch.py
"""
import os
import subprocess
import tempfile

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
SKILLS_BASE = os.path.dirname(SCRIPT_DIR)
CLAUDE_MD = os.path.join(os.path.dirname(SKILLS_BASE), 'CLAUDE.md')

# SKILL.md + CLAUDE.md 共用的 description 改动
CHANGES = {
    'chinese-code-review': [
        ('仅在用户显式 /chinese-code-review 时调用，不要根据上下文自动触发。',
         '当用户要求做中文代码评审、请求 review 他人代码、或在中文团队语境下需要给出 review 意见时调用；用户未明确提出 review 需求时不自动触发。'),
    ],
    'chinese-commit-conventions': [
        ('仅在用户显式 /chinese-commit-conventions 时调用，不要根据上下文自动触发。',
         '当用户要求生成中文 commit message、配置中文 commitlint/husky/commitizen、或需要中文 changelog 时调用；用户未明确提出 commit 规范需求时不自动触发。'),
    ],
    'chinese-documentation': [
        ('仅在用户显式 /chinese-documentation 时调用，不要根据上下文自动触发。',
         '当用户要求做中文文档排版、检查中英文空格/全半角标点、或需要中文文案排版规范时调用；用户未明确提出文档排版需求时不自动触发。'),
    ],
    'chinese-git-workflow': [
        ('仅在用户显式 /chinese-git-workflow 时调用，不要根据上下文自动触发。',
         '当用户要求配置国内 Git 平台（Gitee/Coding.net/极狐 GitLab/CNB）SSH/HTTPS/凭据/CI、或做镜像同步时调用；用户未明确提出国内 Git 平台配置需求时不自动触发。'),
    ],
    'english-commit-conventions': [
        ('仅在用户显式 /english-commit-conventions 时调用，不要根据上下文自动触发。',
         '当用户要求生成英文 commit message、配置英文 commitlint/husky/commitizen、或面向跨国团队/开源项目需要英文 commit 规范时调用；用户未明确提出英文 commit 规范需求时不自动触发。'),
    ],
    'test-driven-development': [
        ('在实现任何功能或修复 bug 时使用，在编写实现代码之前',
         '仅当用户明确要求编写单元测试、补充测试用例、完善测试覆盖时使用；功能开发与代码改造流程中不自动触发，不编写失败测试或 TDD 前置测试'),
    ],
    'using-superpowers': [
        ('调用 Skill 工具', '调用相关技能'),
    ],
}

# 仅 SKILL.md body 的改动（CLAUDE.md 中无对应内容）
SKILL_ONLY_CHANGES = {
    'using-superpowers': [
        ('在进入 EnterPlanMode 之前', '在进入计划模式之前'),
    ],
}

# CLAUDE.md "可用 Skills" 一节里无对应行的 skill
CLAUDE_MD_SKIP = {'english-commit-conventions'}


def plan_file(path, replacements):
    """在内存中规划替换，返回 (新内容, 应用数, 未匹配列表)。"""
    with open(path, encoding='utf-8') as f:
        s = f.read()
    hit = 0
    missed = []
    for old, new in replacements:
        if old in s:
            s = s.replace(old, new, 1)
            hit += 1
        elif new not in s:
            missed.append(old)
    return s, hit, missed


def preflight_overlay(overlay, planned_contents):
    """在临时目录验证 overlay 对规划后的文件可应用或已应用。"""
    result = subprocess.run(
        ['git', 'apply', '--numstat', overlay],
        check=True, capture_output=True, text=True)
    targets = [line.rsplit('\t', 1)[-1] for line in result.stdout.splitlines()]

    with tempfile.TemporaryDirectory(prefix='codex-skill-overlay-') as temp_dir:
        for rel_path in targets:
            source = os.path.join(SKILLS_BASE, rel_path)
            if not os.path.exists(source):
                raise RuntimeError(f'overlay 目标不存在: {source}')
            target = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            content = planned_contents.get(source)
            if content is None:
                with open(source, encoding='utf-8') as f:
                    content = f.read()
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)

        reverse = subprocess.run(
            ['git', 'apply', '--reverse', '--check', overlay],
            cwd=temp_dir, capture_output=True, text=True)
        forward = subprocess.run(
            ['git', 'apply', '--check', overlay],
            cwd=temp_dir, capture_output=True, text=True)
        if reverse.returncode != 0 and forward.returncode != 0:
            detail = forward.stderr.strip() or reverse.stderr.strip()
            raise RuntimeError(f'overlay 无法安全应用: {detail}')


def main():
    planned_contents = {}
    skill_results = []
    errors = []

    # ---- Preflight 1: plan SKILL.md changes without writing ----
    all_skills = sorted(set(CHANGES) | set(SKILL_ONLY_CHANGES))
    for name in all_skills:
        p = os.path.join(SKILLS_BASE, name, 'SKILL.md')
        if not os.path.exists(p):
            errors.append(f'SKILL.md 不存在: {name}')
            continue
        reps = CHANGES.get(name, []) + SKILL_ONLY_CHANGES.get(name, [])
        content, hit, missed = plan_file(p, reps)
        if missed:
            errors.append(f'SKILL.md 未匹配: {name} -> {missed}')
        planned_contents[p] = content
        skill_results.append((name, hit))

    # ---- Preflight 2: plan CLAUDE.md changes without writing ----
    claude_result = None
    if not os.path.exists(CLAUDE_MD):
        errors.append(f'CLAUDE.md 不存在: {CLAUDE_MD}')
    else:
        all_reps = []
        for name in sorted(CHANGES):
            if name not in CLAUDE_MD_SKIP:
                all_reps.extend(CHANGES[name])
        content, hit, missed = plan_file(CLAUDE_MD, all_reps)
        if missed:
            errors.append(f'CLAUDE.md 未匹配: {missed}')
        planned_contents[CLAUDE_MD] = content
        claude_result = hit

    # ---- Preflight 3: verify overlay against the planned file state ----
    overlay_script = os.path.join(SKILLS_BASE, 'scripts', 'apply-local-skill-overlays')
    overlay = os.path.join(SKILLS_BASE, 'overlays', 'codex-local-policy.patch')
    if not os.path.isfile(overlay_script) or not os.access(overlay_script, os.X_OK):
        errors.append(f'overlay 脚本不存在或不可执行: {overlay_script}')
    if not os.path.isfile(overlay):
        errors.append(f'overlay 不存在: {overlay}')

    if errors:
        print('=== 预检失败，未修改任何文件 ===')
        for error in errors:
            print(f'  !! {error}')
        raise SystemExit(65)

    try:
        preflight_overlay(overlay, planned_contents)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print('=== 预检失败，未修改任何文件 ===')
        print(f'  !! {exc}')
        raise SystemExit(65) from exc

    # ---- Apply only after every preflight passes ----
    print('=== 恢复 SKILL.md 措辞 ===')
    for name, hit in skill_results:
        print(f'  {"计划应用 " + str(hit) + " 处" if hit else "已存在(跳过)"}: {name}')
    print('\n=== 恢复 CLAUDE.md "可用 Skills" 对应行 ===')
    print(f'  计划应用 {claude_result} 处')

    for path, content in planned_contents.items():
        with open(path, encoding='utf-8') as f:
            current = f.read()
        if current != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

    print('\n=== 恢复本地 Skill policy overlay ===')
    subprocess.run([overlay_script, '--apply'], check=True)

    print('\n完成。')


if __name__ == '__main__':
    main()
