# AIPM Coach Evaluation Upgrade Template

这份文档记录自动评测机制的可信度升级要求，避免再次把内置样例误当成真实 AI 教练表现。

## 核心问题

旧版 `run_eval.py` 的逻辑是：

1. 查找 `tests/aipm-coach-eval/samples/<case_id>.txt`。
2. 如果真实回答文件不存在，就使用 case JSON 里的 `sample_output`。
3. 再根据关键词和结构规则打分。

这样得到的 100 分只说明“内置样例符合规则”，不能说明“AI 教练真实回答符合规则”。

## 新版目标

每个 case 必须标记样本来源：

- `real_sample`：来自 `samples/<case_id>.txt` 的真实 AI 教练回答。
- `embedded_sample`：来自 case JSON 的内置样例，只能用于冒烟测试。
- `missing_sample`：没有真实回答，也没有启用内置样例。
- `system_check`：环境、脚本、雷达图这类非 AI 回答检查。

默认模式必须是严格真实评测：

```powershell
python tests\aipm-coach-eval\run_eval.py
```

默认模式没有真实回答时，必须明确报告：

```text
这不是一次真实评测，因为缺少真实 AI 教练回答。
```

样例冒烟测试必须显式开启：

```powershell
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```

样例模式报告必须明确说明：

```text
这是样例冒烟测试，只能说明评测脚本能跑通，不能说明 AI 教练真实表现 100 分。
```

## 报告必须包含

- 本次评测模式
- 可信等级
- 总分
- 真实样本分数
- 测试用例总数
- 真实回答数量
- 内置样例数量
- 缺少样本数量
- 系统检查数量
- 每个 case 的来源、结果、失败原因、命中证据
- 雷达图报告地址

## Case 设计建议

每个 case 应描述真实用户输入、期望节点、禁止节点和结构要求。

```json
{
  "case_id": "workflow_eval_observability_001",
  "stage": "01-router",
  "user_input": "我想知道自动评测是否可信",
  "expected_modules": ["aipm-guide", "aipm-explainer", "aipm-recorder"],
  "forbidden_modules": ["aipm-learning-evaluator", "aipm-gap-evaluator"],
  "must_include": ["真实回答", "节点 trace", "等待用户确认"],
  "sample_output": "只用于 --allow-fixtures 的内置样例"
}
```

真实回答保存到：

```text
tests/aipm-coach-eval/samples/workflow_eval_observability_001.txt
```

## 验收标准

机制可用：

- 默认严格模式不会使用内置样例。
- `--allow-fixtures` 才允许使用 `sample_output`。
- 报告能展示每个 case 的来源和证据。
- 没有真实回答时不能宣称“可进入真实用户试运行”。

真实评测可用：

- 所有 AI 回答类 case 都有 `real_sample`。
- 没有 `embedded_sample` 和 `missing_sample`。
- 路由、流程门禁、结构、E2E、雷达图全部通过。
- 报告可信等级达到 `REAL_EVAL_HIGH_CONFIDENCE` 或 `REAL_EVAL_TRIAL_READY`。
