# taskmgr 工作镜像

最后更新：2026-04-29。

本文件给未来接手本项目的 Codex 使用。扩展功能前先读 `AGENTS.md`、`README.md`、`TASK_INBOX.md` 和 `data/tasks.yaml`。

## 当前架构

旧的单文件 `task_appender.py` 已经被替换为包结构 CLI。现在 `task_appender.py` 只是兼容入口，真正实现位于 `taskmgr/`。

源码结构：

- `taskmgr/model.py`：任务 dataclass、合法任务类型、合法状态、共享异常。
- `taskmgr/store.py`：YAML 加载、保存、ID 分配、任务引用解析。
- `taskmgr/graph.py`：任务图校验、父子关系校验、依赖环检测。
- `taskmgr/render.py`：Mermaid、Graphviz DOT、Markdown 和自包含 HTML 导出。
- `taskmgr/recurrence.py`：每日任务 recurrence 校验、简单自然语言日期解析。
- `taskmgr/cli.py`：argparse CLI 入口。
- `task_appender.py`：兼容 wrapper，调用 `taskmgr.cli`。

数据和导出：

- `data/tasks.yaml`：任务图唯一数据源。
- `exports/graph.mmd`：Mermaid 图。
- `exports/graph.dot`：Graphviz DOT 图。
- `exports/tasks.md`：Markdown 任务摘要。
- `exports/graph.html`：可直接拖进浏览器查看的自包含 HTML 图。

## 数据模型

每个任务包含：

- `id`：任务 ID，例如 `T-0001`。
- `title`：任务标题。
- `kind`：任务类型，只能是 `short`、`long`、`daily`、`milestone`。
- `status`：任务状态，只能是 `todo`、`doing`、`blocked`、`done`、`archived`。
- `created_at`：创建日期。
- `due_at`：截止日期，可为空。
- `priority`：优先级，1 到 5。
- `tags`：标签列表。
- `parent`：父任务 ID，可为空。
- `depends_on`：前置依赖任务 ID 列表。
- `children`：子任务 ID 列表。
- `recurrence`：重复任务元数据，主要用于 `daily`。
- `notes`：备注。

关系语义：

- `parent` / `children` 表示目标拆解。
- `depends_on` 表示执行依赖。

依赖环会被 `validate` 和 `link` 拒绝。

## CLI 命令

入口：

```bash
python -m taskmgr.cli <command>
```

可用命令：

- `add`：新增任务。
- `list`：列出任务。
- `today`：列出今天需要关注的任务。
- `done`：标记任务完成。
- `link`：建立依赖。
- `unlink`：移除依赖。
- `validate`：校验任务图。
- `render`：导出 Mermaid、DOT、Markdown 或 HTML。
- `apply-inbox`：从 `TASK_INBOX.md` 解析自然语言任务。

## 校验命令

有意义的修改后运行：

```bash
python -m taskmgr.cli validate
python -m taskmgr.cli render --format mermaid
python -m unittest discover -s tests
python harness/run_harness.py
```

如果环境安装了 pytest，也运行：

```bash
python -m pytest
```

## 扩展原则

- 不要一开始做 GUI。
- 优先扩展 CLI 和测试。
- 不要绕过 store 层直接改数据，除非是在迁移或测试场景里。
- 新增命令时同步更新 `README.md`、`USAGE.md` 和测试。
