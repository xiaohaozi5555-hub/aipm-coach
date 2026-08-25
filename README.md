# AIPM Coach

AIPM Coach 是一个面向 AI 产品经理学习、真实项目推进、作品集表达与能力复盘的模块化 Codex 教练插件。它不是一个固定人设的聊天提示词，而是一套包含问题路由、专业分工、流程门禁、知识沉淀、学习评估、长期能力雷达和教练自我改进的可执行 workflow。

**状态**：0.1.0 可安装发布候选版

**周期**：2026-05—2026-06

**规模**：10 个 Skill、4 个运行脚本、完整评测 harness

**项目角色**：个人独立完成（需求、产品设计、路由架构、Skill 设计、工具脚本、评测与文档）

> 当前 GitHub 仓库先按 Private 发布，供作者审阅。仓库改为 Public 后，其他人可以按[安装与使用](#安装与使用)直接安装。项目当前仍为 `UNLICENSED`，公开前还需要由作者确定许可证。

## 它解决什么问题

通用 AI 助手能回答问题，但很难稳定承担“长期教练”角色：

- 同一个问题可能同时需要实操指导、概念解释、取舍讨论和图示，单一提示词容易顾此失彼；
- 项目讨论结束后，结论常停留在聊天记录里，没有形成可复用知识和作品集素材；
- 用户说“我懂了”不代表真正吸收，需要通过复盘问题检验理解、迁移、应用和表达；
- 单次评分不能代表长期成长，需要保存历史、最近窗口和训练任务；
- 教练自己也会暴露问题，但如果只靠聊天记忆，下次很难稳定改进；
- 自动评测很容易把预写的标准答案当成真实回答，产生“看起来 100 分”的虚假可信度。

AIPM Coach 把这些问题拆成十个边界明确的模块，并用显式路由、用户确认门、结构化文件和可追溯评测把它们串成闭环。

## 目标用户

- 正在转型或学习 AI 产品管理的人；
- 需要推进 AI 产品、Agent、工作流、评测系统或工具项目的人；
- 需要把项目过程转成作品集和面试表达的人；
- 希望通过复盘问题检验自己是否真正学会的人；
- 希望长期观察 AIPM 能力变化，而不是只获得一次答案的人。

## 典型使用场景

### 1. 现实问题推进

用户带着产品、AI、工具、代码或项目阻塞进入。路由器调用指导者拆出关键阻塞、可选路径和最小下一步；如果涉及概念误区，再补充讲解者。

示例：

```text
AIPM教练：我的 Agent 项目功能很多，但不知道第一版应该先验证什么。
```

### 2. 概念学习

讲解者用新手可以理解的方式解释概念，并区分产品经理视角与技术实现视角；可视化讲解者在需要时补充 Mermaid 或对比表。

```text
AIPM教练：Function Calling、MCP 和 Agent workflow 分别解决什么问题？
```

### 3. 方案取舍与专家讨论

专家讨论者识别关键假设，比较多个方向的收益、代价、风险和适用条件，并从产品价值、AI 设计、可执行性、可验证性与作品集表达五个角度给出建议。

```text
AIPM教练：这个功能应该先用规则实现，还是直接交给大模型？
```

### 4. 截图、流程与架构分析

用户可以直接粘贴截图，也可以使用插件内的 Windows 截图脚本。路由器会组合指导、讲解和可视化模块；涉及账号、密钥或隐私时，只允许记录脱敏描述。

```text
AIPM教练：分析这张低代码 Agent 画布，告诉我哪里有结构问题。
```

### 5. 作品集与面试表达

项目类内容在主教练模块完成后，会进入作品集转化讲解者。它不虚构结果，而是把本轮真实内容重组为：问题发现、产品判断、取舍、AI/Agent 设计、已有证据、缺失证据和面试表达草稿。

```text
AIPM教练：把这次评测系统改造整理成作品集案例，但不要编造业务数据。
```

### 6. 完整学习闭环

当用户明确说“完整教练”“完整流程”或“完整 workflow”时，系统执行完整链路：先解决问题，再生成知识笔记草稿，等待用户确认，然后提问、评估吸收程度、形成十维能力雷达，最后保存真实 session 并刷新评测。

```text
AIPM教练：按完整流程处理这个项目问题，结束后保存 session 并刷新评测。
```

## 需求设计

### 功能需求

| 需求 | 设计响应 |
| --- | --- |
| 不同问题需要不同专业处理方式 | 用路由器识别问题类型、输入材料和缺失上下文，再选择一个或多个模块 |
| 复杂问题需要多个视角 | 指导、讲解、讨论、可视化可以组合，作品集转化在主模块之后串行加入 |
| 简单问题不能被流程拖慢 | “怎么做”“什么意思”“想法好不好”“只画图”可以收敛到单模块 |
| 学习结果需要沉淀 | 记录者生成结构化知识笔记草稿，用户确认后写入本地知识库与索引 |
| 不能未经确认就进入复盘 | 第 08 步后设置用户确认门；确认前不能调用第 09 步 |
| 评估必须基于本轮学习目标 | 第 10 步同时读取知识笔记、评估摘要、复盘问题和用户回答 |
| 长期能力需要可比较 | 第 11 步输出固定十维评分，维护完整历史、最近五次窗口和雷达图 |
| 项目过程要能转成求职材料 | 独立作品集转化模块，只使用真实证据，并明确区分已有证据与待补证据 |
| 教练需要持续改进 | 差距评估产生带证据的改进候选，脚本验证后才进入下一轮生效规则 |
| 评测不能把标准答案当真实结果 | 默认严格模式只读取真实回答；内置 `sample_output` 只能显式用于冒烟测试 |

### 非功能需求

- **边界清晰**：每个 Skill 只承担一种核心职责，不让记录者替代评估者，也不让评估者重新长篇授课；
- **流程可控**：通过显式前置条件阻止跳过确认、无上下文评分或提前进入长期差距判断；
- **隐私优先**：知识笔记、真实 session、截图和能力历史默认保存在本地并被 Git 忽略；
- **可追溯**：评分、作品集表达和教练改进都要求指向本轮输入、输出或文件证据；
- **可恢复**：核心状态写入 Markdown、JSON 和 JSONL，不依赖聊天上下文保存；
- **可扩展**：新增模块只需补 Skill、路由规则、流程位置和评测 case，不需要重写整套教练；
- **可验证**：插件结构、模块边界、workflow 门禁、输出格式、真实样本来源和运行脚本都有独立检查。

## 功能模块

| 模块 | 职责 | 主要输出 |
| --- | --- | --- |
| `aipm-coach-router` | 判断问题类型、输入材料、需要的模块与执行顺序 | 路由结果、模块列表、记录/作品集/复盘触发判断 |
| `aipm-guide` | 推进现实问题，给出路径、推荐方案和下一步 | 阻塞点、可选路径、推荐路径、行动步骤 |
| `aipm-explainer` | 解释概念、工具、原理和方法 | 一句话解释、AIPM 视角、例子、误区、自测题 |
| `aipm-expert-discussion` | 暴露假设，讨论方向和取舍 | 收益、代价、风险、适用条件、专家建议与追问 |
| `aipm-visual-explainer` | 把流程、架构、对比或能力结构可视化 | Mermaid、Markdown 表格或生图提示词 |
| `aipm-portfolio-explainer` | 把本轮真实内容转成作品集与面试材料 | 问题发现、判断取舍、设计亮点、证据与表达草稿 |
| `aipm-recorder` | 生成并保存结构化知识笔记 | 笔记草稿、索引条目、后续评估摘要 |
| `aipm-reflection-questioner` | 在用户确认笔记后提出少量高质量问题 | 1—3 个理解、迁移、应用或表达问题 |
| `aipm-learning-evaluator` | 对照本轮学习目标评估用户回答 | 五维吸收评分、遗漏、误解和补强建议 |
| `aipm-gap-evaluator` | 映射到长期 AIPM 能力并闭环保存 | 十维雷达、历史对比、训练任务、教练改进候选 |

## 整体架构

```text
用户问题 / 截图 / 代码 / 项目材料 / 学习反思
                         │
                         ▼
              ┌────────────────────┐
              │ 02 Router 路由层    │
              │ 类型、材料、上下文、│
              │ 模块组合、执行顺序  │
              └──────────┬─────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   03 Guide       04 Explainer     05 Expert Discussion
   实操推进          概念讲解           假设与取舍
          └──────────────┼──────────────┘
                         ▼
                 06 Visual Explainer
                   流程 / 架构 / 对比
                         │
              项目、Agent、作品集相关？
                    ┌────┴────┐
                   是         否
                    ▼          │
          07 Portfolio Explainer
               作品集与面试转化
                    └────┬─────┘
                         ▼
                  08 Recorder
             生成知识笔记草稿与索引条目
                         │
                 用户审查确认门
                   ┌─────┴─────┐
                未确认         已确认
              修改/等待          ▼
                         09 Reflection
                         1—3 个复盘问题
                                │ 用户回答
                                ▼
                         10 Learning Eval
                         本轮五维吸收评估
                                │
                                ▼
                         11 Gap Evaluator
                  十维雷达 / 历史 / 训练任务
                  教练改进候选 / session 落地
```

更完整的路由表、门禁状态、数据流和扩展方法见 [ARCHITECTURE.md](ARCHITECTURE.md)。

## 路由设计

### 简单问题收敛

| 用户意图 | 默认模块 |
| --- | --- |
| “怎么做” | `aipm-guide` |
| “什么意思” | `aipm-explainer` |
| “这个想法好不好” | `aipm-expert-discussion` |
| “画图 / 可视化” | `aipm-visual-explainer` |

### 复杂问题组合

| 场景 | 模块组合 |
| --- | --- |
| 项目设计 | Guide + Expert + Visual + Portfolio |
| AI 产品 / Agent / 评测系统 | Guide + Expert + Visual + Portfolio |
| 工具或环境卡点 | Guide + Explainer |
| 截图分析 | Guide + Explainer + Visual |
| 面试与作品集优化 | Guide + Expert + Portfolio |
| 学习困惑 | Explainer + Expert |
| 复杂 AIPM 项目 | Guide + Explainer + Expert + Visual + Portfolio |

正常进入 03—06 后，默认触发 Recorder；只有纯寒暄、误触发或用户明确说“这次不要记录”时跳过。Portfolio 只在项目、AI 产品、Agent、评测、复盘或求职表达相关场景加入。

## Workflow 门禁

完整流程不是一次回答内强行跑完，而是有两个真实的人机边界：

1. **知识笔记确认门**：Recorder 先生成草稿；用户确认后才保存并进入 Reflection；
2. **复盘回答门**：Reflection 只提问；用户回答后才进入 Learning Evaluator。

后续模块的前置条件如下：

| 目标节点 | 必需上下文 | 缺失时的行为 |
| --- | --- | --- |
| Reflection | 已确认的 08 知识笔记 | 返回 08 或等待确认，不凭空提问 |
| Learning Evaluator | 08 笔记、08 摘要、09 问题、用户回答 | 明确报告缺少哪一项，不评分 |
| Gap Evaluator | 08、09、用户回答、10 评估与 10 摘要 | 要求先完成第 10 步，不做长期能力判断 |
| Session 收尾 | 完整模块输出、雷达数据、评测 case id | 保存失败时明确报告，不宣称已写入评测端 |

## 数据与记忆

插件不依赖远程数据库，运行数据默认写在当前仓库的 `coach-data/`：

```text
coach-data/
├─ knowledge-notes/       用户确认后的知识笔记
├─ knowledge-index.md     笔记检索入口
├─ session-drafts/        完整 workflow 的待校验草稿
├─ session-runs/          校验通过的真实 session
├─ capability-radar/      PNG、完整历史、最近五次与索引
├─ coach-policy/
│  └─ active-lessons.md   下一轮必须读取的生效改进规则
└─ improvement-backlog.jsonl
                          有证据但尚待筛选的教练改进候选
```

这里同时维护两种不同的“记忆”：

- **用户学习记忆**：知识笔记、复盘、能力雷达，描述用户本轮和长期学习状态；
- **教练策略记忆**：改进 backlog 与 active lessons，描述教练下一轮应该改变什么行为。

两者不能混在一起。教练规则必须包含具体短板、证据、目标 Skill、下一步行为和可检查信号，才能由脚本提升为生效规则。

## 评测体系

评测目录不是用来制造漂亮分数，而是用来区分三件事：

1. 插件结构和工具脚本是否能运行；
2. 内置 case 的断言逻辑是否合理；
3. AI 教练面对真实问题时是否真的满足要求。

默认严格模式：

```powershell
python tests\aipm-coach-eval\run_eval.py
```

它只读取 `samples/<case_id>.txt` 中保存的真实原始回答。缺少样本时会明确标记 `NOT_REAL_RUN_NO_REAL_SAMPLES`，不会自动拿 case 里的标准答案补位。

显式样例冒烟：

```powershell
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```

这个模式允许使用内置 `sample_output`，只能证明评测 harness 和断言能跑通，不能证明真实教练表现达到同样分数。

评测覆盖：

- 插件环境与清单；
- Router 模块选择；
- 各 Skill 职责边界；
- 08—11 workflow 门禁；
- 固定输出结构与中文编码；
- 能力雷达历史和最近五次窗口；
- 项目、作品集、工具问题的端到端链路；
- 真实 session 完整性与样本转换；
- 作品集表达信号；
- 教练自我改进规则是否被下一轮行为吸收。

### 发布候选版复验结果

| 检查 | 结果 | 解释 |
| --- | --- | --- |
| 发布包结构检查 | 通过 | manifest、marketplace、10 个 Skill、备份/缓存排除均符合预期 |
| 官方 `plugin-creator` 校验 | 通过 | `.codex-plugin/plugin.json` 可被当前插件 schema 接受 |
| 10 个 Skill 独立校验 | 10 / 10 通过 | front matter、名称与目录结构有效 |
| fixture 冒烟 | 92.31 / 100，`FIXTURE_SMOKE_ONLY` | Router、边界、门禁、格式、雷达、E2E、作品集和自我迭代均通过；唯一未通过节点是公开包不含真实 session |
| 默认严格模式 | 正确返回 `NOT_REAL_RUN_NO_REAL_SAMPLES` | 0 个真实回答、36 个缺失样本，没有用内置样例冒充真实结果 |

上述 92.31 分不是“AI 教练真实能力分”，只说明发布包内的评测机制能对内置结构样例正常运行。真实能力结论必须在使用者积累真实回答后由严格模式给出。

## 关键设计决策

1. **用 Router 组合模块，而不是写一个巨型 Prompt**

   每个模块只处理一种问题，复杂问题再由路由器组合；放弃“一个系统提示词同时完成指导、教学、记录和评分”的做法，因为职责冲突难以测试。

2. **简单问题单模块，复杂问题多模块**

   路由默认允许多模块，但“怎么做”“什么意思”等明确意图会收敛；放弃所有问题都强制跑完整链路，避免用户为一个小问题等待整套仪式。

3. **把作品集转化放在解决问题之后、记录之前**

   先获得真实判断与证据，再整理表达材料；放弃直接让模型“包装项目”，避免虚构业务结果和空泛亮点。

4. **用人工确认门保护知识库质量**

   Recorder 只先生成草稿，用户确认后才写入并进入复盘；放弃自动把每次回答直接变成长期知识，避免错误内容被固化。

5. **区分本轮学习吸收与长期能力差距**

   第 10 步只判断本轮是否学会，第 11 步再映射到十维长期能力；放弃用一次回答直接给用户下“整体能力”结论。

6. **本地文件是真实状态源，聊天上下文不是**

   笔记、session、雷达历史和教练规则都落地到结构化文件；放弃依赖长对话记忆，因为它不可审计、不可恢复，也难以跨任务使用。

7. **真实评测与 fixture 冒烟严格分开**

   默认不使用内置标准答案，只有显式参数才允许；放弃“没有真实样本就自动补 fixture 继续打分”，避免对能力产生虚假结论。

8. **教练自我改进也必须过证据门禁**

   只有带观察证据、目标 Skill、可执行行为与评测信号的候选才能进入 active lessons；放弃把模糊建议直接写进长期规则。

## 安装与使用

根据 [OpenAI 官方插件说明](https://learn.chatgpt.com/docs/plugins)，插件可以在支持的 ChatGPT/Codex 桌面界面和 Codex CLI 中使用；Codex CLI 安装后应启动一个新任务加载插件。插件需要 `.codex-plugin/plugin.json`，本仓库同时提供 repo marketplace，结构遵循[官方插件打包说明](https://developers.openai.com/plugins/build/plugins)。

### 环境要求

- Git；
- Codex CLI，且 `codex plugin --help` 可正常运行；
- Python 3.11 或更新版本；
- Pillow，仅用于生成能力雷达图；
- 截图辅助脚本目前面向 Windows PowerShell，其他核心 Skill 不依赖 Windows。

### 方式一：克隆后安装（推荐，支持完整数据与评测）

```powershell
git clone https://github.com/xiaohaozi5555-hub/aipm-coach.git
Set-Location aipm-coach
python -m pip install -r requirements.txt
codex plugin marketplace add .
codex plugin add aipm-coach@aipm-coach-marketplace
```

也可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

安装完成后，从这个仓库目录启动一个新的 Codex 任务。这样知识笔记、session、雷达历史和本地评测都能使用仓库内的标准目录。

### 方式二：直接添加 GitHub marketplace

```powershell
codex plugin marketplace add xiaohaozi5555-hub/aipm-coach
codex plugin add aipm-coach@aipm-coach-marketplace
```

这种方式适合先使用指导、讲解、讨论和可视化等 Skill。需要完整的本地知识库、session 和评测闭环时，仍建议克隆仓库并从仓库根目录运行。

### 验证安装包

```powershell
python scripts\verify_package.py
python tests\aipm-coach-eval\run_eval.py --allow-fixtures
```

安装或更新插件后请启动新任务，再使用类似提示：

```text
AIPM教练：解释 Agent workflow 和普通聊天机器人的区别。

AIPM教练：分析我的项目方案，给出产品取舍与下一步。

AIPM教练：按完整流程处理我的问题，并在结束后保存 session。
```

## 截图辅助

Windows 下可以使用：

```powershell
powershell -ExecutionPolicy Bypass -File plugins\aipm-coach\scripts\capture_screen.ps1
powershell -ExecutionPolicy Bypass -File plugins\aipm-coach\scripts\save_clipboard_image.ps1
```

截图默认保存到本地 `coach-data/screenshots/`。如果截图中包含账号、密钥、真实姓名或其他隐私，后续知识笔记只能记录脱敏描述。

## 目录结构

```text
.agents/plugins/marketplace.json      Repo marketplace 入口
plugins/aipm-coach/
  .codex-plugin/plugin.json           插件身份、版本与界面元数据
  skills/                              10 个教练模块
  scripts/                             截图、雷达、session 与自我改进工具
coach-data/                            空白的本地运行数据模板
tests/aipm-coach-eval/
  cases/                               路由、门禁、结构与 E2E case
  fixtures/                            雷达与学习评估的非个人样例
  samples/                             真实回答落点，默认不提交
  reports/                             评测输出，默认不提交
  run_eval.py                          严格评测与 fixture 冒烟入口
docs/                                  评测可信度升级说明
scripts/verify_package.py              发布包结构检查
install.ps1                            Windows 安装脚本
requirements.txt                       Python 运行依赖
```

## 隐私与公开边界

本仓库发布的是插件、通用测试和空白数据结构，主动排除了：

- 作者个人知识笔记和知识索引内容；
- 真实教练 session、用户输入与复盘回答；
- 个人能力评分、雷达历史和训练计划；
- 保存过的截图、临时文件和运行日志；
- `cloudflared.exe` 等本地二进制工具；
- 机器绝对路径、账号、联系方式、密钥与 `.env`；
- Python 字节码、缓存和备份文件；
- 原始 Git 历史，发布仓库使用新的单次初始提交。

`.gitignore` 默认排除新生成的个人数据和真实回答。使用者仍应在提交代码前自行检查，因为知识笔记与 session 可能包含项目或个人信息。

## 已知限制

1. **当前是 Codex 插件，不是独立 Web 应用**：需要在支持插件的 Codex 桌面界面或 Codex CLI 中使用；官方说明目前不支持在 IDE 扩展中浏览和安装插件。
2. **完整闭环要求从仓库根目录运行**：技能本身可以独立加载，但 session 转换和本地评测依赖仓库内的 `coach-data/` 与 `tests/`。
3. **流程纪律由 Skill 指令和 Codex 执行保证**：当前没有单独的后端状态机服务；如果执行环境忽略 Skill 指令，文件落地和自动收尾可能失败。
4. **真实回答样本不随仓库公开**：这是隐私保护选择，也意味着下载者第一次运行严格评测时会看到“缺少真实样本”，而不是一个虚假的高分。
5. **评测以结构、关键词、文件和流程证据为主**：它能检查门禁和可追溯性，但不能完全替代人工对回答专业质量的判断。
6. **雷达分数依赖当前轮次证据**：未在本轮体现的能力会保守评分，不应把一次雷达图当成长期能力定论。
7. **截图脚本主要验证于 Windows**：其他系统可以直接向 Codex 上传截图，但本仓库的 PowerShell 辅助脚本未做跨平台适配。
8. **尚未确定开源许可证**：当前清单为 `UNLICENSED`。如果要允许公众复制、修改和再分发，需要作者在公开前选择并加入许可证。

## 文档索引

- [ARCHITECTURE.md](ARCHITECTURE.md)：完整模块架构、路由、门禁、数据流、评测与扩展方式；
- [tests/aipm-coach-eval/README.md](tests/aipm-coach-eval/README.md)：真实评测、fixture 冒烟、信任等级与报告说明；
- [docs/aipm-coach-eval-upgrade-template.md](docs/aipm-coach-eval-upgrade-template.md)：为什么要把标准答案与真实回答严格分开；
- [coach-data/README.md](coach-data/README.md)：本地知识、session、雷达和教练策略数据；
- [plugins/aipm-coach/.codex-plugin/plugin.json](plugins/aipm-coach/.codex-plugin/plugin.json)：插件元数据与默认提示；
- [OpenAI 官方插件说明](https://learn.chatgpt.com/docs/plugins)；
- [OpenAI 官方插件打包说明](https://developers.openai.com/plugins/build/plugins)。

---

作者：肖晨昊
