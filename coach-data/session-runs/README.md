# AIPM Coach Session Runs

本目录保存经过校验的真实完整教练会话，每次完整 workflow 对应一个 JSON：

```text
coach-data/session-runs/<run_id>.json
```

必填字段：

```text
run_id, timestamp, user_input, router_result, called_modules, module_outputs,
knowledge_note_path, reflection_questions, user_reflection_answer,
learning_evaluation, gap_evaluation, radar_scores, radar_artifacts, eval_case_id
```

建议同时保存 `full_raw_answer`，用于生成严格评测读取的真实回答样本。`sample_output` 只能用于 `--allow-fixtures` 冒烟测试，不能作为真实 session。
