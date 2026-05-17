# taskmgr 工作镜像

最后更新：2026-05-17。

本文件给未来接手本项目的 Codex 使用。扩展功能前先读 `AGENTS.md`、`README.md`、`TASK_INBOX.md` 和 `data/tasks.yaml`。

## 当前架构

旧的单文件 `task_appender.py` 已经被替换为包结构 CLI。现在 `task_appender.py` 只是兼容入口，真正实现位于 `taskmgr/`。

源码结构：

- `taskmgr/model.py`：任务 dataclass、合法任务类型、合法状态、共享异常。
- `taskmgr/store.py`：YAML 加载、保存、ID 分配、任务引用解析。
- `taskmgr/graph.py`：任务图校验、父子关系校验、依赖环检测。
- `taskmgr/render.py`：Mermaid、Graphviz DOT、Markdown、自包含 HTML 图 UI 和成长计分板导出。
- `taskmgr/recurrence.py`：每日任务 recurrence 校验、简单自然语言日期解析。
- `taskmgr/cli.py`：argparse CLI 入口。
- `task_appender.py`：兼容 wrapper，调用 `taskmgr.cli`。

数据和导出：

- `data/tasks.yaml`：任务图唯一数据源。
- `exports/graph.mmd`：Mermaid 图。
- `exports/graph.dot`：Graphviz DOT 图。
- `exports/tasks.md`：Markdown 任务摘要。
- `exports/graph.html`：可直接拖进浏览器查看的自包含交互式 HTML 图，任务块可拖拽，连线跟随重绘，布局保存到浏览器 localStorage。

## 2026-05-17 工作镜像

当前分支：`refactor-draggable-ui-20260517-2228`。

本轮重构目标是把用户不满意的静态任务图升级成一个最小可用 UI。已采取的方向：

- 不改 `data/tasks.yaml` 模型，不引入前端构建依赖，仍由 `python -m taskmgr.cli render --format html` 生成单文件 HTML。
- `taskmgr/render.py` 的 `graph.html` 导出现在包含工具栏、筛选、缩放、任务详情面板和内联 JS。
- SVG 任务节点改为带 `data-*` 元数据的 `.task-node`，支持鼠标/触控拖动和键盘方向键微调；父子/依赖连线用 `.graph-edge` 按节点位置实时重算。
- 手动布局写入浏览器 `localStorage`，布局 key 基于任务 ID 集合；重新生成 HTML 后，只要任务集合不变，同一浏览器会继续载入旧布局。
- 测试中加入了 `data-task-graph-ui`、`.task-node` 和 `save-layout` 断言，防止交互 UI 被退化成静态 SVG。

追加一轮 UI 写入能力：

- 新增 `python -m taskmgr.cli serve`，默认服务地址 `http://127.0.0.1:8765/`。
- 平时启动方式固定为仓库根目录下的 `./start_ui.sh`。脚本使用 `python3 -m taskmgr.cli serve --host ${HOST:-127.0.0.1} --port ${PORT:-8765}`，并在终端打印浏览器地址。
- 新增 `taskmgr/server.py`，用标准库 `HTTPServer` 提供本地页面和 `/api/tasks` 写接口；服务器单线程处理请求，避免并行写任务库和导出文件。
- 服务模式的任务图支持右键任务块修改状态，右键“编辑任务”可修改标题、类型、状态、截止、优先级、父任务、子任务、依赖、标签和备注；点击“新增任务”或右键图空白区域新建任务。写入路径复用 `Task`、`allocate_id`、`normalize_for_save`、`validate_data` 和全量导出重建。
- UI 写入前会把当前 `data/tasks.yaml` 文本压入服务内存 undo 栈，最多保留 20 步。浏览器中按 `Ctrl-Z` 或点“撤销”会调用 `/api/undo` 恢复最近一次 UI 写入并重建全部导出。服务重启后 undo 栈清空。
- 静态 `exports/graph.html` 仍可拖动和保存浏览器本地布局，但不会直接写 `data/tasks.yaml`；需要写任务库时使用 `serve`。
- 原有 CLI 创建/修改方式保留：`add`、`done`、`link`、`unlink`、`move`、`apply-inbox` 没有被替换。

发布记录：

- `v0.1.1` 的 release note 写在 `RELEASE_NOTES.md`：支持了本地任务图 UI，而不是以前只能查看静态 graph。
- 以后每次发版本都必须更新 `RELEASE_NOTES.md`。

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
