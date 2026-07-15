---
name: compressing-large-context
description: Use when a task needs to inspect long build or test logs, 300+ lines of command output, 500+ lines of source code, broad repository search results, large generated JSON, or multi-file diffs; only activate when Headroom MCP tools are loaded and available.
---

# 压缩大上下文
## 触发参考
- 用户触发话术：`分析上千行编译日志` / `读取500行以上驱动源码` / `全仓检索代码定位问题` / `查看多文件大型diff变更` / `解析大容量JSON配置`
- 触发标志：任务涉及超大行数源码、长日志、批量仓库检索、多文件diff、大容量结构化JSON；优先限流缩小读取范围，自动调用headroom工具压缩文本，精准代码/故障定位时按需取回完整原文，长任务结束统计token节省数据。

本技能依托 Headroom MCP 对大容量文本做轻量化预处理，缩减上下文token占用；压缩后的精简文本仅用于宏观分析，**不可作为精确代码修改、字段校验、报错定位的唯一依据**，精准操作必须通过hash检索原始完整内容。

## 执行流程规则
1. 前置限流（优先执行，避免一次性加载超大内容）
    文件检索限定精确文件路径、关键词、行号范围；日志仅优先提取错误堆栈、异常摘要、失败关键信息，禁止无边界读取完整大文件。
2. 触发压缩判定
    满足以下任意条件时，调用 `mcp__headroom__headroom_compress` 处理文本：
    - 源码文件 ≥ 500 行
    - 日志/终端命令输出 ≥ 300 行
    - 全仓批量检索结果、多文件大型diff、大容量结构化JSON
3. 压缩后缓存逻辑
    使用压缩返回的hash值绑定原文，全程仅使用精简文本做分析，会话内不再重复加载同一份原始完整文本。
4. 精准内容回溯
    如需定位精确代码行、变量标识符、修改源码、核对协议/寄存器字段时，调用 `mcp__headroom__headroom_retrieve`；
    优先携带`query`关键词定向抽取片段，仅在必要时拉取完整原始文件。
5. 豁免场景（不执行压缩，必须保留原文）
    短代码片段、当前待编辑局部代码、协议定义字段、报错核心堆栈帧，直接使用原始文本，不做压缩处理。
6. 会话token统计收尾
    每一轮长工程任务结束后，强制调用 `mcp__headroom__headroom_stats`；
    以返回的 `tokens_saved` 总量与会话全局统计作为节省判断标准，不单独依赖单次压缩的`savings_percent`。

## 强制红线（不可违反）
1. 禁止先完整读取超大文件/无限制全仓搜索，再执行压缩；必须前置限流缩小读取范围。
2. 禁止将压缩摘要作为精确代码、硬件寄存器值、通信协议字段、报错行号的唯一判断依据。
3. 无有效内容hash时，不得声称可还原完整原始文本。
