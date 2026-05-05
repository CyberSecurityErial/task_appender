from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date
from typing import Any


COMPLETED_STATUSES = {"done", "archived"}

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

KIND_XP = {
    "short": 45,
    "long": 130,
    "daily": 12,
    "milestone": 180,
}

PRIORITY_MULTIPLIERS = {
    1: 1.45,
    2: 1.2,
    3: 1.0,
    4: 0.85,
    5: 0.7,
}

LEVEL_RANKS = [
    {"title": "任务新手", "badge": "< I >", "motto": "点亮第一枚任务符文"},
    {"title": "稳定推进者", "badge": "< II >", "motto": "启动恒定推进炉"},
    {"title": "系统学习者", "badge": "[ III ]", "motto": "展开系统星图"},
    {"title": "输出型学习者", "badge": "[ IV ]", "motto": "把知识铸成光刃"},
    {"title": "任务图构建者", "badge": "{== V ==}", "motto": "编织任务因果网"},
    {"title": "长期工程师", "badge": "{== VI ==}", "motto": "锻造长期工程核心"},
    {"title": "复盘架构师", "badge": "<< VII >>", "motto": "重构经验回路"},
    {"title": "高阶自驱者", "badge": "<< VIII >>", "motto": "进入自驱星域"},
]

SKILL_TREE_SPEC = {
    "id": "core",
    "label": "星核主干",
    "description": "XP 汇流核心",
    "tags": [],
    "children": [
        {
            "id": "output",
            "label": "星文输出",
            "description": "知识铸成卷轴",
            "tags": [],
            "children": [
                {"id": "blog", "label": "卷轴写作", "description": "博客即法术书", "tags": ["blog", "writing"]},
                {"id": "mup", "label": "MuP 秘典", "description": "尺度法则觉醒", "tags": ["mup"]},
            ],
        },
        {
            "id": "systems",
            "label": "推理秘术",
            "description": "驱动 KV 星流",
            "tags": [],
            "children": [
                {
                    "id": "kvcache",
                    "label": "缓存咒术",
                    "description": "驯服 KV 星河",
                    "tags": ["kvcache", "vllm", "sglang", "paged-attention"],
                },
                {
                    "id": "inference",
                    "label": "模型星门",
                    "description": "推理链路展开",
                    "tags": ["llm", "inference", "mooncake", "pd-disaggregation", "foundation"],
                },
                {
                    "id": "transport",
                    "label": "传输法阵",
                    "description": "RDMA 开门",
                    "tags": ["ucx", "rdma", "transport"],
                },
            ],
        },
        {
            "id": "forge",
            "label": "工程炼成",
            "description": "实验点火成真",
            "tags": [],
            "children": [
                {"id": "experiment", "label": "实验炉心", "description": "Demo 点燃现实", "tags": ["experiment", "demo"]},
                {"id": "training", "label": "训练矩阵", "description": "并行阵列启动", "tags": ["megatron", "distributed-training", "performance"]},
                {"id": "comm_lib", "label": "通信锻炉", "description": "拓扑化作武器", "tags": ["nccl-gin"]},
            ],
        },
        {
            "id": "tooling",
            "label": "工具圣殿",
            "description": "自动化结界",
            "tags": [],
            "children": [
                {
                    "id": "task_graph",
                    "label": "任务图引擎",
                    "description": "本地星图自转",
                    "tags": ["task-appender", "feature", "scoreboard", "analytics", "release"],
                },
                {"id": "ritual", "label": "日课仪式", "description": "复盘回路充能", "tags": ["daily", "review", "reminder"]},
                {"id": "deadline", "label": "时钟塔", "description": "DDL 齿轮校准", "tags": ["ddl", "automation"]},
            ],
        },
    ],
}

ARTIFACT_RULES = [
    {
        "id": "article",
        "label": "博客/文章",
        "xp": 70,
        "tags": {"blog", "writing"},
        "keywords": ("博客", "文章", "blog", "解读"),
    },
    {
        "id": "demo",
        "label": "Demo/实验",
        "xp": 55,
        "tags": {"experiment", "demo"},
        "keywords": ("demo", "实验", "跑通", "样例"),
    },
    {
        "id": "source_map",
        "label": "源码地图",
        "xp": 60,
        "tags": {"source-reading"},
        "keywords": ("源码", "阅读", "主线", "实现细节"),
    },
    {
        "id": "review",
        "label": "复盘/总结",
        "xp": 45,
        "tags": {"daily", "review", "performance"},
        "keywords": ("复盘", "总结", "沉淀", "整理"),
    },
    {
        "id": "release",
        "label": "工具/版本发布",
        "xp": 90,
        "tags": {"task-appender", "feature", "release"},
        "keywords": ("发布", "版本", "功能", "工具", "CLI"),
    },
]

GAIN_RULES = [
    {
        "area": "可复用输出",
        "tags": {"blog", "writing"},
        "keywords": ("博客", "文章", "解读"),
        "gain": "我把学习内容组织成可以复用和分享的输出",
    },
    {
        "area": "MuP 知识体系",
        "tags": {"mup"},
        "keywords": ("MuP", "mup"),
        "gain": "我沉淀 MuP 的核心直觉、机制细节和延展主题",
    },
    {
        "area": "LLM 推理系统",
        "tags": {"kvcache", "inference", "mooncake", "pd-disaggregation", "ucx", "rdma"},
        "keywords": ("KVCache", "推理", "Mooncake", "UCX", "P/D", "RDMA"),
        "gain": "我推进了对 LLM 推理、KVCache、通信和调度链路的理解",
    },
    {
        "area": "源码阅读",
        "tags": {"source-reading"},
        "keywords": ("源码", "阅读", "主线"),
        "gain": "我形成了从入口到关键模块的数据路径和源码地图",
    },
    {
        "area": "工程实验",
        "tags": {"experiment", "demo"},
        "keywords": ("demo", "实验", "跑通", "样例"),
        "gain": "我把概念落到可运行实验，并记录配置、日志和现象",
    },
    {
        "area": "个人工具演进",
        "tags": {"task-appender", "feature", "release"},
        "keywords": ("task_appender", "任务图", "CLI", "发布", "功能"),
        "gain": "我把个人任务管理流程固化到本地优先的工具能力里",
    },
    {
        "area": "复盘习惯",
        "tags": {"daily", "review"},
        "keywords": ("每日", "每天", "复盘", "整理"),
        "gain": "我加强了持续记录、每日回顾和知识沉淀的节奏",
    },
]


def build_progress(data: dict[str, Any]) -> dict[str, Any]:
    tasks = [task for task in data.get("tasks", []) if isinstance(task, dict)]
    completed = [task for task in tasks if task.get("status") in COMPLETED_STATUSES]
    open_tasks = [task for task in tasks if task.get("status") not in COMPLETED_STATUSES]

    completed_details = [task_detail(task) for task in completed]
    open_details = [task_detail(task) for task in open_tasks]
    earned_xp = sum(detail["total_xp"] for detail in completed_details)
    available_xp = sum(detail["total_xp"] for detail in open_details)
    level = level_for_xp(earned_xp)

    status_counts = count_by(tasks, "status")
    kind_counts = count_by(tasks, "kind")
    completion_rate = round(len(completed) / len(tasks) * 100, 1) if tasks else 0.0
    artifacts = artifact_summary(completed_details)
    gains = extract_gains(completed_details)
    tag_scores = tag_scoreboard(completed_details)
    skill_tree = build_skill_tree(tag_scores)

    return {
        "generated_at": date.today().isoformat(),
        "total_tasks": len(tasks),
        "completed_tasks": len(completed),
        "open_tasks": len(open_tasks),
        "earned_xp": earned_xp,
        "available_xp": available_xp,
        "completion_rate": completion_rate,
        "level": level,
        "status_counts": status_counts,
        "kind_counts": kind_counts,
        "artifacts": artifacts,
        "gains": gains,
        "tag_scores": tag_scores,
        "skill_tree": skill_tree,
        "level_catalog": level_catalog(),
        "completed_details": sorted(
            completed_details,
            key=lambda detail: (
                str(detail["task"].get("completed_at") or detail["task"].get("created_at") or ""),
                str(detail["task"].get("id") or ""),
            ),
            reverse=True,
        ),
        "open_details": open_details,
    }


def task_detail(task: dict[str, Any]) -> dict[str, Any]:
    task_xp = score_task(task)
    artifacts = matching_artifacts(task)
    artifact_xp = sum(int(rule["xp"]) for rule in artifacts)
    return {
        "task": task,
        "task_xp": task_xp,
        "artifact_xp": artifact_xp,
        "total_xp": task_xp + artifact_xp,
        "artifacts": artifacts,
        "areas": matching_gain_rules(task),
    }


def score_task(task: dict[str, Any]) -> int:
    kind = str(task.get("kind", "short"))
    base = KIND_XP.get(kind, KIND_XP["short"])
    priority = int(task.get("priority") or 3)
    multiplier = PRIORITY_MULTIPLIERS.get(priority, 1.0)
    dependency_bonus = min(30, len(task.get("depends_on", []) or []) * 8)
    child_bonus = min(36, len(task.get("children", []) or []) * 6)
    tag_bonus = min(18, len(task.get("tags", []) or []) * 3)
    return int(round((base + dependency_bonus + child_bonus + tag_bonus) * multiplier))


def matching_artifacts(task: dict[str, Any]) -> list[dict[str, Any]]:
    tags = {str(tag).lower() for tag in task.get("tags", [])}
    text = task_text(task).lower()
    matched: list[dict[str, Any]] = []
    for rule in ARTIFACT_RULES:
        rule_tags = {str(tag).lower() for tag in rule["tags"]}
        keywords = tuple(str(keyword).lower() for keyword in rule["keywords"])
        if tags & rule_tags or any(keyword in text for keyword in keywords):
            matched.append(rule)
    return matched


def matching_gain_rules(task: dict[str, Any]) -> list[dict[str, Any]]:
    tags = {str(tag).lower() for tag in task.get("tags", [])}
    text = task_text(task).lower()
    matched: list[dict[str, Any]] = []
    for rule in GAIN_RULES:
        rule_tags = {str(tag).lower() for tag in rule["tags"]}
        keywords = tuple(str(keyword).lower() for keyword in rule["keywords"])
        if tags & rule_tags or any(keyword in text for keyword in keywords):
            matched.append(rule)
    if not matched:
        matched.append(
            {
                "area": KIND_LABELS.get(task.get("kind"), "任务推进"),
                "gain": f"我完成了一个{KIND_LABELS.get(task.get('kind'), '任务')}节点，推进任务图闭环",
            }
        )
    return matched


def artifact_summary(completed_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    xp_by_id: Counter[str] = Counter()
    labels: dict[str, str] = {}
    for detail in completed_details:
        for rule in detail["artifacts"]:
            rule_id = str(rule["id"])
            labels[rule_id] = str(rule["label"])
            counts[rule_id] += 1
            xp_by_id[rule_id] += int(rule["xp"])
    return [
        {"id": rule_id, "label": labels[rule_id], "count": counts[rule_id], "xp": xp_by_id[rule_id]}
        for rule_id in sorted(counts, key=lambda item: (-xp_by_id[item], labels[item]))
    ]


def extract_gains(completed_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gains: list[dict[str, Any]] = []
    for detail in sorted(
        completed_details,
        key=lambda item: (
            str(item["task"].get("completed_at") or item["task"].get("created_at") or ""),
            str(item["task"].get("id") or ""),
        ),
        reverse=True,
    ):
        task = detail["task"]
        rules = detail["areas"]
        areas = unique_text(str(rule["area"]) for rule in rules)
        gain_text = "；".join(unique_text(str(rule["gain"]) for rule in rules)[:3])
        tags = [str(tag) for tag in task.get("tags", [])]
        artifacts = [str(rule["label"]) for rule in detail["artifacts"]]
        gains.append(
            {
                "task_id": str(task.get("id", "")),
                "title": str(task.get("title", "")),
                "area": " / ".join(areas[:3]),
                "gain": gain_text,
                "evidence": note_digest(task),
                "tags": tags,
                "artifacts": artifacts,
                "xp": detail["total_xp"],
            }
        )
    return gains


def unique_text(values: Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def tag_scoreboard(completed_details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    xp_by_tag: defaultdict[str, int] = defaultdict(int)
    for detail in completed_details:
        tags = [str(tag) for tag in detail["task"].get("tags", []) if str(tag).strip()]
        if not tags:
            continue
        share = detail["total_xp"] // len(tags)
        remainder = detail["total_xp"] % len(tags)
        for index, tag in enumerate(tags):
            counts[tag] += 1
            xp_by_tag[tag] += share + (1 if index < remainder else 0)
    return [
        {"tag": tag, "completed": counts[tag], "xp": xp_by_tag[tag]}
        for tag in sorted(counts, key=lambda item: (-xp_by_tag[item], item))
    ]


def build_skill_tree(tag_scores: list[dict[str, Any]]) -> dict[str, Any]:
    tag_stats = {str(item["tag"]): {"completed": int(item["completed"]), "xp": int(item["xp"])} for item in tag_scores}
    assigned = collect_tree_tags(SKILL_TREE_SPEC)
    unknown_tags = sorted(tag for tag in tag_stats if tag not in assigned)
    return build_skill_node(SKILL_TREE_SPEC, tag_stats, unknown_tags)


def build_skill_node(
    spec: dict[str, Any],
    tag_stats: dict[str, dict[str, int]],
    unknown_tags: list[str],
) -> dict[str, Any]:
    child_specs = list(spec.get("children", []))
    if spec.get("id") == "core" and unknown_tags:
        child_specs.append(
            {
                "id": "wild_runes",
                "label": "游离符文",
                "description": "未归档能量",
                "tags": unknown_tags,
                "children": [],
            }
        )
    children = [build_skill_node(child, tag_stats, unknown_tags) for child in child_specs]
    direct_tags = [str(tag) for tag in spec.get("tags", [])]
    direct_xp = sum(tag_stats.get(tag, {}).get("xp", 0) for tag in direct_tags)
    direct_completed = sum(tag_stats.get(tag, {}).get("completed", 0) for tag in direct_tags)
    total_xp = direct_xp + sum(int(child["xp"]) for child in children)
    total_completed = direct_completed + sum(int(child["completed"]) for child in children)
    return {
        "id": str(spec["id"]),
        "label": str(spec["label"]),
        "description": str(spec["description"]),
        "tags": direct_tags,
        "direct_xp": direct_xp,
        "direct_completed": direct_completed,
        "xp": total_xp,
        "completed": total_completed,
        "unlocked": total_xp > 0,
        "children": children,
    }


def collect_tree_tags(spec: dict[str, Any]) -> set[str]:
    tags = {str(tag) for tag in spec.get("tags", [])}
    for child in spec.get("children", []):
        tags.update(collect_tree_tags(child))
    return tags


def format_skill_tree_cli(node: dict[str, Any]) -> list[str]:
    lines: list[str] = []

    def walk(current: dict[str, Any], prefix: str, is_last: bool, is_root: bool) -> None:
        connector = "" if is_root else ("└─ " if is_last else "├─ ")
        state = "解锁" if current["unlocked"] else "封印"
        lines.append(
            f"{prefix}{connector}{current['label']} [{state}] {current['xp']} XP - {current['description']}"
        )
        child_prefix = prefix if is_root else prefix + ("   " if is_last else "│  ")
        children = current.get("children", [])
        for index, child in enumerate(children):
            walk(child, child_prefix, index == len(children) - 1, False)

    walk(node, "", True, True)
    return lines


def level_for_xp(xp: int) -> dict[str, Any]:
    level = 1
    floor_xp = 0
    next_cost = level_cost(level)
    while xp >= floor_xp + next_cost:
        floor_xp += next_cost
        level += 1
        next_cost = level_cost(level)
    current = xp - floor_xp
    progress = round(current / next_cost * 100, 1) if next_cost else 100.0
    rank = rank_for_level(level)
    return {
        "level": level,
        "title": rank["title"],
        "badge": rank["badge"],
        "motto": rank["motto"],
        "floor_xp": floor_xp,
        "current_xp": current,
        "next_level_xp": next_cost,
        "progress_pct": progress,
        "remaining_xp": max(0, next_cost - current),
    }


def level_cost(level: int) -> int:
    return 120 + (level - 1) * 80


def rank_for_level(level: int) -> dict[str, str]:
    if level <= len(LEVEL_RANKS):
        return LEVEL_RANKS[max(level, 1) - 1]
    return {
        "title": "星界自驱者",
        "badge": f"<< {level} >>",
        "motto": "继续扩展未知星域",
    }


def level_catalog() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    floor_xp = 0
    for level, rank in enumerate(LEVEL_RANKS, start=1):
        rows.append(
            {
                "level": level,
                "title": rank["title"],
                "badge": rank["badge"],
                "motto": rank["motto"],
                "min_xp": floor_xp,
            }
        )
        floor_xp += level_cost(level)
    return rows


def format_progress_cli(progress: dict[str, Any]) -> str:
    level = progress["level"]
    lines = [
        f"{level['badge']} Lv.{level['level']} {level['title']}  XP {progress['earned_xp']} (+{progress['available_xp']} 可领取)",
        f"段位铭文：{level['motto']}",
        f"升级进度 {level['current_xp']}/{level['next_level_xp']}，还差 {level['remaining_xp']} XP",
        f"任务完成 {progress['completed_tasks']}/{progress['total_tasks']}（{progress['completion_rate']}%）",
    ]
    if progress["artifacts"]:
        artifact_text = "，".join(f"{item['label']}x{item['count']}" for item in progress["artifacts"][:5])
        lines.append(f"产出：{artifact_text}")
    if progress["gains"]:
        lines.append("最近收获：")
        for gain in progress["gains"][:5]:
            lines.append(f"- {gain['task_id']} {gain['area']}：{gain['gain']}")
    lines.append("技能树：")
    lines.extend(format_skill_tree_cli(progress["skill_tree"]))
    lines.append("等级谱：")
    for row in progress["level_catalog"]:
        lines.append(f"- {row['badge']} Lv.{row['level']} {row['title']}（{row['min_xp']} XP+）")
    return "\n".join(lines)


def count_by(tasks: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for task in tasks:
        value = str(task.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def task_text(task: dict[str, Any]) -> str:
    tags = " ".join(str(tag) for tag in task.get("tags", []))
    return f"{task.get('title', '')} {task.get('notes', '')} {tags}"


def note_digest(task: dict[str, Any], max_length: int = 92) -> str:
    raw = str(task.get("notes") or "").strip()
    if not raw:
        raw = str(task.get("title", "")).strip()
    raw = re.sub(r"\s+", " ", raw)
    if "：" in raw:
        prefix, rest = raw.split("：", 1)
        if len(prefix) <= 16 and rest.strip():
            raw = rest.strip()
    if len(raw) <= max_length:
        return raw
    return raw[: max_length - 3].rstrip() + "..."
