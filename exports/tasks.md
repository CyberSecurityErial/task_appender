# 任务列表

## 成长计分板

- 等级：{== VI ==} Lv.6 长期工程师
- 段位铭文：锻造长期工程核心
- 已获得经验：1914 XP
- 下一级进度：514/520 XP，还差 6 XP
- 任务完成：11/50（22.0%）
- 任务池待领取：6281 XP
- 产出：工具/版本发布 x5（+450 XP）；博客/文章 x3（+210 XP）；源码地图 x1（+60 XP）；复盘/总结 x1（+45 XP）

## 技能树

```text
星核主干 [解锁] 1914 XP - XP 汇流核心
├─ 星文输出 [解锁] 498 XP - 知识铸成卷轴
│  ├─ 卷轴写作 [解锁] 351 XP - 博客即法术书
│  └─ MuP 秘典 [解锁] 147 XP - 尺度法则觉醒
├─ 推理秘术 [解锁] 52 XP - 驱动 KV 星流
│  ├─ 缓存咒术 [解锁] 26 XP - 驯服 KV 星河
│  ├─ 模型星门 [解锁] 26 XP - 推理链路展开
│  └─ 传输法阵 [封印] 0 XP - RDMA 开门
├─ 工程炼成 [封印] 0 XP - 实验点火成真
│  ├─ 实验炉心 [封印] 0 XP - Demo 点燃现实
│  ├─ 训练矩阵 [封印] 0 XP - 并行阵列启动
│  └─ 通信锻炉 [封印] 0 XP - 拓扑化作武器
├─ 工具圣殿 [解锁] 1093 XP - 自动化结界
│  ├─ 任务图引擎 [解锁] 1093 XP - 本地星图自转
│  ├─ 日课仪式 [封印] 0 XP - 复盘回路充能
│  └─ 时钟塔 [封印] 0 XP - DDL 齿轮校准
└─ 游离符文 [解锁] 271 XP - 未归档能量
```

## 已完成任务收获

- **T-0051** 长期：我完成了一个长期节点，推进任务图闭环（+167 XP）
  证据：系统理解 SMD 与模型训练动力学的关系，梳理核心假设、优化视角、收敛直觉和可迁移到深度学习训练分析的结论。；产出：-；标签：`theory` `training-dynamics` `smd`
- **T-0037** LLM 推理系统：我推进了对 LLM 推理、KVCache、通信和调度链路的理解（+78 XP）
  证据：理解 PagedAttention 的 block/page 抽象、物理块分配、逻辑到物理映射、连续/非连续 KVCache 管理和对吞吐/显存碎片的影响。；产出：-；标签：`kvcache` `pagedattention` `attention`
- **T-0044** LLM 推理系统：我推进了对 LLM 推理、KVCache、通信和调度链路的理解（+78 XP）
  证据：为 Pico-vLLM 增加 CPU 推理支持，明确 CPU backend、算子路径、调度兼容和基础正确性验证。；产出：-；标签：`pico-vllm` `cpu` `inference`
- **T-0034** 源码阅读 / 个人工具演进：我形成了从入口到关键模块的数据路径和源码地图；我把个人任务管理流程固化到本地优先的工具能力里（+344 XP）
  证据：技能树、段位字符标志、等级谱注脚、导出和测试验证通过后打 v0.1.0rc1 标签并推送主线。；产出：源码地图，工具/版本发布；标签：`task-appender` `release`
- **T-0033** 个人工具演进：我把个人任务管理流程固化到本地优先的工具能力里（+155 XP）
  证据：成长计分板技能树改为单根树状结构，技能描述更简洁并带科技/魔幻风格，等级增加字符段位标志和等级谱注脚。；产出：工具/版本发布；标签：`task-appender` `feature` `scoreboard` `release`
- **T-0032** 个人工具演进：我把个人任务管理流程固化到本地优先的工具能力里（+292 XP）
  证据：收获提取、成长计分板、HTML 导出和默认任务库写入后的自动同步全部验证通过后打 tag。；产出：工具/版本发布；标签：`task-appender` `release`
- **T-0031** 个人工具演进：我把个人任务管理流程固化到本地优先的工具能力里（+155 XP）
  证据：把任务和产出量化为 XP、等级、任务池经验、技能标签和产出统计，并提供 exports/scoreboard.html。；产出：工具/版本发布；标签：`task-appender` `feature` `scoreboard` `release`
- **T-0030** 个人工具演进：我把个人任务管理流程固化到本地优先的工具能力里（+147 XP）
  证据：从已完成任务的标题、备注和标签中提取用户收获，并导出到 Markdown、图谱 HTML 和成长计分板 HTML。；产出：工具/版本发布；标签：`task-appender` `feature` `analytics` `release`
- **T-0024** 可复用输出 / MuP 知识体系：我把学习内容组织成可以复用和分享的输出；我沉淀 MuP 的核心直觉、机制细节和延展主题（+129 XP）
  证据：深入讨论更高阶的 MuP 机制、实践细节和常见坑点。；产出：博客/文章；标签：`blog` `mup`
- **T-0023** 可复用输出 / MuP 知识体系 / 复盘习惯：我把学习内容组织成可以复用和分享的输出；我沉淀 MuP 的核心直觉、机制细节和延展主题；我加强了持续记录、每日回顾和知识沉淀的节奏（+166 XP）
  证据：整理 MuP 的核心问题、直觉、基本概念和入门示例。；产出：博客/文章，复盘/总结；标签：`blog` `mup`
- **T-0021** 可复用输出：我把学习内容组织成可以复用和分享的输出（+203 XP）
  证据：搭建个人博客；产出：博客/文章；标签：`blog`

## 任务明细

- **T-0001** [进行中/长期] 学习 KVCache 分布式推理调度
  截止：2026-05-19；完成：-；优先级：1；标签：`kvcache` `inference` `scheduling`
  子任务：T-0002, T-0003
- **T-0018** [进行中/长期] 学习 KVCache 调度
  截止：-；完成：-；优先级：1；标签：`kvcache` `scheduling` `inference`
  子任务：T-0001
- **T-0020** [进行中/长期] llm推理
  截止：-；完成：-；优先级：1；标签：`llm` `inference`
  子任务：T-0018
- **T-0022** [进行中/长期] 写 MuP 博客
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  子任务：T-0023, T-0024, T-0025, T-0026, T-0027, T-0028
- **T-0003** [被阻塞/短期] 学习 UCX
  截止：2026-05-12；完成：-；优先级：2；标签：`ucx` `rdma` `transport`
- **T-0004** [待办/短期] 学习 P/D 分离的基础
  截止：2026-05-03；完成：-；优先级：1；标签：`pd-disaggregation` `inference` `foundation`
- **T-0002** [待办/短期] 学习 Mooncake
  截止：2026-05-10；完成：-；优先级：1；标签：`mooncake` `kvcache` `pd-disaggregation`
  前置依赖：T-0004
- **T-0005** [待办/长期] 学习 nccl-gin
  截止：-；完成：-；优先级：3；标签：`nccl-gin`
  子任务：T-0006, T-0007
- **T-0006** [待办/短期] 学习 nccl-gin 具体源码
  截止：-；完成：-；优先级：3；标签：`nccl-gin`
- **T-0007** [待办/短期] 学习 nccl-gin 原理
  截止：-；完成：-；优先级：3；标签：`nccl-gin`
- **T-0008** [待办/长期] 学习 Megatron 训练框架
  截止：-；完成：-；优先级：2；标签：`megatron` `distributed-training`
  子任务：T-0009, T-0010, T-0011, T-0012
- **T-0009** [待办/短期] 梳理 Megatron 训练架构与并行基础
  截止：-；完成：-；优先级：2；标签：`megatron` `distributed-training`
- **T-0010** [待办/短期] 跑通 Megatron 小规模训练样例
  截止：-；完成：-；优先级：2；标签：`megatron` `experiment`
  前置依赖：T-0009
- **T-0011** [待办/短期] 阅读 Megatron 模型、并行与优化器源码主线
  截止：-；完成：-；优先级：2；标签：`megatron` `source-reading`
  前置依赖：T-0010
- **T-0012** [待办/里程碑] 完成一次 Megatron 训练调优复盘
  截止：-；完成：-；优先级：2；标签：`megatron` `performance`
  前置依赖：T-0011
- **T-0013** [待办/长期] 维护 task_appender 功能 TODO List
  截止：-；完成：-；优先级：1；标签：`task-appender` `feature`
  子任务：T-0014, T-0015, T-0016, T-0017, T-0030, T-0031, T-0032, T-0033, T-0034
- **T-0014** [待办/短期] 实现每日任务创建与展示
  截止：-；完成：-；优先级：1；标签：`task-appender` `daily` `feature`
- **T-0015** [待办/短期] 支持每日任务分时提醒
  截止：-；完成：-；优先级：1；标签：`task-appender` `daily` `reminder`
  前置依赖：T-0014
- **T-0016** [待办/短期] 支持 DDL 日期手动修改
  截止：-；完成：-；优先级：1；标签：`task-appender` `ddl` `feature`
- **T-0017** [待办/短期] 支持 DDL 日期自动修改策略
  截止：-；完成：-；优先级：1；标签：`task-appender` `ddl` `automation`
  前置依赖：T-0016
- **T-0025** [待办/短期] MuP 之上 1
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  前置依赖：T-0024
- **T-0026** [待办/短期] MuP 之上 2
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  前置依赖：T-0025
- **T-0027** [待办/短期] MuP 之上 3
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  前置依赖：T-0026
- **T-0028** [待办/短期] MuP 之上 4
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  前置依赖：T-0027
- **T-0029** [待办/短期] 编写 UCX 源码解读博客
  截止：-；完成：-；优先级：2；标签：`blog` `ucx` `source-reading`
  前置依赖：T-0003
- **T-0035** [待办/短期] 支持个人博客中英文双语
  截止：-；完成：-；优先级：2；标签：`blog` `i18n` `bilingual`
- **T-0036** [待办/长期] 学习推理框架里面 KVCache 的寻址
  截止：-；完成：-；优先级：1；标签：`kvcache` `inference` `attention` `serving`
  子任务：T-0037, T-0038, T-0039, T-0040, T-0041, T-0042
- **T-0038** [待办/短期] 学习 RadixAttention
  截止：-；完成：-；优先级：1；标签：`kvcache` `radixattention` `attention`
- **T-0039** [待办/短期] 学习 pico-vLLM 的 PA+RA
  截止：-；完成：-；优先级：1；标签：`kvcache` `pico-vllm` `pagedattention` `radixattention`
  前置依赖：T-0037, T-0038
- **T-0040** [待办/短期] 学习正统 vLLM 的 PagedAttention
  截止：-；完成：-；优先级：1；标签：`kvcache` `vllm` `pagedattention`
  前置依赖：T-0037
- **T-0041** [待办/短期] 学习正统 SGLang 的 RadixAttention
  截止：-；完成：-；优先级：1；标签：`kvcache` `sglang` `radixattention`
  前置依赖：T-0038
- **T-0042** [待办/短期] 学习其他不成熟但开放的 KVCache 管理方案
  截止：-；完成：-；优先级：2；标签：`kvcache` `serving` `research` `open-source`
  前置依赖：T-0039, T-0040, T-0041
- **T-0043** [待办/长期] Pico-vLLM开发
  截止：-；完成：-；优先级：1；标签：`pico-vllm` `inference` `development`
  子任务：T-0044, T-0045, T-0046
- **T-0045** [待办/短期] Pico-vLLM profiling 和 memtrack 插件支持
  截止：-；完成：-；优先级：1；标签：`pico-vllm` `profiling` `memtrack` `plugin`
- **T-0046** [待办/短期] Pico-vLLM blockManager 重构
  截止：-；完成：-；优先级：1；标签：`pico-vllm` `block-manager` `storage` `mla` `attention`
- **T-0047** [待办/长期] 强化学习框架攻关
  截止：-；完成：-；优先级：1；标签：`reinforcement-learning` `rl-framework` `post-training`
  子任务：T-0048, T-0049, T-0050
- **T-0048** [待办/短期] 学习 LLM 后训练强化学习流程
  截止：-；完成：-；优先级：1；标签：`reinforcement-learning` `llm` `post-training`
- **T-0049** [待办/短期] 学习 verl 框架大致骨架
  截止：-；完成：-；优先级：1；标签：`reinforcement-learning` `verl` `framework`
  前置依赖：T-0048
- **T-0050** [待办/短期] 实现自研 RL 框架原型
  截止：-；完成：-；优先级：1；标签：`reinforcement-learning` `femotron` `pico-vllm` `training` `inference`
  前置依赖：T-0049
- **T-0030** [已完成/短期] 实现 v0.1 已完成任务收获提取
  截止：2026-05-05；完成：2026-05-05；优先级：3；标签：`task-appender` `feature` `analytics` `release`
- **T-0031** [已完成/短期] 实现 v0.1 成长计分板和经验等级导出
  截止：2026-05-05；完成：2026-05-05；优先级：3；标签：`task-appender` `feature` `scoreboard` `release`
  前置依赖：T-0030
- **T-0032** [已完成/里程碑] 发布 task_appender v0.1
  截止：2026-05-05；完成：2026-05-05；优先级：3；标签：`task-appender` `release`
  前置依赖：T-0030, T-0031
- **T-0033** [已完成/短期] 实现 v0.1.0rc1 技能树和段位标志补丁
  截止：2026-05-05；完成：2026-05-05；优先级：3；标签：`task-appender` `feature` `scoreboard` `release`
  前置依赖：T-0032
- **T-0034** [已完成/里程碑] 发布 task_appender v0.1.0rc1
  截止：2026-05-05；完成：2026-05-05；优先级：3；标签：`task-appender` `release`
  前置依赖：T-0033
- **T-0021** [已完成/长期] 搭建个人博客
  截止：-；完成：-；优先级：3；标签：`blog`
- **T-0023** [已完成/短期] 初探 MuP
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
- **T-0024** [已完成/短期] 高阶 MuP
  截止：-；完成：-；优先级：3；标签：`blog` `mup`
  前置依赖：T-0023
- **T-0037** [已完成/短期] 学习 PagedAttention
  截止：-；完成：2026-05-14；优先级：1；标签：`kvcache` `pagedattention` `attention`
- **T-0044** [已完成/短期] Pico-vLLM CPU 推理支持
  截止：-；完成：2026-05-13；优先级：1；标签：`pico-vllm` `cpu` `inference`
- **T-0051** [已完成/长期] 学习模型训练动力学-SMD
  截止：-；完成：2026-05-17；优先级：2；标签：`theory` `training-dynamics` `smd`

## 等级谱注脚

- < I > Lv.1 任务新手：点亮第一枚任务符文；0 XP 起
- < II > Lv.2 稳定推进者：启动恒定推进炉；120 XP 起
- [ III ] Lv.3 系统学习者：展开系统星图；320 XP 起
- [ IV ] Lv.4 输出型学习者：把知识铸成光刃；600 XP 起
- {== V ==} Lv.5 任务图构建者：编织任务因果网；960 XP 起
- {== VI ==} Lv.6 长期工程师：锻造长期工程核心；1400 XP 起
- << VII >> Lv.7 复盘架构师：重构经验回路；1920 XP 起
- << VIII >> Lv.8 高阶自驱者：进入自驱星域；2520 XP 起
