# 个人任务图管理器

这是一个本地优先的个人任务图管理器，适合配合 Codex 做长期维护。它不是 GUI 应用，而是一个可验证、可测试、可持续扩展的 CLI 工具。

## 核心概念

任务类型：

- `short`：短期可执行任务，通常应该有截止日期。
- `long`：长期目标或学习方向，不强制要求截止日期。
- `daily`：每日重复任务，必须有 recurrence 元数据。
- `milestone`：阶段性检查点，常用于长期目标或项目。

任务状态：

- `todo`：待办。
- `doing`：进行中。
- `blocked`：被阻塞。
- `done`：已完成。
- `archived`：已归档。

关系类型：

- `parent` / `children`：目标拆解关系，例如长期目标下面拆出多个短期任务。
- `depends_on`：执行依赖关系，例如任务 A 必须等任务 B 完成后才能做。

依赖图必须是无环图。

## 文件结构

任务数据存放在：

```text
data/tasks.yaml
```

导出文件存放在：

```text
exports/graph.mmd
exports/graph.dot
exports/tasks.md
exports/graph.html
exports/scoreboard.html
```

主要源码：

```text
taskmgr/model.py       # 任务模型
taskmgr/store.py       # YAML 读写和 ID 分配
taskmgr/graph.py       # 校验和环检测
taskmgr/analytics.py   # 收获提取、经验、等级和产出量化
taskmgr/render.py      # Mermaid / DOT / Markdown / HTML 导出
taskmgr/recurrence.py  # 每日任务和简单日期解析
taskmgr/cli.py         # CLI 入口
```

## 常用命令

新增长期目标：

```bash
python -m taskmgr.cli add --kind long --title "学习 Triton" --tag triton
```

新增短期任务，并挂到父任务下面：

```bash
python -m taskmgr.cli add --kind short --title "写 matmul demo" --parent T-0001 --due 2026-05-01 --tag triton
```

新增每日任务：

```bash
python -m taskmgr.cli add --kind daily --title "每天复盘工程实验" --time "23:00" --tag daily
```

建立执行依赖：

```bash
python -m taskmgr.cli link --task T-0002 --depends-on T-0001
```

调整父任务：

```bash
python -m taskmgr.cli move --task T-0002 --parent T-0001
python -m taskmgr.cli move --task T-0002 --root
```

查看任务：

```bash
python -m taskmgr.cli list
python -m taskmgr.cli list --blocked
python -m taskmgr.cli today
python -m taskmgr.cli scoreboard
```

校验和导出：

```bash
python -m taskmgr.cli validate
python -m taskmgr.cli render --format mermaid
python -m taskmgr.cli render --format dot
python -m taskmgr.cli render --format markdown
python -m taskmgr.cli render --format html
python -m taskmgr.cli render --format scoreboard
```

也可以一次完成校验和全部导出：

```bash
python -m taskmgr.cli sync
```

HTML 输出是自包含文件：

```text
exports/graph.html
exports/scoreboard.html
```

它们内嵌 SVG/HTML/CSS，不需要浏览器插件。`graph.html` 侧重任务图，`scoreboard.html` 侧重成长计分板、等级、经验、产出和已完成任务收获。

## v0.1 成长系统

v0.1 会从任务库自动推导两个激励视图：

- 已完成任务收获：从 `done` / `archived` 任务的标题、备注和标签中提取“我完成了什么、沉淀了什么”。
- 成长计分板：按任务类型、优先级、依赖复杂度、子任务数量、标签和产出类型计算 XP、等级、待领取经验、技能标签和产出数量。

`add`、`done`、`link`、`unlink`、`move`、`apply-inbox` 成功写入后会自动重建全部导出文件，保证计分板和任务图同步。默认任务库写到仓库 `exports/`；使用 `--db` 指向其他任务库时，写到该任务库旁边的 `exports/`。

## v0.1.0rc1 补丁

v0.1.0rc1 调整成长计分板表现：

- 技能标签改成单根技能树，从“星核主干”展开到输出、推理、工程和工具分支。
- 技能描述改为更短的科技/魔幻风格短句。
- 等级增加字符段位标志，例如 `{== V ==} Lv.5 任务图构建者`。
- Markdown 和 HTML 导出都会在注脚列出完整等级谱和对应字符标志。

从收件箱导入自然语言任务：

```bash
python -m taskmgr.cli apply-inbox TASK_INBOX.md
```

兼容入口仍然可用：

```bash
python task_appender.py validate
```

## Codex 工作流

当你让 Codex 更新任务时，推荐这样说：

```text
先读 AGENTS.md，然后把 TASK_INBOX.md 里的任务应用到任务图。
使用 CLI，不要直接改 data/tasks.yaml。
完成后运行 validate、render 和测试。
```

Codex 应该优先通过 CLI 修改任务图。只有当 CLI 缺少必要能力时，才允许补充最小功能或直接编辑数据文件。
