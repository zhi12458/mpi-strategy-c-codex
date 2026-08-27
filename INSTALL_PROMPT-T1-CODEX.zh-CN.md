# MPI T1-Codex 1.1.0 候选安装提示词

将下面整段交给另一台机器上的 Codex。当前固定候选尚未通过三文体发布
验证，因此必须保留 `release_ready=false`，不得冒充正式发布版。

```text
请安装并离线验证 MPI T1-Codex 1.1.0 候选 Skill。

公开仓库：zhi12458/mpi-strategy-c-codex
T1-Codex Skill 路径：skills/mpi-strategy-t1-codex
固定候选标签：t1-codex-v1.1.0-candidate.1
基础运行时 Skill 路径：skills/mpi-strategy-t1
基础运行时固定标签：t1-v1.0.1-installer-1.0.0

要求：

1. 先完整读取 Codex 内置 skill-installer。若目标目录已存在，先报告版本、
   MANIFEST、READY 和差异，不得直接覆盖。
2. 从固定标签 t1-v1.0.1-installer-1.0.0 安装 skills/mpi-strategy-t1；
   不得从移动的 main 安装基础运行时。
3. 按基础 Skill 的 installation/readiness 说明核验 Git、Python、Pandoc、
   LibreOffice、keyring、OMP 17.3.4、Personal workspace、DeepSeek 系统凭据库、
   repository doctors、故障注入和固定公开 smoke。
4. 需要系统安装、管理员权限、OpenAI 登录或 DeepSeek Key 时暂停，让我亲自
   确认或输入。不能让我把密码、验证码、Key 或 token 发到对话中，也不能把
   凭据放进命令参数、shell 历史、仓库或日志。
5. 从固定候选标签 t1-codex-v1.1.0-candidate.1 安装
   skills/mpi-strategy-t1-codex。
6. 完整读取新 Skill 的 SKILL.md、dependency-lock.json、MANIFEST.sha256、
   references/workflow.md、production-lock.json、installation.md 和 readiness.md。
7. 运行 python scripts/validate_package.py。必须确认 MANIFEST 全覆盖，并确认：
   - source.dj 是唯一中文语义权威；
   - 当前 Codex/GPT-5.6-Sol high 负责翻译、意见落实、标题和精简；
   - OMP 只负责 Flash/high 和新鲜 Pro/max 独立角色；
   - 语义桥只覆盖高风险段且不生成英文；
   - 两轮 Pro 双语审校与精简后 Pro 双向语义回归均保留；
   - 全文中文预写不是默认流程；
   - T1-OMP 只作为明确回滚或盲评对照，不自动拼接两稿。
8. 核对当前 Codex 任务实际设置为 GPT-5.6-Sol、high reasoning。无法验证时，
   只能报告 Skill 文件已安装，不能报告生产运行就绪。
9. 只有在我明确同意消耗少量额度后，才可运行固定公开 Flash/high 和 Pro/max
   smoke；禁止发送任何文稿或私密内容作为安装 smoke。
10. 输出脱敏报告：两个 Skill 的实际路径、标签、MANIFEST SHA-256、基础 READY、
    OMP 版本、模型 smoke、Codex 任务设置、候选发布状态和 blockers。不得输出
    凭据或完整账号标识。
11. 当前候选必须保留 release_ready=false，直到 Dharma talk、written article、
    quotation-dense Buddhist text 三类同源人工盲评全部通过。

推荐调用：请使用 T1-Codex 翻译这份中文佛教文档。
```
