# 客户日常使用提示词

完成一次性安装且 `READY.json` 为 `ready: true` 后，客户不需要了解命令行。把文件附到 Codex，使用下面任一句即可。

## 翻译文档

```text
请用 MPI 方案 C 翻译这个文件。按出版书稿处理，完成英文稿和中英双语稿，并把 QA、审核意见和 MANIFEST 一并交付。
```

## 翻译音频

```text
请用 MPI 方案 C 整理并翻译这个音频。只用已锁定的 whisper-medium-2512-ft-best 模型转写；遇到会影响意思的听不清之处再问我。请交付整理后的中文、英文、双语稿和字幕。
```

## 翻译视频并生成字幕

```text
请用 MPI 方案 C 整理并翻译这个视频，生成中文、英文和中英双语 SRT/VTT 字幕，同时交付英文 DOCX、双语 DOCX、QA 和完整审计记录。
```

## 继续中断的任务

```text
请继续刚才的 MPI 方案 C 翻译。先重新验证 READY、两个锁定仓库和已有收据，只从哈希有效的检查点继续。
```

## 只核验是否真实使用了 MPI 与 toolkit

```text
请审计这个翻译项目是否真正调用了锁定的 mpi-translations 和 translation-toolkit。核对 origin、SHA、规范读取收据、每个强制脚本收据和最终哈希链；不要重新翻译。请列出缺失或失效的证据，并说明 pipeline_complete 是否可信。
```

客户无需在日常提示中重复模型名称。技能会固定执行 Flash high → GPT-5.6-Sol medium → Pro max；如果当前 Codex 不是 GPT-5.6-Sol medium，流程会在产生译稿前停止并提示切换。Sol high 只用于第二轮后仍未解决的标题或 critical/major 定向裁决。
