# AIPM Coach Session Drafts

完整 workflow 到达第 11 步后，助手先把本轮结构化内容保存为：

```text
coach-data/session-drafts/<run_id>.json
```

随后执行：

```powershell
python plugins\aipm-coach\scripts\record_session_run.py --latest-draft --run-eval
```

草稿必须包含 `coach-data/session-runs/README.md` 中列出的字段，且不能复制评测 case 的 `sample_output` 冒充真实回答。
