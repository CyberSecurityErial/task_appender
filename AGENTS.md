# 本仓库的 Codex 工作规则

你正在维护一个本地优先的个人任务图管理器。

每次进入仓库后，按下面顺序工作：

1. 先阅读 `README.md`、`TASK_INBOX.md` 和 `data/tasks.yaml`。
2. 优先使用 CLI 修改任务数据，不要直接手改任务库：
   - `python -m taskmgr.cli add ...`
   - `python -m taskmgr.cli link ...`
   - `python -m taskmgr.cli validate`
   - `python -m taskmgr.cli render --format mermaid`
   - `python -m taskmgr.cli render --format dot`
   - `python -m taskmgr.cli render --format markdown`
   - `python -m taskmgr.cli render --format html`
3. 除非用户明确要求，不要做 GUI。
4. 依赖图必须保持无环。
5. 每个任务必须包含：
   - `id`
   - `title`
   - `kind`
   - `status`
   - `created_at`
6. 任务类型只能是 `short`、`long`、`daily`、`milestone`。
7. 任务状态只能是 `todo`、`doing`、`blocked`、`done`、`archived`。
8. 用 `parent` / `children` 表达目标拆解，用 `depends_on` 表达执行依赖。
9. `daily` 任务必须包含 `recurrence` 元数据。
10. 禁止并行执行会写入任务库或导出文件的命令。所有 `add`、`link`、`unlink`、`done`、`apply-inbox`、`render` 必须串行运行，避免 ID 分配、父子关系、依赖关系或导出文件被覆盖。
11. `data/tasks.yaml` 是任务图源数据；`exports/graph.mmd`、`exports/graph.dot`、`exports/tasks.md`、`exports/graph.html` 都是它的依赖产物。任何任务数据、关系、渲染逻辑或任务模型变化后，必须重新生成全部导出文件，禁止只更新其中一个。
12. 修改代码或任务数据后，运行：
    - `python -m taskmgr.cli validate`
    - `python -m taskmgr.cli render --format mermaid`
    - `python -m taskmgr.cli render --format dot`
    - `python -m taskmgr.cli render --format markdown`
    - `python -m taskmgr.cli render --format html`
    - `python -m unittest discover -s tests`
    - 如果环境安装了 pytest，再运行 `python -m pytest`

完成标准：任务库校验通过、测试通过、`exports/graph.mmd`、`exports/graph.dot`、`exports/tasks.md`、`exports/graph.html` 全部已重新生成，并且没有遗漏任何由任务图变化触发的依赖产物。
