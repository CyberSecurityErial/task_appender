# 任务列表

- **T-0001** [进行中/长期] 学习 KVCache 分布式推理调度  
  截止：2026-05-19；优先级：1；标签：`kvcache` `inference` `scheduling`
  子任务：T-0002, T-0003
- **T-0004** [待办/短期] 学习 P/D 分离的基础  
  截止：2026-05-03；优先级：1；标签：`pd-disaggregation` `inference` `foundation`
- **T-0002** [待办/短期] 学习 Mooncake  
  截止：2026-05-10；优先级：1；标签：`mooncake` `kvcache` `pd-disaggregation`
  前置依赖：T-0004
- **T-0003** [待办/短期] 学习 UCX  
  截止：2026-05-12；优先级：2；标签：`ucx` `rdma` `transport`
- **T-0005** [待办/长期] 学习 nccl-gin  
  截止：-；优先级：3；标签：`nccl-gin`
  子任务：T-0006, T-0007
- **T-0006** [待办/短期] 学习 nccl-gin 具体源码  
  截止：-；优先级：3；标签：`nccl-gin`
- **T-0007** [待办/短期] 学习 nccl-gin 原理  
  截止：-；优先级：3；标签：`nccl-gin`
- **T-0008** [待办/长期] 学习 Megatron 训练框架  
  截止：-；优先级：2；标签：`megatron` `distributed-training`
  子任务：T-0009, T-0010, T-0011, T-0012
- **T-0009** [待办/短期] 梳理 Megatron 训练架构与并行基础  
  截止：-；优先级：2；标签：`megatron` `distributed-training`
- **T-0010** [待办/短期] 跑通 Megatron 小规模训练样例  
  截止：-；优先级：2；标签：`megatron` `experiment`
  前置依赖：T-0009
- **T-0011** [待办/短期] 阅读 Megatron 模型、并行与优化器源码主线  
  截止：-；优先级：2；标签：`megatron` `source-reading`
  前置依赖：T-0010
- **T-0012** [待办/里程碑] 完成一次 Megatron 训练调优复盘  
  截止：-；优先级：2；标签：`megatron` `performance`
  前置依赖：T-0011
- **T-0013** [待办/长期] 维护 task_appender 功能 TODO List  
  截止：-；优先级：1；标签：`task-appender` `feature`
  子任务：T-0014, T-0015, T-0016, T-0017
- **T-0014** [待办/短期] 实现每日任务创建与展示  
  截止：-；优先级：1；标签：`task-appender` `daily` `feature`
- **T-0015** [待办/短期] 支持每日任务分时提醒  
  截止：-；优先级：1；标签：`task-appender` `daily` `reminder`
  前置依赖：T-0014
- **T-0016** [待办/短期] 支持 DDL 日期手动修改  
  截止：-；优先级：1；标签：`task-appender` `ddl` `feature`
- **T-0017** [待办/短期] 支持 DDL 日期自动修改策略  
  截止：-；优先级：1；标签：`task-appender` `ddl` `automation`
  前置依赖：T-0016
