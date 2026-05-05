from __future__ import annotations

import html
from datetime import date
from pathlib import Path
from typing import Any

from .analytics import build_progress, format_skill_tree_cli
from .model import task_sort_key


KIND_LABELS = {
    "short": "短期",
    "long": "长期",
    "daily": "每日",
    "milestone": "里程碑",
}

STATUS_LABELS = {
    "todo": "待办",
    "doing": "进行中",
    "blocked": "被阻塞",
    "done": "已完成",
    "archived": "已归档",
}


def render_mermaid(data: dict[str, Any]) -> str:
    tasks = sorted(data.get("tasks", []), key=lambda task: str(task.get("id", "")))
    if not tasks:
        return "flowchart LR\n  empty[\"No tasks\"]\n"

    by_id = {task["id"]: task for task in tasks}
    lines = [
        "flowchart LR",
        "  classDef long fill:#e0f2fe,stroke:#0369a1,stroke-width:2px,color:#0f172a;",
        "  classDef milestone fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#422006;",
        "  classDef daily fill:#dcfce7,stroke:#16a34a,color:#14532d;",
        "  classDef short fill:#fff7ed,stroke:#ea580c,color:#1f2937;",
        "  classDef done fill:#f1f5f9,stroke:#94a3b8,color:#64748b;",
    ]

    rendered: set[str] = set()
    parents = [
        task
        for task in tasks
        if not task.get("parent") and any(child_id in by_id for child_id in task.get("children", []))
    ]
    for parent in parents:
        lines.append(f'  subgraph SG_{safe_node(parent["id"])}["{escape(parent["id"] + " " + parent["title"])}"]')
        lines.append("    direction TB")
        lines.append(f"    {node_line(parent)}")
        rendered.add(parent["id"])
        for child_id in parent.get("children", []):
            child = by_id.get(child_id)
            if child:
                lines.append(f"    {node_line(child)}")
                rendered.add(child_id)
        lines.append("  end")

    for task in tasks:
        if task["id"] not in rendered:
            lines.append(f"  {node_line(task)}")
            rendered.add(task["id"])

    for task in tasks:
        class_name = "done" if task.get("status") in {"done", "archived"} else task.get("kind", "short")
        lines.append(f"  class {safe_node(task['id'])} {class_name};")

    edge_styles: list[str] = []
    for task in tasks:
        for child_id in task.get("children", []):
            if child_id in by_id:
                lines.append(f"  {safe_node(task['id'])} --> {safe_node(child_id)}")
                edge_styles.append("stroke:#2563eb,stroke-width:1.6px")
        for dependency in task.get("depends_on", []):
            if dependency in by_id:
                lines.append(f"  {safe_node(dependency)} -.-> {safe_node(task['id'])}")
                edge_styles.append("stroke:#d97706,stroke-width:1.8px,stroke-dasharray:6 4")

    for index, style in enumerate(edge_styles):
        lines.append(f"  linkStyle {index} {style};")
    return "\n".join(lines) + "\n"


def render_dot(data: dict[str, Any]) -> str:
    tasks = sorted(data.get("tasks", []), key=lambda task: str(task.get("id", "")))
    lines = [
        "digraph Tasks {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor="#f8fafc", color="#475569"];',
    ]
    for task in tasks:
        label = escape_dot(f'{task["id"]}\\n{task["title"]}')
        lines.append(f'  "{task["id"]}" [label="{label}"];')
    for task in tasks:
        for child_id in task.get("children", []):
            lines.append(f'  "{task["id"]}" -> "{child_id}" [color="#2563eb", label="child"];')
        for dependency in task.get("depends_on", []):
            lines.append(f'  "{dependency}" -> "{task["id"]}" [style=dashed, color="#d97706", label="depends"];')
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_markdown(data: dict[str, Any]) -> str:
    progress = build_progress(data)
    level = progress["level"]
    lines = [
        "# 任务列表",
        "",
        "## 成长计分板",
        "",
        f"- 等级：{level['badge']} Lv.{level['level']} {level['title']}",
        f"- 段位铭文：{level['motto']}",
        f"- 已获得经验：{progress['earned_xp']} XP",
        f"- 下一级进度：{level['current_xp']}/{level['next_level_xp']} XP，还差 {level['remaining_xp']} XP",
        f"- 任务完成：{progress['completed_tasks']}/{progress['total_tasks']}（{progress['completion_rate']}%）",
        f"- 任务池待领取：{progress['available_xp']} XP",
    ]
    if progress["artifacts"]:
        artifacts = "；".join(f"{item['label']} x{item['count']}（+{item['xp']} XP）" for item in progress["artifacts"])
        lines.append(f"- 产出：{artifacts}")
    lines.extend(["", "## 技能树", "", "```text"])
    lines.extend(format_skill_tree_cli(progress["skill_tree"]))
    lines.append("```")

    lines.extend(["", "## 已完成任务收获", ""])
    if progress["gains"]:
        for gain in progress["gains"]:
            tags = " ".join(f"`{tag}`" for tag in gain["tags"]) or "-"
            artifacts = "，".join(gain["artifacts"]) or "-"
            lines.append(f"- **{gain['task_id']}** {gain['area']}：{gain['gain']}（+{gain['xp']} XP）")
            lines.append(f"  证据：{gain['evidence']}；产出：{artifacts}；标签：{tags}")
    else:
        lines.append("- 暂无已完成任务收获。")

    lines.extend(["", "## 任务明细", ""])
    for task in sorted(data.get("tasks", []), key=task_sort_key):
        tags = " ".join(f"`{tag}`" for tag in task.get("tags", [])) or "-"
        due = task.get("due_at") or "-"
        status = STATUS_LABELS.get(task.get("status"), task.get("status"))
        kind = KIND_LABELS.get(task.get("kind"), task.get("kind"))
        lines.append(f"- **{task['id']}** [{status}/{kind}] {task['title']}")
        completed_at = task.get("completed_at") or "-"
        lines.append(f"  截止：{due}；完成：{completed_at}；优先级：{task.get('priority', 3)}；标签：{tags}")
        if task.get("depends_on"):
            lines.append(f"  前置依赖：{', '.join(task['depends_on'])}")
        if task.get("children"):
            lines.append(f"  子任务：{', '.join(task['children'])}")
    lines.extend(["", "## 等级谱注脚", ""])
    for row in progress["level_catalog"]:
        lines.append(f"- {row['badge']} Lv.{row['level']} {row['title']}：{row['motto']}；{row['min_xp']} XP 起")
    return "\n".join(lines) + "\n"


def write_rendered(data: dict[str, Any], fmt: str, output: Path) -> str:
    if fmt == "mermaid":
        content = render_mermaid(data)
    elif fmt == "dot":
        content = render_dot(data)
    elif fmt == "markdown":
        content = render_markdown(data)
    elif fmt == "html":
        content = render_html(data)
    elif fmt == "scoreboard":
        content = render_scoreboard_html(data)
    else:
        raise ValueError(f"unsupported render format: {fmt}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return content


def render_html(data: dict[str, Any]) -> str:
    tasks = sorted(data.get("tasks", []), key=lambda task: str(task.get("id", "")))
    progress = build_progress(data)
    svg = render_svg_graph(data)
    task_rows = "\n".join(render_html_task_row(task) for task in sorted(tasks, key=task_sort_key))
    counts = count_by(tasks, "kind")
    status_counts = count_by(tasks, "status")
    today = date.today().isoformat()
    level = progress["level"]
    progress_sections = render_progress_sections(progress)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>任务关系图</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --line: #cbd5e1;
      --text: #0f172a;
      --muted: #64748b;
      --blue: #2563eb;
      --orange: #d97706;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    }}
    header {{
      padding: 24px 28px 14px;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      border-bottom: 1px solid #e2e8f0;
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .meta {{ color: var(--muted); }}
    .summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .pill {{
      display: inline-flex;
      gap: 6px;
      align-items: center;
      padding: 6px 10px;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      background: #fff;
      color: #334155;
      white-space: nowrap;
    }}
    main {{ padding: 18px 28px 32px; }}
    .graph-shell {{
      overflow: auto;
      background: var(--panel);
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
    }}
    .graph-shell svg {{ display: block; min-width: 100%; }}
    .legend {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 14px 0 22px;
      color: #334155;
    }}
    .legend span {{ display: inline-flex; align-items: center; gap: 7px; }}
    .swatch {{
      width: 22px;
      height: 0;
      border-top: 3px solid currentColor;
      display: inline-block;
    }}
    .dependency {{ color: var(--orange); border-top-style: dashed; }}
    .child {{ color: var(--blue); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      overflow: hidden;
    }}
    th, td {{
      padding: 9px 10px;
      border-bottom: 1px solid #e2e8f0;
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #f1f5f9; color: #334155; font-weight: 650; }}
    tr:last-child td {{ border-bottom: 0; }}
    code {{
      background: #f1f5f9;
      padding: 1px 5px;
      border-radius: 5px;
      color: #334155;
    }}
    @media print {{
      body {{ background: #fff; }}
      header, main {{ padding: 12px; }}
      .graph-shell {{ overflow: visible; box-shadow: none; }}
    }}
{progress_css()}
  </style>
</head>
<body>
  <header>
    <h1>任务关系图</h1>
    <div class="meta">生成日期：{html.escape(today)}；数据源：<code>data/tasks.yaml</code>；文本图：<code>exports/graph.mmd</code> / <code>exports/graph.dot</code></div>
    <div class="summary">
      <span class="pill">总任务 {len(tasks)}</span>
      <span class="pill">短期 {counts.get("short", 0)}</span>
      <span class="pill">长期 {counts.get("long", 0)}</span>
      <span class="pill">每日 {counts.get("daily", 0)}</span>
      <span class="pill">里程碑 {counts.get("milestone", 0)}</span>
      <span class="pill">待办 {status_counts.get("todo", 0)}</span>
      <span class="pill">进行中 {status_counts.get("doing", 0)}</span>
      <span class="pill">已完成 {status_counts.get("done", 0)}</span>
      <span class="pill">{html.escape(str(level["badge"]))} Lv.{level["level"]} {html.escape(str(level["title"]))}</span>
      <span class="pill">经验 {progress["earned_xp"]} XP</span>
    </div>
  </header>
  <main>
{progress_sections}
    <div class="legend">
      <span><i class="swatch child"></i>父子拆解</span>
      <span><i class="swatch dependency"></i>执行依赖</span>
      <span>横向滚动可查看完整图；浏览器缩放可放大细节。</span>
    </div>
    <section class="graph-shell">
{svg}
    </section>
    <h2>任务明细</h2>
    <table>
      <thead>
        <tr><th>ID</th><th>状态</th><th>类型</th><th>截止</th><th>标题</th><th>前置依赖</th><th>子任务</th><th>标签</th></tr>
      </thead>
      <tbody>
{task_rows}
      </tbody>
    </table>
  </main>
</body>
</html>
"""


def render_scoreboard_html(data: dict[str, Any]) -> str:
    progress = build_progress(data)
    today = date.today().isoformat()
    level = progress["level"]
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>成长计分板</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f8fafc;
      --panel: #ffffff;
      --line: #cbd5e1;
      --text: #0f172a;
      --muted: #64748b;
      --blue: #2563eb;
      --orange: #d97706;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
    }}
    header {{
      padding: 24px 28px 14px;
      background: #ffffff;
      border-bottom: 1px solid #e2e8f0;
    }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .meta {{ color: var(--muted); }}
    main {{ padding: 18px 28px 32px; }}
    code {{
      background: #f1f5f9;
      padding: 1px 5px;
      border-radius: 5px;
      color: #334155;
    }}
{progress_css()}
  </style>
</head>
<body>
  <header>
    <h1>成长计分板</h1>
    <div class="meta">生成日期：{html.escape(today)}；等级：{html.escape(str(level["badge"]))} Lv.{level["level"]} {html.escape(str(level["title"]))}；数据源：<code>data/tasks.yaml</code></div>
  </header>
  <main>
{render_progress_sections(progress)}
  </main>
</body>
</html>
"""


def progress_css() -> str:
    return """
    .progress-shell {
      display: grid;
      gap: 14px;
      margin: 0 0 22px;
    }
    .score-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(160px, 1fr));
      gap: 10px;
    }
    .score-card {
      background: var(--panel);
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px 14px;
      min-height: 92px;
    }
    .score-label {
      margin: 0 0 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .score-value {
      margin: 0;
      color: #111827;
      font-size: 24px;
      font-weight: 750;
      letter-spacing: 0;
    }
    .score-note {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 12px;
    }
    .rank-badge {
      display: inline-block;
      margin: 2px 0 4px;
      padding: 3px 7px;
      border: 1px solid #2563eb;
      border-radius: 6px;
      color: #1d4ed8;
      background: #eff6ff;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .level-bar {
      height: 10px;
      margin-top: 10px;
      overflow: hidden;
      border-radius: 999px;
      background: #e2e8f0;
    }
    .level-fill {
      height: 100%;
      background: linear-gradient(90deg, #2563eb, #16a34a);
    }
    .progress-columns {
      display: grid;
      grid-template-columns: minmax(260px, 1.05fr) minmax(300px, 1.4fr);
      gap: 12px;
    }
    .progress-panel {
      background: var(--panel);
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 14px;
    }
    .progress-panel h2 {
      margin: 0 0 10px;
      font-size: 17px;
      letter-spacing: 0;
    }
    .compact-table {
      width: 100%;
      border-collapse: collapse;
      border: 0;
      background: transparent;
    }
    .compact-table th,
    .compact-table td {
      padding: 7px 6px;
      border-bottom: 1px solid #e2e8f0;
      text-align: left;
      vertical-align: top;
    }
    .compact-table th {
      background: #f8fafc;
      color: #334155;
      font-weight: 650;
    }
    .compact-table tr:last-child td {
      border-bottom: 0;
    }
    .gain-list {
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .gain-item {
      padding: 10px 0;
      border-bottom: 1px solid #e2e8f0;
    }
    .gain-item:last-child {
      border-bottom: 0;
    }
    .gain-head {
      display: flex;
      gap: 8px;
      align-items: baseline;
      justify-content: space-between;
      color: #111827;
      font-weight: 700;
    }
    .gain-body {
      margin: 5px 0;
      color: #334155;
    }
    .gain-meta {
      color: var(--muted);
      font-size: 12px;
    }
    .skill-tree {
      margin-top: 14px;
    }
    .skill-tree h3,
    .rank-footnote h3 {
      margin: 0 0 9px;
      font-size: 15px;
    }
    .skill-tree ul {
      margin: 0;
      padding-left: 18px;
      list-style: none;
      border-left: 1px solid #dbe3ef;
    }
    .skill-tree > ul {
      padding-left: 0;
      border-left: 0;
    }
    .skill-tree li {
      position: relative;
      margin: 8px 0;
      padding-left: 12px;
    }
    .skill-tree li::before {
      content: "";
      position: absolute;
      left: -18px;
      top: 13px;
      width: 18px;
      border-top: 1px solid #dbe3ef;
    }
    .skill-tree > ul > li::before {
      display: none;
    }
    .skill-node {
      display: grid;
      gap: 2px;
      padding: 8px 9px;
      border: 1px solid #e2e8f0;
      border-radius: 7px;
      background: #f8fafc;
    }
    .skill-node.locked {
      opacity: 0.64;
    }
    .skill-node-title {
      display: flex;
      gap: 8px;
      justify-content: space-between;
      color: #111827;
      font-weight: 700;
    }
    .skill-node-desc {
      color: var(--muted);
      font-size: 12px;
    }
    .rank-footnote {
      margin-top: 14px;
      padding: 12px 14px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: var(--panel);
    }
    .rank-catalog {
      display: grid;
      grid-template-columns: repeat(2, minmax(220px, 1fr));
      gap: 7px 12px;
    }
    .rank-row {
      display: flex;
      gap: 8px;
      align-items: baseline;
      color: #334155;
      font-size: 12px;
    }
    .rank-row code {
      min-width: 72px;
      text-align: center;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    @media (max-width: 920px) {
      .score-grid,
      .progress-columns,
      .rank-catalog {
        grid-template-columns: 1fr;
      }
    }
"""


def render_progress_sections(progress: dict[str, Any]) -> str:
    level = progress["level"]
    progress_pct = max(0.0, min(100.0, float(level["progress_pct"])))
    return f"""    <section class="progress-shell" aria-label="成长计分板">
      <div class="score-grid">
        <article class="score-card">
          <p class="score-label">等级</p>
          <span class="rank-badge">{html.escape(str(level["badge"]))}</span>
          <p class="score-value">Lv.{level["level"]}</p>
          <p class="score-note">{html.escape(str(level["title"]))}</p>
          <p class="score-note">{html.escape(str(level["motto"]))}</p>
          <div class="level-bar" aria-label="升级进度"><div class="level-fill" style="width: {progress_pct}%"></div></div>
          <p class="score-note">{level["current_xp"]}/{level["next_level_xp"]} XP，还差 {level["remaining_xp"]}</p>
        </article>
        <article class="score-card">
          <p class="score-label">已获得经验</p>
          <p class="score-value">{progress["earned_xp"]}</p>
          <p class="score-note">来自已完成和已归档任务</p>
        </article>
        <article class="score-card">
          <p class="score-label">任务完成</p>
          <p class="score-value">{progress["completed_tasks"]}/{progress["total_tasks"]}</p>
          <p class="score-note">完成率 {progress["completion_rate"]}%</p>
        </article>
        <article class="score-card">
          <p class="score-label">任务池经验</p>
          <p class="score-value">{progress["available_xp"]}</p>
          <p class="score-note">待办、进行中和阻塞任务可领取</p>
        </article>
      </div>
      <div class="progress-columns">
        <section class="progress-panel">
          <h2>产出量化</h2>
          <table class="compact-table">
            <thead><tr><th>产出</th><th>数量</th><th>经验</th></tr></thead>
            <tbody>
{render_artifact_rows(progress)}
            </tbody>
          </table>
          <div class="skill-tree">
            <h3>技能树</h3>
{render_skill_tree_html(progress["skill_tree"])}
          </div>
        </section>
        <section class="progress-panel">
          <h2>已完成任务收获</h2>
{render_gain_list(progress)}
        </section>
      </div>
{render_level_footnote_html(progress)}
    </section>"""


def render_artifact_rows(progress: dict[str, Any]) -> str:
    if not progress["artifacts"]:
        return '              <tr><td colspan="3">暂无可量化产出</td></tr>'
    rows = []
    for item in progress["artifacts"]:
        rows.append(
            "              <tr>"
            f"<td>{html.escape(str(item['label']))}</td>"
            f"<td>{item['count']}</td>"
            f"<td>+{item['xp']} XP</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render_skill_tree_html(node: dict[str, Any]) -> str:
    return "            <ul>\n" + render_skill_node_html(node, 14) + "\n            </ul>"


def render_skill_node_html(node: dict[str, Any], indent: int) -> str:
    pad = " " * indent
    state_class = "" if node.get("unlocked") else " locked"
    state = "解锁" if node.get("unlocked") else "封印"
    parts = [
        f'{pad}<li>',
        f'{pad}  <div class="skill-node{state_class}">',
        f'{pad}    <div class="skill-node-title"><span>{html.escape(str(node["label"]))}</span><span>{state} · {node["xp"]} XP</span></div>',
        f'{pad}    <div class="skill-node-desc">{html.escape(str(node["description"]))}</div>',
        f'{pad}  </div>',
    ]
    children = node.get("children", [])
    if children:
        parts.append(f"{pad}  <ul>")
        for child in children:
            parts.append(render_skill_node_html(child, indent + 4))
        parts.append(f"{pad}  </ul>")
    parts.append(f"{pad}</li>")
    return "\n".join(parts)


def render_level_footnote_html(progress: dict[str, Any]) -> str:
    rows = []
    for row in progress["level_catalog"]:
        rows.append(
            "          <div class=\"rank-row\">"
            f"<code>{html.escape(str(row['badge']))}</code>"
            f"<span>Lv.{row['level']} {html.escape(str(row['title']))}，{html.escape(str(row['motto']))}，{row['min_xp']} XP 起</span>"
            "</div>"
        )
    return (
        "      <footer class=\"rank-footnote\">\n"
        "        <h3>等级谱注脚</h3>\n"
        "        <div class=\"rank-catalog\">\n"
        + "\n".join(rows)
        + "\n        </div>\n"
        "      </footer>"
    )


def render_gain_list(progress: dict[str, Any]) -> str:
    if not progress["gains"]:
        return '          <p class="gain-body">暂无已完成任务收获。</p>'
    items = []
    for gain in progress["gains"][:12]:
        tags = " ".join(f"#{tag}" for tag in gain["tags"]) or "-"
        artifacts = "，".join(gain["artifacts"]) or "-"
        items.append(
            "          <li class=\"gain-item\">"
            "<div class=\"gain-head\">"
            f"<span>{html.escape(gain['task_id'])} · {html.escape(gain['area'])}</span>"
            f"<span>+{gain['xp']} XP</span>"
            "</div>"
            f"<p class=\"gain-body\">{html.escape(gain['gain'])}</p>"
            f"<div class=\"gain-meta\">{html.escape(gain['title'])}；证据：{html.escape(gain['evidence'])}；产出：{html.escape(artifacts)}；标签：{html.escape(tags)}</div>"
            "</li>"
        )
    return "          <ul class=\"gain-list\">\n" + "\n".join(items) + "\n          </ul>"


def render_svg_graph(data: dict[str, Any]) -> str:
    tasks = sorted(data.get("tasks", []), key=lambda task: str(task.get("id", "")))
    if not tasks:
        return '      <svg viewBox="0 0 760 220" width="760" height="220" role="img" aria-label="空任务图"><text x="40" y="90" fill="#64748b">暂无任务</text></svg>'

    by_id = {task["id"]: task for task in tasks}
    grouped_ids: set[str] = set()
    sections: list[tuple[str, list[dict[str, Any]]]] = []
    for task in tasks:
        children = [by_id[child_id] for child_id in task.get("children", []) if child_id in by_id]
        if not task.get("parent") and children:
            group_tasks = [task, *children]
            sections.append((f'{task["id"]} {task["title"]}', group_tasks))
            grouped_ids.update(child["id"] for child in group_tasks)

    standalone = [task for task in tasks if task["id"] not in grouped_ids]
    if standalone:
        sections.append(("独立任务和跨组依赖", standalone))

    positions: dict[str, tuple[int, int]] = {}
    section_boxes: list[tuple[str, int, int, int, int]] = []
    width = 1120
    y_cursor = 30
    node_w = 230
    node_h = 86
    x_gap = 285
    y_gap = 122
    left = 48

    for title, section_tasks in sections:
        section_ids = {task["id"] for task in section_tasks}
        levels = compute_section_levels(section_tasks, by_id, section_ids)
        rows_by_level: dict[int, int] = {}
        max_level = max(levels.values(), default=0)
        for task in sorted(section_tasks, key=lambda item: (levels[item["id"]], item["id"])):
            level = levels[task["id"]]
            row = rows_by_level.get(level, 0)
            rows_by_level[level] = row + 1
            x = left + level * x_gap
            y = y_cursor + 72 + row * y_gap
            positions[task["id"]] = (x, y)
        max_rows = max(rows_by_level.values(), default=1)
        section_w = max(760, left * 2 + (max_level + 1) * node_w + max_level * (x_gap - node_w))
        section_h = 112 + max_rows * y_gap
        section_boxes.append((title, 24, y_cursor, section_w, section_h))
        width = max(width, section_w + 48)
        y_cursor += section_h + 36

    height = max(260, y_cursor + 20)
    parts = [
        f'      <svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="任务关系图">',
        "        <defs>",
        '          <marker id="arrow-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#2563eb"/></marker>',
        '          <marker id="arrow-orange" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#d97706"/></marker>',
        "        </defs>",
    ]
    for title, x, y, w, h in section_boxes:
        parts.append(f'        <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#f8fafc" stroke="#dbe3ef"/>')
        parts.append(f'        <text x="{x + 18}" y="{y + 31}" fill="#334155" font-size="17" font-weight="700">{svg_escape(title)}</text>')

    parts.extend(render_svg_edges(tasks, by_id, positions, node_w, node_h))
    for task in tasks:
        if task["id"] in positions:
            parts.append(render_svg_node(task, *positions[task["id"]], node_w, node_h))
    parts.append("      </svg>")
    return "\n".join(parts)


def compute_section_levels(
    section_tasks: list[dict[str, Any]], by_id: dict[str, dict[str, Any]], section_ids: set[str]
) -> dict[str, int]:
    levels: dict[str, int] = {}

    def level_of(task_id: str, stack: set[str] | None = None) -> int:
        if task_id in levels:
            return levels[task_id]
        stack = stack or set()
        if task_id in stack:
            return 0
        task = by_id[task_id]
        parents: list[str] = []
        if task.get("parent") in section_ids:
            parents.append(task["parent"])
        parents.extend(ref for ref in task.get("depends_on", []) if ref in section_ids)
        if not parents:
            levels[task_id] = 0
            return 0
        value = max(level_of(ref, stack | {task_id}) + 1 for ref in parents)
        levels[task_id] = value
        return value

    for task in section_tasks:
        level_of(task["id"])
    return levels


def render_svg_edges(
    tasks: list[dict[str, Any]],
    by_id: dict[str, dict[str, Any]],
    positions: dict[str, tuple[int, int]],
    node_w: int,
    node_h: int,
) -> list[str]:
    parts: list[str] = []
    for task in tasks:
        start = positions.get(task["id"])
        if not start:
            continue
        for child_id in task.get("children", []):
            if child_id in by_id and child_id in positions:
                parts.append(svg_edge(start, positions[child_id], node_w, node_h, "#2563eb", "arrow-blue", dashed=False))
        for dependency in task.get("depends_on", []):
            if dependency in by_id and dependency in positions:
                parts.append(svg_edge(positions[dependency], start, node_w, node_h, "#d97706", "arrow-orange", dashed=True))
    return parts


def svg_edge(
    start: tuple[int, int],
    end: tuple[int, int],
    node_w: int,
    node_h: int,
    color: str,
    marker: str,
    *,
    dashed: bool,
) -> str:
    x1 = start[0] + node_w
    y1 = start[1] + node_h // 2
    x2 = end[0]
    y2 = end[1] + node_h // 2
    if x2 <= x1:
        x1 = start[0] + node_w // 2
        y1 = start[1] + node_h
        x2 = end[0] + node_w // 2
        y2 = end[1]
    mid = max(x1 + 42, (x1 + x2) // 2)
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    return (
        f'        <path d="M {x1} {y1} C {mid} {y1}, {mid} {y2}, {x2} {y2}" '
        f'fill="none" stroke="{color}" stroke-width="2.2"{dash} marker-end="url(#{marker})" opacity="0.9"/>'
    )


def render_svg_node(task: dict[str, Any], x: int, y: int, width: int, height: int) -> str:
    fill, stroke = svg_node_colors(task)
    title_lines = split_display_text(str(task.get("title", "")), 22, 2)
    status = STATUS_LABELS.get(task.get("status"), task.get("status"))
    kind = KIND_LABELS.get(task.get("kind"), task.get("kind"))
    due = short_due(task.get("due_at"))
    tags = " ".join(f"#{tag}" for tag in task.get("tags", [])[:2])
    text_parts = [
        f'        <g id="{svg_escape(safe_node(task["id"]))}">',
        f'          <rect x="{x}" y="{y}" width="{width}" height="{height}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="2"/>',
        f'          <text x="{x + 14}" y="{y + 21}" fill="#0f172a" font-size="14" font-weight="700">{svg_escape(task["id"])}</text>',
        f'          <text x="{x + width - 14}" y="{y + 21}" text-anchor="end" fill="#475569" font-size="12">{svg_escape(str(status))}/{svg_escape(str(kind))}</text>',
    ]
    title_y = y + 43
    for index, line in enumerate(title_lines):
        text_parts.append(f'          <text x="{x + 14}" y="{title_y + index * 17}" fill="#111827" font-size="14">{svg_escape(line)}</text>')
    meta = f"{due}" + (f" · {tags}" if tags else "")
    text_parts.append(f'          <text x="{x + 14}" y="{y + height - 13}" fill="#64748b" font-size="12">{svg_escape(meta)}</text>')
    text_parts.append("        </g>")
    return "\n".join(text_parts)


def svg_node_colors(task: dict[str, Any]) -> tuple[str, str]:
    if task.get("status") in {"done", "archived"}:
        return "#f1f5f9", "#94a3b8"
    kind = task.get("kind")
    if kind == "long":
        return "#e0f2fe", "#0369a1"
    if kind == "milestone":
        return "#fef3c7", "#d97706"
    if kind == "daily":
        return "#dcfce7", "#16a34a"
    return "#fff7ed", "#ea580c"


def render_html_task_row(task: dict[str, Any]) -> str:
    tags = " ".join(f"<code>{html.escape(str(tag))}</code>" for tag in task.get("tags", [])) or "-"
    return (
        "        <tr>"
        f"<td><code>{html.escape(str(task.get('id', '')))}</code></td>"
        f"<td>{html.escape(str(STATUS_LABELS.get(task.get('status'), task.get('status'))))}</td>"
        f"<td>{html.escape(str(KIND_LABELS.get(task.get('kind'), task.get('kind'))))}</td>"
        f"<td>{html.escape(str(task.get('due_at') or '-'))}</td>"
        f"<td>{html.escape(str(task.get('title', '')))}</td>"
        f"<td>{html.escape(', '.join(task.get('depends_on', [])) or '-')}</td>"
        f"<td>{html.escape(', '.join(task.get('children', [])) or '-')}</td>"
        f"<td>{tags}</td>"
        "</tr>"
    )


def count_by(tasks: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(task.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def split_display_text(value: str, max_units: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    current_units = 0
    for char in value:
        units = 2 if ord(char) > 127 else 1
        if current and current_units + units > max_units:
            lines.append(current)
            current = char
            current_units = units
            if len(lines) == max_lines:
                break
        else:
            current += char
            current_units += units
    if len(lines) < max_lines and current:
        lines.append(current)
    if not lines:
        return [""]
    consumed = "".join(lines)
    if len(consumed) < len(value):
        lines[-1] = truncate_display_text(lines[-1], max_units - 2) + "..."
    return lines


def truncate_display_text(value: str, max_units: int) -> str:
    result = ""
    units_used = 0
    for char in value:
        units = 2 if ord(char) > 127 else 1
        if units_used + units > max_units:
            break
        result += char
        units_used += units
    return result


def node_line(task: dict[str, Any]) -> str:
    kind = KIND_LABELS.get(task.get("kind"), task.get("kind"))
    label = "\\n".join(
        [
            str(task.get("title", "")),
            f"{task.get('id')} · {kind} · {short_due(task.get('due_at'))}",
        ]
    )
    return f'{safe_node(task["id"])}["{escape(label)}"]'


def short_due(value: str | None) -> str:
    if not value:
        return "截止 -"
    try:
        due = date.fromisoformat(str(value))
    except ValueError:
        return f"截止 {value}"
    if due.year == date.today().year:
        return f"截止 {due.month:02d}-{due.day:02d}"
    return f"截止 {value}"


def safe_node(task_id: str) -> str:
    return str(task_id).replace("-", "_")


def escape(value: str) -> str:
    return value.replace('"', '\\"')


def escape_dot(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def svg_escape(value: str) -> str:
    return html.escape(str(value), quote=True)
