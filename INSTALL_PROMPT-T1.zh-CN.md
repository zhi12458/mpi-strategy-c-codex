# MPI T1.0.1 Codex 安装提示词

将下面整段交给 Codex。用户必须亲自完成系统管理员确认、OpenAI 浏览器登录、
Personal 工作区选择和 DeepSeek Key 的本地隐藏输入。

```text
请安装并验证 MPI T1.0.1 生产翻译环境。

公开仓库：zhi12458/mpi-strategy-c-codex
技能路径：skills/mpi-strategy-t1
固定版本标签：t1-v1.0.1-installer-1.0.0
技能名称：mpi-strategy-t1

要求：

1. 使用 Codex 内置 skill-installer 安装上述固定标签中的技能；只安装
   skills/mpi-strategy-t1，不安装或启用 C、M、M2。传给安装器的参数必须等价于：
   --repo zhi12458/mpi-strategy-c-codex --path skills/mpi-strategy-t1
   --ref t1-v1.0.1-installer-1.0.0。不得从移动的 main 安装。
2. 如果目标目录已经存在，不要覆盖。先报告现有版本、MANIFEST 和差异，等待我确认。
3. 安装后读取 SKILL.md、references/installation.md、dependency-lock.json；不要把
   “技能文件安装成功”当成“生产环境可用”。
4. 检查操作系统和现有依赖。T1 要求 Git、Python 3.11+、Pandoc、LibreOffice、
   Python keyring，以及锁定的 OMP 17.3.4。需要安装系统软件或管理员权限时，先说明
   将执行的命令并等待我确认；不要在聊天中询问管理员密码。
5. OMP 必须来自官方 can1357/oh-my-pi。可复现安装优先使用：
   bun install -g @oh-my-pi/pi-coding-agent@17.3.4
   如果没有 Bun，只能在向我说明来源和命令、取得本机安装确认后，从 Bun 官方发行渠道
   安装；不要使用来路不明的脚本。随后再执行上述固定版本命令。安装后核对
   omp --version。不同版本不能宣称已经通过 T1 验证。
6. 运行 python scripts/strategy_t1.py login-openai。让我亲自在浏览器完成登录，明确
   选择 Personal account，不选择任何组织或团队工作区。不要替我输入密码、验证码。
7. 登录完成后运行 python scripts/strategy_t1.py confirm-personal-workspace，显示非秘密的
   plan/workspace 摘要，让我核对后亲自在本地终端输入 PERSONAL。不要把 OAuth token、
   account ID 或完整凭据写入报告。
8. 运行 python scripts/credential_store.py。暂停并让我亲自在本机隐藏输入框/终端中输入
   DeepSeek API Key。绝不能让我把 Key 发到 Codex 对话，也不能把 Key 放进命令参数、
   shell 历史、仓库、配置明文或日志。只允许存入 T1 专属系统凭据库
   mpi-strategy-t1-deepseek。
9. 在我确认允许消耗少量模型额度后，运行：
   python scripts/strategy_t1.py install --confirm-public-smoke
   live smoke 只能发送安装包内固定的公开测试句，禁止发送我的文稿或任何私密内容。
10. 安装器必须验证 MANIFEST、固定依赖提交、两个 repository doctor、故障注入、OMP
    版本、Personal 确认、DeepSeek 凭据存在性和以下模型/推理档位：
    - deepseek/deepseek-v4-flash：high
    - openai-codex/gpt-5.6-sol：high
    - deepseek/deepseek-v4-pro：max
11. 最后运行 python scripts/strategy_t1.py doctor。只有 READY.json 显示 strategy_id=T1、
    workflow_version=1.0.1、installer_version=1.0.0、ready=true，才能报告安装完成。
12. 输出脱敏安装报告：实际路径、版本、依赖状态、模型状态、smoke/fault 报告 SHA-256
    和最终 ready 状态。不得输出任何 API Key、OAuth token 或完整账号标识。
13. 告诉我该技能将在下一轮 Codex 对话可用。推荐调用：用 T1 翻译 XX。
```

该标签只可在完整测试通过后创建，并应固定指向 T1.0.1 工作流与安装器 1.0.0 的
发布提交；不得移动或复用该标签。
