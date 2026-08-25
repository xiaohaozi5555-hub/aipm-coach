# AIPM Coach 自动评测说明

这个目录用于评测本项目里的 `aipm-coach` AI 教练插件。

重要变化：默认评测不再偷偷使用 case 文件里的 `sample_output`。如果没有真实 AI 教练回答文件，报告会明确标记为“缺少样本”，并说明这不是一次真实评测。

## 什么是真实评测

真实评测是指：

1. 你真的向 AI 教练插件提出了某个测试问题。
2. 你把 AI 教练的完整原始回答保存到 `samples/<case_id>.txt`。
3. 评测脚本读取这个真实回答，再判断它是否满足路由、流程、结构、能力雷达等规则。

只有这种情况下，分数才代表 AI 教练真实表现。

## 什么是样例测试

样例测试是指：

1. 没有真实 AI 教练回答。
2. 脚本使用 case JSON 里提前写好的 `sample_output`。
3. 这只能说明评测脚本和断言规则可以跑通。

样例测试不能说明 AI 教练真实表现是 100 分。

## 为什么以前的 100 分不一定可信

旧版逻辑是：

1. 先找 `samples/<case_id>.txt`。
2. 如果找不到，就自动使用 case 里的 `sample_output`。
3. 然后照样给出总分。

这会把“标准答案样例”当成“真实 AI 回答”来评测，所以很容易得到漂亮但不真实的 100 分。

## 如何保存真实 AI 教练回答

每个 case 都有一个 `case_id`。例如：

```text
router_project_design_001
```

你真实测试插件后，把完整回答保存到：

```text
tests/aipm-coach-eval/samples/router_project_design_001.txt
```

不要改写、润色或补全回答。保存 AI 教练原始输出即可。

## 从真实 session 自动生成样本

完整 workflow 结束后，优先先保存结构化 session：

```text
coach-data/session-runs/<run_id>.json
```

session 字段和命令见：

```text
coach-data/session-runs/README.md
tests/aipm-coach-eval/session-sample-workflow.md
```

完整 workflow 收尾命令：

```powershell
python plugins\aipm-coach\scripts\record_session_run.py --latest-draft --run-eval
```

这个命令会保存 session、在可行时转换严格评测样本，并刷新严格评测报告。每次完整使用 AI 教练都应该运行一次。

在 AIPM Coach 完整 workflow 中，这一步应由当前助手在 11 AIPM 差距评估完成后自动执行：先生成 `coach-data/session-drafts/<run_id>.json`，再运行上面的 `record_session_run.py --latest-draft --run-eval`。不要只把命令展示给用户，也不要要求用户手动补写正式 session。

如果需要单独排查转换问题，再手动把 session 转成严格评测读取的真实样本：

```powershell
python tests\aipm-coach-eval\scripts\session_to_sample.py --session coach-data\session-runs\<run_id>.json
```

也可以转换最近一次 session：

```powershell
python tests\aipm-coach-eval\scripts\session_to_sample.py --latest
```

转换脚本只写入 `tests/aipm-coach-eval/samples/<eval_case_id>.txt`，并会拒绝把 case JSON 里的 `sample_output` 当成真实回答。`sample_output` 只能用于 `--allow-fixtures` 冒烟测试。

## 首批 E2E 真实样本采集

首批优先补齐 `07-e2e` 的 3 个真实样本：

```text
e2e_project_agent_001
e2e_portfolio_001
e2e_tool_issue_001
```

生成采集 prompts 和缺口检查：

```powershell
python tests\aipm-coach-eval\scripts\prepare_e2e_real_samples.py --write-prompts
```

采集方案见：

```text
tests/aipm-coach-eval/e2e-real-sample-plan.md
tests/aipm-coach-eval/samples/e2e-collection-prompts.md
tests/aipm-coach-eval/samples/README.md
```

补齐后可先检查 3 个 E2E 样本是否都存在：

```powershell
python tests\aipm-coach-eval\scripts\prepare_e2e_real_samples.py --strict
```

## 默认严格评测

从项目根目录运行：

```powershell
python tests\aipm-coach-eval\run_eval.py
```

默认严格模式只读取 `samples/` 里的真实回答。

如果没有真实回答，报告会写：

```text
Trust level: NOT_REAL_RUN_NO_REAL_SAMPLES
Conclusion: 不是一次真实评测：缺少真实 AI 教练回答样本。
```

## 样例冒烟测试

如果只是想确认评测脚本能跑通，可以运行：

```powershell
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```

这个模式允许使用 case 里的 `sample_output`。报告会标记：

```text
Trust level: FIXTURE_SMOKE_ONLY
```

这不是 AI 教练真实能力分数。

## 怎么看可信等级

- `NOT_REAL_RUN_NO_REAL_SAMPLES`：没有真实回答，不是真实评测。
- `FIXTURE_SMOKE_ONLY`：使用内置样例，只是冒烟测试。
- `PARTIAL_REAL_EVAL_MISSING_SAMPLES`：有部分真实回答，但还有 case 缺样本。
- `PARTIAL_REAL_EVAL_WITH_FIXTURES`：混用了真实回答和内置样例。
- `REAL_EVAL_HIGH_CONFIDENCE`：全部使用真实回答，且分数达标。
- `REAL_EVAL_TRIAL_READY`：真实评测基本可用，但仍有缺陷。
- `REAL_EVAL_NEEDS_FIXES`：真实评测未达标，需要修复。

## 报告位置

每次运行会更新：

```text
tests/aipm-coach-eval/reports/latest-report.md
tests/aipm-coach-eval/reports/latest-report.json
tests/aipm-coach-eval/reports/capability-radar-report.md
tests/aipm-coach-eval/reports/dashboard.html
```

报告会显示：

- 总分
- 可信等级
- 测试用例总数
- 真实回答数量
- 内置样例数量
- 缺少样本数量
- 每个 case 的通过/失败原因
- 每个判断的关键词证据
- 雷达图报告地址

## 本地 HTML Dashboard

每次运行评测后，会刷新：

```text
tests/aipm-coach-eval/reports/dashboard.html
```

也会生成模式专属页面：

```text
tests/aipm-coach-eval/reports/strict-real-samples-dashboard.html
tests/aipm-coach-eval/reports/fixture-smoke-dashboard.html
```

直接用浏览器打开 HTML 文件即可查看。页面包含：

- 本次评测分数和可信等级
- 真实回答、内置样例、缺失样本数量
- 节点通过情况
- 每个 case 的原因和证据
- 运行历史
- 能力雷达图
- 作品集表达能力补强计划

该页面带 8 秒自动刷新。如果评测脚本重新运行，页面会自动看到最新状态。

## 新增架构观测节点

当前评测端额外观测三项架构改造：

- `08-real-session`：检查 `coach-data/session-runs/*.json` 是否存在、是否包含完整 session 字段、是否能安全转换为 `samples/<case_id>.txt`。没有真实 session 时只给出缺失提示，不使用 `sample_output` 冒充真实样本。
- `09-portfolio-explainer`：检查作品集讲解回答是否覆盖作品集素材、问题发现、产品判断、验证证据、面试表达、还缺什么证据。命中率会写入报告和 dashboard。
- `10-self-iteration`：检查 `improvement-backlog.jsonl` 是否记录短板、`active-lessons.md` 是否吸收规则、下一轮回答是否覆盖上轮要求补强的行为。

分数解释：

- 真实 session 节点通过，表示至少有一条真实 workflow session 可以转成严格评测样本。
- 作品集讲解命中率 = 已命中的表达信号 / 应命中的表达信号。
- 自我迭代覆盖 = 下一轮回答命中的补强行为 / active lesson 要求补强的行为。
