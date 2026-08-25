# E2E Real Sample Collection Prompts

这些 prompts 用于采集首批 3 个真实 E2E 样本。把 AIPM Coach 的完整原始回答保存到对应 `samples/<case_id>.txt`，不要改写或补写。

## e2e_project_agent_001: 项目 Agent 设计闭环

- Target file: `samples\e2e_project_agent_001.txt`
- Expected E2E markers: `router -> guide -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar`
- Collection note: 重点覆盖 router -> guide -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar。真实样本应包含作品集转化讲解和最终能力雷达数据。

### Prompt

```text
AIPM教练，我想做一个面向产品经理的需求澄清 Agent，能把用户一句话需求拆成目标、用户、场景、约束、验收标准，但我不知道该怎么设计 workflow、prompt、评估指标和项目交付路径。请你按完整教练流程指导我，并在后续带我完成知识记录、复盘、学习吸收评估和能力雷达。
```

### Minimum save requirement

- 保存完整原始回答，包含路由、主教练模块、08 记录、09 复盘、10 学习吸收评估、11 差距评估和能力雷达数据。
- 回答中需要能命中 case 的 expected steps，以及 `能力雷达图数据` 和可解析的 `scores` JSON。

## e2e_portfolio_001: 作品集表达闭环

- Target file: `samples\e2e_portfolio_001.txt`
- Expected E2E markers: `router -> expert_discussion -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar`
- Collection note: 重点覆盖 router -> expert_discussion -> portfolio_explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar。真实样本应体现作品集转化讲解和作品集表达建议。

### Prompt

```text
AIPM教练，我想把 AIPM Coach 自动评测这件事包装成作品集案例，但担心只是在展示脚本和分数，不能体现产品判断、取舍、验证证据和面试表达。请你用专家讨论方式帮我判断叙事主线、亮点、风险和取舍，并继续走完记录、复盘、学习评估和能力雷达。
```

### Minimum save requirement

- 保存完整原始回答，包含路由、主教练模块、08 记录、09 复盘、10 学习吸收评估、11 差距评估和能力雷达数据。
- 回答中需要能命中 case 的 expected steps，以及 `能力雷达图数据` 和可解析的 `scores` JSON。

## e2e_tool_issue_001: 工具环境问题闭环

- Target file: `samples\e2e_tool_issue_001.txt`
- Expected E2E markers: `router -> guide -> explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar`
- Collection note: 重点覆盖 router -> guide -> explainer -> recorder -> reflection -> learning_evaluator -> gap_evaluator -> radar。真实样本应包含排障步骤和原理解释。

### Prompt

```text
AIPM教练，我在 VPS 的 Windows 环境里预览前端项目，用户在大陆本地电脑打不开 localhost:3000。请你帮我排查 localhost、127.0.0.1、端口、dev server、PowerShell npm.ps1 限制和安全隧道的关系，并解释原理，然后继续完成知识记录、复盘、学习吸收评估和能力雷达。
```

### Minimum save requirement

- 保存完整原始回答，包含路由、主教练模块、08 记录、09 复盘、10 学习吸收评估、11 差距评估和能力雷达数据。
- 回答中需要能命中 case 的 expected steps，以及 `能力雷达图数据` 和可解析的 `scores` JSON。
