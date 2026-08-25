# AIPM Coach Eval Samples

严格真实评测只读取本目录下的真实 AI 教练原始回答：

```text
tests/aipm-coach-eval/samples/<case_id>.txt
```

首批要补齐的 3 个 E2E 样本是：

```text
e2e_project_agent_001.txt
e2e_portfolio_001.txt
e2e_tool_issue_001.txt
```

保存规则：

- 每个文件只放对应 case 的一次完整原始回答。
- 不要使用 `cases/e2e.json` 里的 `sample_output` 伪造真实样本。
- 不要润色、改写、补齐 AI 回答；评测要看真实输出是否自然命中规则。
- 如果回答分多轮完成，把完整闭环合并到同一个 `<case_id>.txt`，保留轮次顺序。
- E2E 样本至少要包含路由、主教练模块、08 记录、09 复盘、10 学习吸收评估、11 差距评估，以及 `能力雷达图数据` 和 `scores` JSON。

生成采集 prompts 和检查缺口：

```powershell
python tests\aipm-coach-eval\scripts\prepare_e2e_real_samples.py --write-prompts
```

补齐样本后复跑严格评测：

```powershell
python tests\aipm-coach-eval\run_eval.py
```
