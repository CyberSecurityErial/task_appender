# taskmgr 使用说明

这个项目现在是一个包结构的任务图管理器。稳定操作入口是 CLI：

```bash
python -m taskmgr.cli <命令>
```

旧入口也保留了：

```bash
python task_appender.py <命令>
```

## 每天常用命令

最常用的启动方式：

```bash
cd /home/echo/vibe_tools/task_appender
./start_ui.sh
```

看到 `Open: http://127.0.0.1:8765/` 后，用浏览器打开这个地址。服务会占用当前终端；不用时按 `Ctrl-C` 停止。

查看所有任务：

```bash
python -m taskmgr.cli list
```

查看今天需要关注的任务：

```bash
python -m taskmgr.cli today
```

查看成长计分板：

```bash
python -m taskmgr.cli scoreboard
```

启动本地 UI：

```bash
./start_ui.sh
```

默认打开 `http://127.0.0.1:8765/`。服务模式可以写回 `data/tasks.yaml`：右键任务块修改状态或打开编辑表单，点击“新增任务”或在图空白处右键新建任务。编辑表单支持标题、类型、状态、截止、优先级、父任务、子任务、依赖、标签和备注。写入后会自动校验并重新生成全部导出文件；按 `Ctrl-Z` 可以撤销最近一次 UI 写入。

查看被前置任务阻塞的任务：

```bash
python -m taskmgr.cli list --blocked
```

校验任务图：

```bash
python -m taskmgr.cli validate
```

重新生成 Mermaid 图：

```bash
python -m taskmgr.cli render --format mermaid
```

生成可直接拖进浏览器查看的交互式 HTML 图：

```bash
python -m taskmgr.cli render --format html
```

生成成长计分板 HTML：

```bash
python -m taskmgr.cli render --format scoreboard
```

校验并重新生成全部导出：

```bash
python -m taskmgr.cli sync
```

## 新增任务

新增长期目标：

```bash
python -m taskmgr.cli add --kind long --title "系统学习 GPU 通信库设计" --tag nccl --tag rdma
```

新增短期任务：

```bash
python -m taskmgr.cli add --kind short --title "阅读 ncclTopoCompute" --due 2026-05-03 --tag nccl
```

新增子任务：

```bash
python -m taskmgr.cli add --kind short --title "整理拓扑搜索笔记" --parent T-0001 --due 2026-05-05 --tag nccl
```

新增每日任务：

```bash
python -m taskmgr.cli add --kind daily --title "每天复盘工程实验" --time "23:00" --tag daily
```

## 依赖关系

建立依赖关系：

```bash
python -m taskmgr.cli link --task T-0003 --depends-on T-0002
```

含义是：`T-0003` 依赖 `T-0002`，也就是要先完成 `T-0002`。

移除依赖关系：

```bash
python -m taskmgr.cli unlink --task T-0003 --depends-on T-0002
```

CLI 会拒绝形成环的依赖。

## 父子关系

把任务移动到新的父任务下面：

```bash
python -m taskmgr.cli move --task T-0003 --parent T-0001
```

把任务移动回根层级：

```bash
python -m taskmgr.cli move --task T-0003 --root
```

CLI 只更新子任务的 `parent` 字段，并自动重建父任务的 `children`，同时拒绝形成环的父子关系。

## 完成任务

```bash
python -m taskmgr.cli done T-0003
```

`done` 会记录 `completed_at`。`add`、`done`、`link`、`unlink`、`move`、`apply-inbox` 成功写入后会自动重建任务图、Markdown 摘要和成长计分板导出。默认任务库写到仓库 `exports/`；使用 `--db` 指向其他任务库时，写到该任务库旁边的 `exports/`。

## 成长系统

成长系统是 v0.1 的派生视图，不需要手工维护第二份数据：

- `done` / `archived` 任务会计入已获得 XP，并用于提取“我”的收获。
- `todo` / `doing` / `blocked` 任务会计入任务池待领取 XP。
- XP 由任务类型、优先级、依赖、子任务、标签和产出类型共同决定。
- 产出类型包括博客/文章、Demo/实验、源码地图、复盘/总结、工具/版本发布。
- v0.1.0rc1 起，技能以“星核主干”为根节点渲染成树，分支描述采用短句风格。
- 每个等级都有字符段位标志，完整等级谱会出现在 Markdown/HTML 导出的注脚。
- HTML 计分板输出到 `exports/scoreboard.html`。

## 从 TASK_INBOX.md 导入

先把自然语言任务写进 `TASK_INBOX.md`，例如：

```md
- 短期任务：本周日前完成 Triton autotune demo。 #triton
- 长期目标：系统学习 Mooncake 的 PD 分离和 KVCache 设计。 #mooncake
- 每日任务：每天晚上 11 点整理当天学到的一个系统知识点。 #daily
```

然后运行：

```bash
python -m taskmgr.cli apply-inbox TASK_INBOX.md
python -m taskmgr.cli validate
python -m taskmgr.cli render --format mermaid
```

## 导出文件

生成 Mermaid 图：

```bash
python -m taskmgr.cli render --format mermaid
```

生成 DOT 图：

```bash
python -m taskmgr.cli render --format dot
```

生成 Markdown 摘要：

```bash
python -m taskmgr.cli render --format markdown
```

生成自包含 HTML 图：

```bash
python -m taskmgr.cli render --format html
```

`exports/graph.html` 包含可拖拽任务块、自动重绘连线、搜索、类型/状态筛选、缩放和任务详情面板。手动调整后的布局会保存到浏览器 `localStorage`；重新生成 HTML 后，只要任务 ID 集合不变，同一浏览器会继续使用该布局。

直接打开 `exports/graph.html` 是静态模式，不能写任务库。需要 UI 新建任务或改状态时，运行：

```bash
./start_ui.sh
```

临时换端口：

```bash
PORT=8788 ./start_ui.sh
```

生成成长计分板 HTML：

```bash
python -m taskmgr.cli render --format scoreboard
```

一次生成全部导出：

```bash
python -m taskmgr.cli sync
```

对应输出：

- `exports/graph.mmd`
- `exports/graph.dot`
- `exports/tasks.md`
- `exports/graph.html`
- `exports/scoreboard.html`

## 测试

标准库测试：

```bash
python -m unittest discover -s tests
```

harness 场景测试：

```bash
python harness/run_harness.py
```

如果安装了 pytest：

```bash
python -m pytest
```

## 发布

每次发版本前都要更新 `RELEASE_NOTES.md`。`v0.1.1` 的 release note 是：支持了本地任务图 UI，而不是以前只能查看静态 graph。
