# 给客户的一次性安装提示词

把下面整段复制给客户电脑上的 Codex。客户只需执行这一次；安装完成后使用普通中文提出翻译请求即可。

```text
请实际安装并验证 MPI 方案 C，不要只给我安装说明。请在同一个任务中完成以下工作；只有所有强制门禁通过后才宣布安装完成。

1. 从公开仓库 https://github.com/zhi12458/mpi-strategy-c-codex 获取最新版发布内容，将其中的 mpi-strategy-c 技能安装到本机 Codex 能自动发现的技能目录，然后完整读取该技能的 SKILL.md 和安装规范并照做。

2. 使用该发布自带的 dependency-lock.json，通过 HTTPS 安装并锁定以下两个“经验证的兼容 fork”：
   - MPI：https://github.com/zhi12458/mpi-translations.git
   - translation-toolkit：https://github.com/zhi12458/translation-toolkit.git
   这两个仓库不是官方上游发布。不得跟随任何仓库会移动的 main，也不得自行换成相近版本；必须使用锁文件中的精确 SHA。READY.json 还必须记录各 fork 的绝对路径、origin、精确 SHA，以及官方 SourceHut/Codeberg 上游 origin 和基线 SHA。toolkit 必须是 MPI 仓库里真实初始化、精确固定的 Git 子模块。

3. 自动检查并安装当前 Apple 芯片 Mac 或 Windows 11 所需的 Git、Python 3.11+、Pandoc、FFmpeg、CMake、whisper.cpp 和 Python keyring。需要管理员确认时使用操作系统自己的确认界面，不要让我在聊天里发送系统密码。

4. 需要 DeepSeek API Key 时，必须调用技能提供的 credential_store.py 打开系统隐藏输入窗口，并保存到 macOS 钥匙串或 Windows 凭据管理器；不要让我把密钥粘贴到聊天、命令行参数、普通文本文件或日志中。

5. 需要语音模型时，必须调用技能提供的 select_whisper_model.py 打开系统文件选择窗口。我只使用 whisper-medium-2512-ft-best-ggml.bin；文件名和 SHA-256 都必须与锁文件一致，不得下载或改用其他 Whisper 模型。

6. 运行正式安装器，并实际完成：两个仓库的 origin/SHA/干净工作树/关键文件哈希验证、MPI doctor、toolkit doctor、可丢弃副本上的依赖破坏与恢复测试，以及不含私人内容的 Flash 与 Pro 端到端冒烟测试。故障测试必须证明删除或修改任一 AGENTS.md、子模块、关键脚本、术语库、SHA、origin、doctor 或旧 QA 产物都会阻止翻译，恢复精确锁定依赖后才允许继续。

7. 只有上述项目全部通过，才原子写入 READY.json 的 ready: true。请向我报告 READY.json 的绝对路径、两个 fork 的精确 SHA、官方上游基线 SHA、doctor 结果、故障注入结果和冒烟测试结果。任何一步失败时，先按技能规定进行精确版本的原子修复；仍失败就明确停止，不能静默降级，也不能产生翻译模型费用。

8. 验证 Codex 已能自动识别以下自然语言请求：“请翻译这个文件”“请翻译这个音频”“请整理并翻译这个视频，生成双语字幕”“继续刚才的翻译”。以后每个翻译项目都必须重新预检并实际读取 MPI 与 toolkit 规范，通过审计执行器真实调用锁定 toolkit 做源稿提取、MPI 术语检索、term-map、source/target/bilingual 管理、机械检查、DOCX 生成与质量检查，以及适用时的字幕生成与检查；不得用技能内置替代逻辑绕过。

方案 C 的模型职责固定为：DeepSeek V4 Flash high 只做 toolkit 冻结中文的源义分析；当前 Codex 的 GPT-5.6-Sol medium 独立完成英文；DeepSeek V4 Pro max 在看不到 Flash 分析的条件下做两轮双语审核。仅当第二轮仍有标题或 critical/major 问题时，才允许 GPT-5.6-Sol high 做定向裁决；仍未解决则停下请人工判断。疑难术语先查 MPI 术语库，只在缺项、冲突、语境歧义或高风险时查权威在线来源，并写入 term-decisions.json。所有交付标记为 AI draft，并附 instruction-receipt.json、tool-execution-receipts.jsonl 和 MANIFEST.json；只有收据与哈希链齐全时 pipeline_complete 才能为 true。
```

安装器锁定的是发布 SHA，而不是“永远使用 fork main”。维护者以后如发布新锁，客户应通过技能的升级流程重新验证，不能手动 `git pull` 后继续使用旧 READY。
