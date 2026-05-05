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

生成可直接拖进浏览器查看的 HTML 图：

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
