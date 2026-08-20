# MPI M 策略安装提示

请实际安装并验证 MPI M 策略，不要只给安装说明。

1. 从维护者提供的 `mpi-strategy-m-codex` 固定版本安装
   `skills/mpi-strategy-m` 到 Codex 技能目录。
2. 完整读取 `$mpi-strategy-m`、安装规范和依赖锁；不得跟随任何 `main`
   或自行替换相近提交。
3. 将运行时安装到独立 `MPI-Strategy-M` 根目录，不得复用或覆盖旧 C
   运行目录。
4. 验证两个兼容 fork 的 origin、精确 SHA、真实 Git 子模块、clean
   worktree、医生报告和关键文件哈希。
5. 验证锁定 Whisper 模型，完成故障注入和公开非隐私 Flash/Pro 冒烟；
   其中必须证明“独善其身”被 Flash 列入 `cultural_allusions`，缺少
   `external-lookup-receipts.jsonl` 或 `allusion-decisions.json` 时 Sol
   被阻止，补齐权威网页证据后才允许继续。
6. 只有所有门禁通过，才能原子写入含 `strategy_id: M`、
   `workflow_version: 1.0.12`、模型职责和术语政策版本的 `READY.json`，并
   将 `ready` 设为 `true`。
7. M 安装验证成功后才停用旧 `$mpi-strategy-c` 自动入口；旧源码、
   运行目录和基准资料保持可恢复。

任何一步失败都必须停止，不得静默降级或产生翻译交付。
