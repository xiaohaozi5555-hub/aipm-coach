# AIPM Coach 架构说明

## 1. 架构目标

AIPM Coach 的目标不是“让模型更像一个老师”，而是把长期教练拆成可以路由、组合、暂停、恢复、记录和评测的模块系统。

架构需要同时满足：

- 一个简单问题可以快速进入单模块；
- 一个复杂问题可以组合多个专业视角；
- 项目内容能转成作品集表达，但不能虚构结果；
- 知识写入前必须经过用户确认；
- 学习吸收评估必须基于本轮知识与用户回答；
- 长期能力判断必须与单轮学习评分分开；
- 用户数据与教练自我改进规则必须持久化且互不混淆；
- 自动评测必须区分真实回答与内置 fixture。

## 2. 系统分层

```text
┌─────────────────────────────────────────────────────────────┐
│ 交互输入层                                                   │
│ 用户问题、截图、代码、报错、项目材料、知识笔记确认、复盘回答 │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 路由与编排层                                                 │
│ aipm-coach-router                                           │
│ - 识别问题类型与输入材料                                    │
│ - 读取 active lessons                                       │
│ - 选择模块、顺序与是否记录                                  │
│ - 判断是否加入作品集转化                                    │
└──────────────┬───────────────────────┬──────────────────────┘
               ▼                       ▼
┌─────────────────────────┐  ┌───────────────────────────────┐
│ 问题处理层 03—06         │  │ 求职转化层 07                 │
│ Guide / Explainer       │  │ Portfolio Explainer          │
│ Expert / Visual         │  │ 真实证据 → 项目叙事与面试表达 │
└──────────────┬──────────┘  └───────────────┬───────────────┘
               └──────────────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 学习闭环层 08—11                                            │
│ Recorder → 用户确认 → Reflection → 用户回答                 │
│ → Learning Evaluator → Gap Evaluator                        │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 本地状态与工具层                                             │
│ Markdown / JSON / JSONL / PNG                               │
│ 知识库、session、雷达、改进 backlog、active lessons          │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 评测与可观测层                                               │
│ case、真实 sample、fixture smoke、结构断言、报告与 dashboard │
└─────────────────────────────────────────────────────────────┘
```

## 3. 插件与 marketplace 结构

仓库根目录是一个 repo marketplace：

```text
.agents/plugins/marketplace.json
└─ source.path: ./plugins/aipm-coach

plugins/aipm-coach/
├─ .codex-plugin/plugin.json
├─ skills/
└─ scripts/
```

`marketplace.json` 让 Codex 能把仓库识别为可配置插件来源；`plugin.json` 提供稳定名称、语义版本、作者、描述、Skill 路径和界面元数据。根据 OpenAI 的插件结构约定，每个插件都需要 `.codex-plugin/plugin.json`，Skill 放在插件内的 `skills/`。

这个插件不包含 MCP server，也不连接外部业务系统。它的核心能力来自 Skill 编排和本地脚本，因此不需要 API Key 或第三方账户。

## 4. Router 决策模型

Router 接收四类信息：

1. **用户意图**：解决问题、理解概念、讨论方案、分析截图、复盘、作品集或评估；
2. **输入材料**：截图、代码、报错、产品想法、项目文档、知识笔记或复盘回答；
3. **流程状态**：是否已有第 08 步笔记、是否确认、是否回答第 09 步、是否完成第 10 步；
4. **教练策略**：`active-lessons.md` 中与本轮目标 Skill 匹配的生效规则。

### 4.1 路由伪代码

```text
read active_lessons

if only greeting or accidental trigger:
    do not start coaching workflow

if explicit full-workflow phrase and no concrete problem:
    ask for the problem or project context

if user confirms step 08 note:
    route to reflection_questioner
else if user has answered step 09:
    require step08 + step09 + answer
    route to learning_evaluator
else if step10 completed:
    require full comparison context
    route to gap_evaluator
else:
    classify problem type and inputs
    select one module for a simple request
    select multiple 03-06 modules for a complex request
    append portfolio_explainer when project/career context matches
    append recorder unless user opted out

merge relevant active lessons into execution instructions
```

### 4.2 路由矩阵

| 输入模式 | 必选模块 | 可选增强 | 后续 |
| --- | --- | --- | --- |
| 明确实操问题 | Guide | Explainer | Recorder |
| 纯概念解释 | Explainer | Visual | Recorder |
| 模糊想法或方案取舍 | Expert | Guide / Visual | Recorder |
| 截图或工作流分析 | Guide + Explainer + Visual | Expert | Recorder |
| 项目、AI 产品、Agent、评测 | Guide + Expert | Explainer + Visual | Portfolio → Recorder |
| 面试或作品集 | Guide + Expert + Portfolio | Visual | Recorder |
| 确认第 08 步笔记 | Reflection | 无 | 等待用户回答 |
| 已回答复盘问题 | Learning Evaluator | 无 | Gap Evaluator |
| 已完成第 10 步 | Gap Evaluator | Radar / session scripts | 流程结束 |

### 4.3 为什么不是全并行

03—06 可以并行提供互补视角，但以下节点必须串行：

- Portfolio 必须等待主问题处理结果，否则没有真实判断和证据可转换；
- Recorder 必须等待本轮教学内容完整，否则知识笔记不完整；
- Reflection 必须等待用户确认笔记；
- Learning Evaluator 必须等待用户回答；
- Gap Evaluator 必须等待第 10 步评估结果。

因此系统是“局部并行、主链串行”，而不是所有模块同时运行。

## 5. 三种运行模式

### 5.1 单模块快速回答

```text
用户 → Router → 单一 Skill → 回答
```

适用于目标明确、上下文充分、不需要其他视角的简单请求。

### 5.2 正常教练流程

```text
用户 → Router → 03—06 组合 → 可选 Portfolio → Recorder 草稿
                                               ↓
                                         等待用户确认
```

默认会产生可沉淀的知识笔记草稿，但不会未经确认就继续评分。

### 5.3 完整教练流程

```text
02 Router
→ 03—06 主模块
→ 07 Portfolio（命中时）
→ 08 Recorder 草稿
→ [用户确认门]
→ 09 Reflection
→ [用户回答门]
→ 10 Learning Evaluator
→ 11 Gap Evaluator
→ radar / self-improvement / session / strict eval
```

完整流程会跨多个用户回合，因为确认和复盘回答必须来自真实用户，不应由系统替用户自动填写。

## 6. Workflow 状态机

| 状态 | 进入条件 | 允许动作 | 禁止动作 |
| --- | --- | --- | --- |
| `ROUTING` | 收到新问题 | 分类、选择模块、读取规则 | 直接做长期能力评分 |
| `COACHING` | 路由完成 | 03—06 解决与讲解 | 把未出现的结果包装成证据 |
| `PORTFOLIO` | 命中项目/求职场景 | 转化真实内容 | 虚构业务指标或用户反馈 |
| `NOTE_DRAFT` | 主模块完成 | 生成笔记草稿 | 未确认就写入正式知识库 |
| `WAIT_NOTE_CONFIRMATION` | 草稿已展示 | 修改或等待 | 直接进入 Reflection |
| `REFLECTION` | 用户确认笔记 | 提出 1—3 个问题 | 给答案或评分 |
| `WAIT_REFLECTION_ANSWER` | 问题已提出 | 等待用户回答 | 替用户生成回答 |
| `LEARNING_EVAL` | 用户已回答且上下文完整 | 五维本轮吸收评估 | 泛化成长期能力定论 |
| `GAP_EVAL` | 第 10 步完成 | 十维能力、历史、训练任务 | 缺证据时给高置信结论 |
| `FINALIZING` | 雷达与改进项就绪 | 保存 session、转换样本、刷新评测 | 命令失败时声称成功 |
| `COMPLETE` | 收尾成功或明确报告失败 | 给出产物路径和状态 | 继续追加不存在的第 12 步 |

## 7. 模块边界

### 7.1 问题处理模块

- Guide 负责推进，不写概念百科；
- Explainer 负责教懂，不替用户做完整项目决策；
- Expert 负责假设与取舍，不把讨论包装成已经验证的结论；
- Visual 负责选择合适的图，不为了视觉效果牺牲结构准确性。

### 7.2 学习闭环模块

- Portfolio 不评分、不保存知识笔记；
- Recorder 不出复盘题、不评分；
- Reflection 只提问，不讲答案；
- Learning Evaluator 只判断本轮吸收，不判断长期差距；
- Gap Evaluator 做长期映射和收尾，不重新讲解本轮知识。

这些边界既写入 Skill，也被 `module-boundary.json` 和 `workflow-gating.json` 等 case 检查。

## 8. 数据架构

### 8.1 知识笔记

正式笔记是 Markdown，索引是一张可读表格。写入前必须经过用户确认。

```text
coach-data/knowledge-notes/YYYY-MM-DD-HH-mm-topic.md
coach-data/knowledge-index.md
```

### 8.2 能力雷达

第 11 步固定输出十个 0—5 分维度：

```text
需求分析、产品判断、AI 工作流理解、Agent 设计、Prompt 指令设计、
评估验证、项目交付、作品集表达、学习复盘、工具协作
```

`generate_capability_radar.py` 生成：

```text
YYYY-MM-DD-HH-mm-capability-radar.png
history.jsonl      # 全量追加历史
latest.json        # 最近 5 次窗口
index.md           # 人类可读索引
```

历史比较基于结构化 scores，不依赖图片像素。

### 8.3 真实 Session

完整 workflow 结束时保存结构化 JSON。核心字段包括：

```text
run_id, timestamp, user_input, router_result, called_modules,
module_outputs, knowledge_note_path, reflection_questions,
user_reflection_answer, learning_evaluation, gap_evaluation,
radar_scores, radar_artifacts, eval_case_id, full_raw_answer
```

保存脚本会拒绝缺字段、非法 run id、未知 case、fixture 标记或包含 `sample_output` 的伪真实 session。

## 9. 教练自我改进闭环

```text
本轮评估发现教练短板
          │
          ▼
coach_self_improvement 候选 JSON
          │
          ▼
improvement-backlog.jsonl
          │ validation gate
          ├─ 缺证据 / 无目标 Skill / 不可检查 → 留在 backlog
          ▼
active-lessons.md
          │
          ▼
下一轮 Router 启动前读取并合并到执行指令
          │
          ▼
评测下一轮是否覆盖 expected_next_behavior
```

这是一条“候选 → 验证 → 生效 → 下轮检查”的策略闭环。Gap Evaluator 不直接修改其他 Skill 正文，避免一次不稳定判断永久改变核心行为。

## 10. 评测架构

### 10.1 三种样本来源

| 来源 | 含义 | 是否代表真实表现 |
| --- | --- | --- |
| `real_sample` | 保存的真实 AI 教练原始回答 | 是 |
| `embedded_sample` | case 中预写的结构样例 | 否，只能冒烟 |
| `missing_sample` | 严格模式下没有真实回答 | 否，必须报告缺失 |

系统检查使用 `system_check`，用于插件清单、编码、雷达脚本和文件结构等不需要 AI 回答的部分。

### 10.2 信任等级

- `NOT_REAL_RUN_NO_REAL_SAMPLES`：无真实样本；
- `FIXTURE_SMOKE_ONLY`：只运行内置样例；
- `PARTIAL_REAL_EVAL_MISSING_SAMPLES`：有部分真实回答，仍有缺口；
- `PARTIAL_REAL_EVAL_WITH_FIXTURES`：真实与内置样例混合；
- `REAL_EVAL_HIGH_CONFIDENCE`：真实样本完整且达标；
- `REAL_EVAL_TRIAL_READY`：真实评测基本可用但仍有缺陷；
- `REAL_EVAL_NEEDS_FIXES`：真实评测未达标。

### 10.3 观测节点

```text
00 environment
01 router
02 module boundary
03 workflow gating
04 output structure
05 Chinese encoding
06 radar history
07 end-to-end
08 real session
09 portfolio explainer
10 self iteration
```

报告同时输出 Markdown、JSON 和 HTML dashboard，但生成文件默认不进入 Git。

## 11. 隐私与安全边界

- 插件本身不需要 API Key；
- 用户的笔记、session、截图、雷达与真实样本默认只保存在本机；
- `.gitignore` 排除这些运行数据，但使用者提交前仍应人工检查；
- 记录截图上下文时只能保存脱敏描述；
- 作品集模块禁止虚构指标、反馈或业务结果；
- 真实 session 转样本时优先使用原始回答，不允许拿 case fixture 伪造；
- 插件不包含网络服务、MCP server 或自动对外发送数据的代码。

## 12. 扩展一个新模块

新增模块至少需要完成六件事：

1. 在 `plugins/aipm-coach/skills/<name>/` 新建 `SKILL.md`；
2. 明确职责、输入、输出、禁止行为和前置条件；
3. 在 Router 中加入触发场景与执行顺序；
4. 判断它位于可并行的 03—06，还是必须串行的后续链路；
5. 在 `scripts/verify_package.py` 更新期望 Skill 集合；
6. 在评测 case 中加入路由、边界、门禁和输出结构检查。

如果新模块产生持久化数据，还需要补充 `.gitignore`、数据 schema、隐私说明和失败恢复行为。

## 13. 部署与可移植性

核心 Skill 可以由 Codex 插件缓存加载；完整学习闭环还需要一个可写工作区保存 `coach-data`，并需要仓库中的评测目录。因此推荐使用方式是：

```text
clone repository
→ install repo marketplace
→ install plugin
→ start a new Codex task from repository root
→ use AIPM Coach
```

这样 Skill、工具脚本、空白数据目录和评测 harness 处在同一稳定边界内。只通过远程 marketplace 安装也能使用核心教练模块，但完整 session/评测工作流应在克隆仓库内运行。
