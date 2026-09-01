# MPI T1-Codex 1.2.0 candidate.1 安装提示词

将下面整段交给另一台机器上的 Codex。当前固定候选尚未通过三文体发布
验证，因此必须保留 `release_ready=false`，不得冒充正式发布版。

```text
请安装并完整验证 MPI T1-Codex 1.2.0 候选 Skill。

公开仓库：zhi12458/mpi-strategy-c-codex
T1-Codex Skill 路径：skills/mpi-strategy-t1-codex
完整仓库：https://github.com/zhi12458/mpi-strategy-c-codex.git
固定候选标签：t1-codex-v1.2.0-candidate.1
基础运行时 Skill 路径：skills/mpi-strategy-t1
基础运行时固定标签：t1-v1.0.1-installer-1.0.0

要求：

1. 完整读取 Codex 内置 skill-installer。检查现有安装的版本、MANIFEST、READY
   和差异；如为 candidate.2 或只有静态 PASS，先做可恢复备份，不沿用旧结论。
2. 从基础固定标签安装 skills/mpi-strategy-t1，从候选固定标签安装
   skills/mpi-strategy-t1-codex；不得从移动的 main 安装。完整读取候选 Skill 的
   SKILL.md、dependency-lock.json、installation.md 和 readiness.md。
3. 按 installation.md 检查 Git、Python 3.11+、Pandoc、LibreOffice、keyring 和
   OMP。OMP 必须恰好为 17.3.4；缺失时先征得我的确认，再安装固定版本。
4. 进入 T1-Codex Skill 目录，在交互终端运行唯一的运行时安装入口：
   python scripts/install_runtime.py
   不得拆开或跳过。它会引导 OMP 登录；Personal 输入 PERSONAL，Business 输入
   BUSINESS，旧称 TEAM 也接受。若 DeepSeek Key 缺失，必须让我在隐藏输入框
   亲自输入；公开 smoke 只有我在本地输入
   RUN PUBLIC SMOKE 后才能运行。不得要求我在聊天中发送密码、验证码、Key 或 token。
5. 向导未返回 PASS 时只报告 BLOCKED。不得改成全部使用 Codex，也不得跳过
   OMP/DeepSeek 后仍称为 T1-Codex。随后运行 python scripts/validate_package.py；
   它只验证文件和角色策略，不能替代运行时就绪。
6. 核对当前任务为 GPT-5.6-Sol/high。正确角色是：Codex 在英文起草前生成完整、
   源文绑定的中文语意划分，并负责英文起草与编辑；新增“我们”只能在原文已经
   包含讲者与听众时使用，其他情况必须待确认。OMP + DeepSeek Pro/max 须独立
   审查所有改动过的语意划分记录。其余角色是：
   OMP + DeepSeek Flash/high 负责原文分析和高风险语义桥；OMP + DeepSeek Pro/max
   负责独立挑战、两轮双语审校和精简后语义回归。精简后还必须运行普通英文
   非虚构编辑与英文佛教/Dharma 编辑两道互相隔离的 English-only reader gate；
   修改后完整重跑中文复核、双向语义回归及两位英文读者终检。最终交付除英文稿
   和双语稿外，还应包括可供委托人分析的中文语意划分报告。
7. 只有同时看到 omp_version: 17.3.4、deepseek_credential_present: true、
   base_ready: true、public_smoke_status: PASS，才能报告“本机运行时已就绪”。输出
   脱敏报告和 blockers，不得输出任何凭据或完整账号标识。
8. 候选仍须保留 release_ready=false；安装就绪不等于文稿人工批准或正式发布。

推荐调用：请使用 T1-Codex 翻译这份中文佛教文档。
```
