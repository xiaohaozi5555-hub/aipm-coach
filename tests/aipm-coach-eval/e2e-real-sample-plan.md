# 首批 3 个真实 E2E 样本补齐方案

目标：先补齐 `07-e2e` 节点的 3 个真实样本，让严格评测不再只报告 E2E 缺样本。评测脚本默认严格模式不会使用 `cases/e2e.json` 里的 `sample_output`。

## 当前缺口

| Case | 需要保存到 | 期望链路 |
|---|---|---|
| `e2e_project_agent_001` | `tests/aipm-coach-eval/samples/e2e_project_agent_001.txt` | `router -> guide -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar` |
| `e2e_portfolio_001` | `tests/aipm-coach-eval/samples/e2e_portfolio_001.txt` | `router -> expert_discussion -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar` |
| `e2e_tool_issue_001` | `tests/aipm-coach-eval/samples/e2e_tool_issue_001.txt` | `router -> guide -> explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar` |

每个真实样本还必须包含 `能力雷达图数据`，并包含可解析的 `scores` JSON。否则 `evaluate_e2e()` 会认为 E2E 没有可用能力雷达数据。

## 最省事采集流程

1. 生成采集 prompts：

```powershell
python tests\aipm-coach-eval\scripts\prepare_e2e_real_samples.py --write-prompts
```

2. 打开生成的 prompt sheet：

```text
tests/aipm-coach-eval/samples/e2e-collection-prompts.md
```

3. 逐个把 prompt 发给 AIPM Coach。每个 case 采一条完整闭环回答，直到输出包含：

- `router`
- 对应主模块：`guide` / `expert_discussion` / `explainer`
- `recorder`
- `reflection`
- `learning_evaluator`
- `gap_evaluator`
- `radar`
- `能力雷达图数据`
- `scores`

4. 把每个 case 的完整原始回答保存到对应 `.txt` 文件。不要改写回答，也不要复制 `sample_output`。

5. 检查 3 个文件是否齐了：

```powershell
python tests\aipm-coach-eval\scripts\prepare_e2e_real_samples.py --strict
```

6. 复跑严格评测：

```powershell
python tests\aipm-coach-eval\run_eval.py
```

7. 如果只想验证评测脚本机制是否正常，可以跑冒烟模式，但这个结果不能当真实评测：

```powershell
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```

## 采集输入摘要

### `e2e_project_agent_001`

输入主题：面向产品经理的需求澄清 Agent，要求教练覆盖 workflow、prompt、评估指标和项目交付路径。

采集重点：必须触发 `guide`，并走完整的记录、复盘、学习吸收评估、差距评估和能力雷达。

### `e2e_portfolio_001`

输入主题：把 AIPM Coach 自动评测包装成作品集案例，要求讨论叙事主线、亮点、风险和取舍。

采集重点：必须触发 `expert_discussion`，并体现作品集表达建议。

### `e2e_tool_issue_001`

输入主题：VPS Windows 环境预览前端项目，本地大陆电脑打不开 `localhost:3000`，要求排查并解释原理。

采集重点：必须同时触发 `guide` 和 `explainer`，并覆盖 `localhost`、`127.0.0.1`、端口、dev server、PowerShell `npm.ps1` 限制和安全隧道。
