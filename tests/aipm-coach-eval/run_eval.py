#!/usr/bin/env python
"""Credible semi-automatic evaluation harness for the AIPM Coach plugin."""

from __future__ import annotations

import argparse
import html
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parent
WORKSPACE_ROOT = EVAL_ROOT.parents[1]
PLUGIN_ROOT = WORKSPACE_ROOT / "plugins" / "aipm-coach"
REPORTS_DIR = EVAL_ROOT / "reports"
SAMPLES_DIR = EVAL_ROOT / "samples"
CASES_DIR = EVAL_ROOT / "cases"
FIXTURES_DIR = EVAL_ROOT / "fixtures"

CASE_FILES = [
    "router.json",
    "module-boundary.json",
    "workflow-gating.json",
    "output-structure.json",
    "e2e.json",
    "portfolio-explainer.json",
    "self-iteration.json",
]

EXPECTED_SKILLS = [
    "aipm-coach-router",
    "aipm-guide",
    "aipm-explainer",
    "aipm-expert-discussion",
    "aipm-visual-explainer",
    "aipm-portfolio-explainer",
    "aipm-recorder",
    "aipm-reflection-questioner",
    "aipm-learning-evaluator",
    "aipm-gap-evaluator",
]

SCORE_DIMENSIONS = [
    "需求分析能力",
    "产品判断能力",
    "AI 工作流理解",
    "Agent 设计能力",
    "Prompt 指令设计能力",
    "评估验证能力",
    "项目交付能力",
    "作品集表达能力",
    "学习复盘能力",
    "工具协作能力",
]

MOJIBAKE_TOKENS = ["鐨", "浣", "銆", "锛", "璇", "姣", "妯", "鍔", "闆", "杈", "棶"]

NODE_WEIGHTS = {
    "00-environment": 10,
    "01-router": 15,
    "02-module-boundary": 15,
    "03-workflow-gating": 15,
    "04-output-structure": 10,
    "05-chinese-encoding": 10,
    "06-radar-history": 15,
    "07-e2e": 10,
    "08-real-session": 10,
    "09-portfolio-explainer": 10,
    "10-self-iteration": 10,
}

SESSION_RUNS_DIR = WORKSPACE_ROOT / "coach-data" / "session-runs"
IMPROVEMENT_BACKLOG_PATH = WORKSPACE_ROOT / "coach-data" / "improvement-backlog.jsonl"
ACTIVE_LESSONS_PATH = WORKSPACE_ROOT / "coach-data" / "coach-policy" / "active-lessons.md"

REQUIRED_SESSION_FIELDS = [
    "run_id",
    "timestamp",
    "user_input",
    "router_result",
    "called_modules",
    "module_outputs",
    "knowledge_note_path",
    "reflection_questions",
    "user_reflection_answer",
    "learning_evaluation",
    "gap_evaluation",
    "radar_scores",
    "radar_artifacts",
    "eval_case_id",
]

PORTFOLIO_SIGNAL_GROUPS = {
    "portfolio_material": ["作品集素材", "作品集表达材料", "本轮内容如何变成作品集素材"],
    "problem_discovery": ["问题发现", "可展示的问题发现"],
    "product_judgment": ["产品判断", "产品判断与取舍"],
    "validation_evidence": ["验证证据", "证据"],
    "interview_expression": ["面试表达", "面试表达版本"],
    "missing_evidence": ["还缺什么证据", "仍需补充证据", "缺什么证据"],
}

SELF_ITERATION_BEHAVIOR_GROUPS = {
    "problem_discovery": ["问题发现", "可展示的问题发现"],
    "product_judgment": ["产品判断", "取舍"],
    "validation_evidence": ["验证证据", "证据"],
    "missing_evidence": ["还缺什么证据", "仍需补充证据"],
    "interview_expression": ["面试表达", "面试表达版本"],
}

SOURCE_LABELS = {
    "real_sample": "真实回答",
    "embedded_sample": "内置样例",
    "missing_sample": "缺少样本",
    "system_check": "系统检查",
}

MODE_LABELS = {
    "strict_real_samples": "严格真实评测",
    "fixture_smoke": "样例冒烟测试",
}

TRUST_LABELS = {
    "NOT_REAL_RUN_NO_REAL_SAMPLES": "非真实评测：缺少真实回答",
    "FIXTURE_SMOKE_ONLY": "样例冒烟：只验证评测脚本",
    "PARTIAL_REAL_EVAL_MISSING_SAMPLES": "部分真实评测：仍缺样本",
    "PARTIAL_REAL_EVAL_WITH_FIXTURES": "部分真实评测：混用内置样例",
    "REAL_EVAL_HIGH_CONFIDENCE": "真实评测：高可信",
    "REAL_EVAL_TRIAL_READY": "真实评测：可小范围试用",
    "REAL_EVAL_NEEDS_FIXES": "真实评测：需要修复",
}

WORKFLOW_STAGES = [
    {
        "id": "router",
        "name": "02 路由器",
        "skills": ["aipm-coach-router"],
        "description": "判断用户问题类型，选择后续教练模块，并阻止过早进入 10/11。",
        "nodes": ["01-router"],
    },
    {
        "id": "main_coach",
        "name": "03-06 主教练模块",
        "skills": ["aipm-guide", "aipm-explainer", "aipm-expert-discussion", "aipm-visual-explainer"],
        "description": "完成指导、解释、专家讨论和可视化说明，形成可被记录的学习内容。",
        "case_ids": ["boundary_guide_001", "boundary_explainer_001", "boundary_expert_001", "boundary_visual_001", "structure_visual_001"],
    },
    {
        "id": "portfolio_explainer",
        "name": "07 作品集转化讲解",
        "skills": ["aipm-portfolio-explainer"],
        "description": "把 03-06 的教练内容转成作品集表达、面试表达和项目叙事材料，再交给 08 记录者沉淀。",
        "case_ids": ["boundary_portfolio_explainer_001", "structure_portfolio_explainer_001"],
    },
    {
        "id": "recorder",
        "name": "08 记录者",
        "skills": ["aipm-recorder"],
        "description": "吸收 03-06 和必要的作品集转化讲解输出，生成知识笔记，等待用户确认，并落地到知识库。",
        "case_ids": ["boundary_recorder_001", "structure_recorder_001"],
    },
    {
        "id": "reflection",
        "name": "09 复盘提问",
        "skills": ["aipm-reflection-questioner"],
        "description": "在 08 确认后提出 1-3 个复盘问题，不直接评分。",
        "case_ids": ["boundary_reflection_001", "gating_reflection_without_08_001", "gating_confirm_to_09_001"],
    },
    {
        "id": "learning_eval",
        "name": "10 学习吸收评估",
        "skills": ["aipm-learning-evaluator"],
        "description": "基于 08、09 和用户回答评估理解度、准确度、迁移度、应用度和表达度。",
        "case_ids": ["boundary_learning_eval_001", "gating_learning_without_09_001", "gating_answer_to_10_001", "structure_learning_eval_001"],
    },
    {
        "id": "gap_eval",
        "name": "11 能力差距与雷达图",
        "skills": ["aipm-gap-evaluator"],
        "description": "基于 10 的结果生成 10 维能力评估、雷达图、历史记录和下一步训练任务。",
        "case_ids": ["boundary_gap_eval_001", "gating_gap_without_10_001", "router_gap_eval_001", "structure_gap_json_001", "radar_history_001"],
    },
    {
        "id": "e2e",
        "name": "端到端闭环",
        "skills": ["router -> 03-06 -> 07 -> 08 -> 09 -> 10 -> 11"],
        "description": "模拟完整教练流程，确认主教练、作品集转化、记录、复盘、评估和雷达图节点能够串起来。",
        "nodes": ["07-e2e"],
    },
]

PORTFOLIO_EXPRESSION_PLAN = {
    "title": "作品集表达能力补强计划",
    "problem": "当前短板不是工具实现，而是把评测机制升级过程表达成一个可被面试官理解的 AI 产品项目。",
    "goal": "把 AI 教练自动评测系统整理成作品集案例，能清楚说明问题发现、产品判断、方案设计、验证证据和下一步迭代。",
    "architecture_changes": [
        "在评测端 dashboard 固定展示项目叙事：问题、用户、目标、方案、证据、结果。",
        "把每次评测的可信等级、样本来源、case 证据和雷达图作为作品集材料自动沉淀。",
        "把 08 知识笔记和 11 能力雷达路径直接暴露在 dashboard，证明学习闭环不是只停留在聊天里。",
        "新增真实样本补齐路线，让每次迭代都能看到从缺样本到真实评测的进度变化。",
    ],
    "training_tasks": [
        "用 150 字写清楚：为什么旧版 100 分不可信。",
        "用一张表说明：严格评测和样例冒烟测试的区别。",
        "为 3 个 E2E case 补真实回答，并在 dashboard 中展示通过/失败证据。",
        "把本次评测升级整理成 STAR 项目故事：Situation、Task、Action、Result。",
        "补一段面试表达：我如何设计 AI 教练的可观测评测机制。",
    ],
    "evaluation_signals": [
        "dashboard 中真实回答样本数持续增加。",
        "case 结果不只显示 pass/fail，还能展示证据。",
        "最终能力图和知识笔记都有可点击路径。",
        "能用项目语言解释评测机制，而不是只展示代码和数字。",
    ],
}


@dataclass
class SampleOutput:
    text: str
    source: str
    path: str | None = None


@dataclass
class CheckResult:
    case_id: str
    node: str
    passed: bool
    score: float
    max_score: float
    source: str = "system_check"
    source_path: str | None = None
    messages: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    severity: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load_json(path: Path) -> Any:
    return json.loads(read_text(path))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cases(name: str) -> list[dict[str, Any]]:
    return load_json(CASES_DIR / name)


def all_ai_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for filename in CASE_FILES:
        cases.extend(load_cases(filename))
    return cases


def all_case_map() -> dict[str, dict[str, Any]]:
    return {str(case["case_id"]): case for case in all_ai_cases()}


def case_output(case: dict[str, Any], allow_fixtures: bool) -> SampleOutput:
    sample_path = SAMPLES_DIR / f"{case['case_id']}.txt"
    if sample_path.exists() and read_text(sample_path).strip():
        return SampleOutput(read_text(sample_path), "real_sample", str(sample_path))
    if allow_fixtures and str(case.get("sample_output", "")).strip():
        return SampleOutput(str(case.get("sample_output", "")), "embedded_sample", None)
    return SampleOutput("", "missing_sample", None)


def snippet(output: str, term: str) -> str:
    idx = output.find(term)
    if idx < 0:
        return ""
    start = max(0, idx - 24)
    end = min(len(output), idx + len(term) + 24)
    return output[start:end].replace("\n", " ")


def check_required(output: str, terms: list[str], label: str = "必须出现") -> tuple[list[str], list[str], list[str]]:
    found = [term for term in terms if term in output]
    missing = [term for term in terms if term not in output]
    evidence = [f"{label}命中 `{term}`: {snippet(output, term)}" for term in found]
    return found, missing, evidence


def check_forbidden(output: str, terms: list[str]) -> tuple[list[str], list[str]]:
    hits = [term for term in terms if term in output]
    evidence = [f"禁止词命中 `{term}`: {snippet(output, term)}" for term in hits]
    return hits, evidence


def section_exists(output: str, section: str) -> bool:
    return f"【{section}】" in output or section in output


def extract_json_blocks(output: str) -> list[Any]:
    blocks = re.findall(r"```json\s*(.*?)```", output, flags=re.S | re.I)
    if not blocks:
        blocks = re.findall(r"(\{.*?\"scores\".*?\})", output, flags=re.S)
    parsed: list[Any] = []
    for block in blocks:
        try:
            parsed.append(json.loads(block.strip()))
        except json.JSONDecodeError:
            continue
    return parsed


def find_scores(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        if isinstance(value.get("scores"), dict):
            return value["scores"]
        for item in value.values():
            found = find_scores(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_scores(item)
            if found:
                return found
    return None


def question_count(output: str) -> int:
    numbered = re.findall(r"(?m)^\s*\d+[.、)]", output)
    if numbered:
        return len(numbered)
    return output.count("？") + output.count("?")


def mojibake_count(text: str) -> int:
    return sum(text.count(token) for token in MOJIBAKE_TOKENS)


def hit_group(output: str, aliases: list[str]) -> tuple[bool, str]:
    for term in aliases:
        if term in output:
            return True, term
    return False, aliases[0] if aliases else ""


def jsonl_records(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    if not path.exists():
        return records, [f"missing file: {path}"]
    for index, line in enumerate(read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {index} is not valid JSON: {exc}")
            continue
        if isinstance(value, dict):
            records.append(value)
        else:
            errors.append(f"line {index} is not a JSON object")
    return records, errors


def active_lesson_rule_count(text: str) -> int:
    return len(re.findall(r"\*\*Rule ID:\*\*", text))


def scalar_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2).strip()
    if value is None:
        return ""
    return str(value).strip()


def module_raw_output(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("raw_output", "output", "content", "text"):
            text = scalar_text(value.get(key))
            if text:
                return text
    return scalar_text(value)


def session_raw_answer(session: dict[str, Any]) -> str:
    full_raw_answer = scalar_text(session.get("full_raw_answer"))
    if full_raw_answer:
        return full_raw_answer
    outputs = session.get("module_outputs")
    chunks: list[str] = []
    if isinstance(outputs, list):
        for item in outputs:
            text = module_raw_output(item)
            if text:
                chunks.append(text)
    elif isinstance(outputs, dict):
        called_modules = [str(item) for item in session.get("called_modules", [])]
        for key in called_modules or list(outputs.keys()):
            if key in outputs:
                text = module_raw_output(outputs[key])
                if text:
                    chunks.append(text)
    return "\n\n".join(chunks).strip()


def collect_fixture_outputs(cases: dict[str, dict[str, Any]]) -> set[str]:
    return {scalar_text(case.get("sample_output")) for case in cases.values() if scalar_text(case.get("sample_output"))}


def inspect_session_file(path: Path, cases: dict[str, dict[str, Any]], fixtures: set[str]) -> tuple[bool, bool, list[str], list[str], str | None]:
    messages: list[str] = []
    evidence: list[str] = []
    try:
        session = load_json(path)
    except Exception as exc:
        return False, False, [f"session JSON cannot be parsed: {exc}"], [], None
    if not isinstance(session, dict):
        return False, False, ["session file must contain a JSON object"], [], None

    missing_fields = [field for field in REQUIRED_SESSION_FIELDS if field not in session]
    if missing_fields:
        messages.append(f"missing required session fields: {', '.join(missing_fields)}")
    else:
        evidence.append("required session fields are present")

    eval_case_id = str(session.get("eval_case_id", "")).strip()
    if eval_case_id in cases:
        evidence.append(f"eval_case_id maps to case: {eval_case_id}")
    else:
        messages.append(f"eval_case_id is not defined in eval cases: {eval_case_id or '<empty>'}")

    if session.get("fixture_source") or session.get("from_fixture"):
        messages.append("fixture session marker is present")
    if str(session.get("session_source", "real_workflow_run")) != "real_workflow_run":
        messages.append("session_source must be real_workflow_run")

    raw_answer = session_raw_answer(session)
    if raw_answer:
        evidence.append(f"raw answer characters: {len(raw_answer)}")
    else:
        messages.append("no full_raw_answer or module raw output found")

    case_fixture = scalar_text(cases.get(eval_case_id, {}).get("sample_output"))
    if raw_answer and case_fixture and raw_answer == case_fixture:
        messages.append("raw answer exactly matches this case sample_output")
    if raw_answer and raw_answer in fixtures:
        messages.append("raw answer exactly matches an embedded case sample_output")

    structured = not missing_fields and eval_case_id in cases and bool(raw_answer)
    convertible = structured and not any("fixture" in message or "sample_output" in message for message in messages)
    return structured, convertible, messages, evidence, eval_case_id or None


def source_guard(case: dict[str, Any], node: str, each: float, allow_fixtures: bool) -> CheckResult | None:
    sample = case_output(case, allow_fixtures)
    if sample.source != "missing_sample":
        return None
    sample_path = SAMPLES_DIR / f"{case['case_id']}.txt"
    return CheckResult(
        case_id=case["case_id"],
        node=node,
        passed=False,
        score=0,
        max_score=each,
        source=sample.source,
        source_path=None,
        messages=[f"失败：缺少真实回答样本，请保存到 `{sample_path}`。"],
        evidence=[f"没有找到 `{sample_path}`，默认严格评测不会使用 case 内置 sample_output。"],
        severity="P1",
    )


def result_from_messages(
    case: dict[str, Any],
    node: str,
    each: float,
    sample: SampleOutput,
    messages: list[str],
    evidence: list[str],
    allow_fixtures: bool,
    severity: str = "P1",
) -> CheckResult:
    warnings: list[str] = []
    if sample.source == "embedded_sample":
        warnings.append("警告：这个 case 使用的是内置样例，不是真实 AI 教练回答。")
    passed = not messages
    if passed:
        messages = ["通过：所有自动断言都满足。"]
    return CheckResult(
        case_id=case["case_id"],
        node=node,
        passed=passed,
        score=each if passed else 0,
        max_score=each,
        source=sample.source,
        source_path=sample.path,
        messages=messages,
        evidence=evidence,
        warnings=warnings,
        severity=None if passed else severity,
    )


def evaluate_environment() -> list[CheckResult]:
    messages: list[str] = []
    evidence: list[str] = []
    passed = True

    plugin_json = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
    if not plugin_json.exists():
        passed = False
        messages.append("失败：缺少插件配置 plugin.json。")
    else:
        try:
            plugin = load_json(plugin_json)
            if plugin.get("name") != "aipm-coach":
                passed = False
                messages.append("失败：plugin.json 的 name 不是 aipm-coach。")
            else:
                evidence.append("命中插件配置：plugin.json name=aipm-coach。")
        except Exception as exc:
            passed = False
            messages.append(f"失败：plugin.json 不是合法 JSON：{exc}")

    missing_skills = []
    for skill in EXPECTED_SKILLS:
        skill_file = PLUGIN_ROOT / "skills" / skill / "SKILL.md"
        if skill_file.exists():
            evidence.append(f"命中 skill：{skill}")
        else:
            missing_skills.append(skill)
    if missing_skills:
        passed = False
        messages.append(f"失败：缺少 skill：{', '.join(missing_skills)}")

    backlog_path = WORKSPACE_ROOT / "coach-data" / "improvement-backlog.jsonl"
    active_lessons_path = WORKSPACE_ROOT / "coach-data" / "coach-policy" / "active-lessons.md"
    promote_script = PLUGIN_ROOT / "scripts" / "promote_coach_lessons.py"

    if backlog_path.exists():
        evidence.append(f"教练改进 backlog 存在：{backlog_path}")
    else:
        evidence.append("教练改进 backlog 尚为空；首次产生候选规则时由脚本创建。")

    if active_lessons_path.exists():
        active_text = read_text(active_lessons_path)
        required_active_terms = ["Promotion Guard", "Active Rules", "target_skill", "eval_signal"]
        missing_terms = [term for term in required_active_terms if term not in active_text]
        if missing_terms:
            passed = False
            messages.append(f"失败：active-lessons.md 缺少筛选规则字段：{', '.join(missing_terms)}")
        else:
            evidence.append(f"教练 active lessons 存在且包含筛选门槛：{active_lessons_path}")
    else:
        passed = False
        messages.append("失败：缺少教练生效规则文件：coach-data/coach-policy/active-lessons.md。")

    if not promote_script.exists():
        passed = False
        messages.append("失败：缺少教练改进规则汇总脚本 promote_coach_lessons.py。")
    else:
        try:
            py_compile.compile(str(promote_script), doraise=True)
            evidence.append("教练改进规则汇总脚本通过 py_compile。")
        except py_compile.PyCompileError as exc:
            passed = False
            messages.append(f"失败：教练改进规则汇总脚本语法检查失败：{exc.msg}")

    router_skill = PLUGIN_ROOT / "skills" / "aipm-coach-router" / "SKILL.md"
    gap_skill = PLUGIN_ROOT / "skills" / "aipm-gap-evaluator" / "SKILL.md"
    if router_skill.exists() and "active-lessons.md" in read_text(router_skill):
        evidence.append("router 已声明启动前读取 active-lessons.md。")
    else:
        passed = False
        messages.append("失败：router 未声明启动前读取 active-lessons.md。")
    if gap_skill.exists() and "coach_self_improvement" in read_text(gap_skill):
        evidence.append("gap_evaluator 已声明输出 coach_self_improvement。")
    else:
        passed = False
        messages.append("失败：gap_evaluator 未声明教练自我改进建议结构。")

    radar_script = PLUGIN_ROOT / "scripts" / "generate_capability_radar.py"
    if not radar_script.exists():
        passed = False
        messages.append("失败：缺少雷达图脚本 generate_capability_radar.py。")
    else:
        try:
            py_compile.compile(str(radar_script), doraise=True)
            evidence.append("雷达图脚本通过 py_compile。")
        except py_compile.PyCompileError as exc:
            passed = False
            messages.append(f"失败：雷达图脚本语法检查失败：{exc.msg}")

    smoke_dir = REPORTS_DIR / "radar-smoke"
    if smoke_dir.exists():
        shutil.rmtree(smoke_dir)
    if radar_script.exists():
        cmd = [
            sys.executable,
            str(radar_script),
            "--input",
            str(FIXTURES_DIR / "radar-input-1.json"),
            "--output-root",
            str(smoke_dir),
        ]
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            cmd,
            cwd=WORKSPACE_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=child_env,
        )
        if proc.returncode != 0:
            passed = False
            messages.append(f"失败：雷达图冒烟运行失败：{proc.stderr.strip() or proc.stdout.strip()}")
        else:
            for filename in ["history.jsonl", "latest.json", "index.md"]:
                path = smoke_dir / filename
                if path.exists():
                    evidence.append(f"雷达图冒烟生成：{path}")
                else:
                    passed = False
                    messages.append(f"失败：雷达图冒烟缺少 {filename}。")
            pngs = list(smoke_dir.glob("*.png"))
            if pngs and pngs[0].stat().st_size > 0:
                evidence.append(f"雷达图冒烟生成 PNG：{pngs[0]}")
            else:
                passed = False
                messages.append("失败：雷达图冒烟没有生成非空 PNG。")

    return [
        CheckResult(
            case_id="environment",
            node="00-environment",
            passed=passed,
            score=NODE_WEIGHTS["00-environment"] if passed else 0,
            max_score=NODE_WEIGHTS["00-environment"],
            messages=messages or ["通过：插件配置、skill 和雷达脚本都可用。"],
            evidence=evidence,
            severity=None if passed else "P0",
        )
    ]


def evaluate_router(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("router.json")
    each = NODE_WEIGHTS["01-router"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "01-router", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        found, missing, ev = check_required(output, case.get("expected_modules", []), "期望模块")
        evidence.extend(ev)
        if missing:
            messages.append(f"失败：缺少期望模块：{', '.join(missing)}")
        forbidden, ev = check_forbidden(output, case.get("forbidden_modules", []))
        evidence.extend(ev)
        if forbidden:
            messages.append(f"失败：出现禁止模块：{', '.join(forbidden)}")
        found_required, missing_required, ev = check_required(output, case.get("must_include", []), "必填结构")
        evidence.extend(ev)
        if missing_required:
            messages.append(f"失败：缺少必填结构或关键词：{', '.join(missing_required)}")
        if case.get("complex_case") and "aipm-recorder" not in output:
            messages.append("失败：复杂 03-06 流程没有触发 aipm-recorder。")
        results.append(result_from_messages(case, "01-router", each, sample, messages, evidence, allow_fixtures))
    return results


def evaluate_module_boundary(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("module-boundary.json")
    each = NODE_WEIGHTS["02-module-boundary"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "02-module-boundary", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        found, missing, ev = check_required(output, case.get("must_include", []), "职责关键词")
        evidence.extend(ev)
        if missing:
            messages.append(f"失败：缺少职责关键词：{', '.join(missing)}")
        forbidden, ev = check_forbidden(output, case.get("forbidden_terms", []))
        evidence.extend(ev)
        if forbidden:
            messages.append(f"失败：出现模块边界禁止词：{', '.join(forbidden)}")
        max_questions = case.get("max_questions")
        if max_questions is not None:
            count = question_count(output)
            evidence.append(f"复盘问题数量：{count}，上限：{max_questions}。")
            if count > int(max_questions):
                messages.append(f"失败：复盘问题过多：{count} > {max_questions}")
        results.append(result_from_messages(case, "02-module-boundary", each, sample, messages, evidence, allow_fixtures, "P2"))
    return results


def evaluate_workflow_gating(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("workflow-gating.json")
    each = NODE_WEIGHTS["03-workflow-gating"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "03-workflow-gating", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        found, missing, ev = check_required(output, case.get("must_include", []), "流程门禁")
        evidence.extend(ev)
        if missing:
            messages.append(f"失败：缺少流程门禁证据：{', '.join(missing)}")
        forbidden, ev = check_forbidden(output, case.get("forbidden_terms", []))
        evidence.extend(ev)
        if forbidden:
            messages.append(f"失败：出现提前跳步证据：{', '.join(forbidden)}")
        results.append(result_from_messages(case, "03-workflow-gating", each, sample, messages, evidence, allow_fixtures))
    return results


def evaluate_output_structure(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("output-structure.json")
    each = NODE_WEIGHTS["04-output-structure"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "04-output-structure", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        missing_sections = [section for section in case.get("required_sections", []) if not section_exists(output, section)]
        for section in case.get("required_sections", []):
            if section not in missing_sections:
                evidence.append(f"结构命中 `{section}`。")
        if missing_sections:
            messages.append(f"失败：缺少结构区块：{', '.join(missing_sections)}")
        found, missing_terms, ev = check_required(output, case.get("required_terms", []), "结构关键词")
        evidence.extend(ev)
        if missing_terms:
            messages.append(f"失败：缺少结构关键词：{', '.join(missing_terms)}")
        if case.get("requires_json"):
            blocks = extract_json_blocks(output)
            evidence.append(f"解析到 JSON 块数量：{len(blocks)}。")
            if not blocks:
                messages.append("失败：没有可解析 JSON 块。")
            elif case.get("requires_score_dimensions"):
                scores = find_scores(blocks)
                if not scores:
                    messages.append("失败：JSON 里没有 scores 对象。")
                else:
                    missing_dims = [dim for dim in SCORE_DIMENSIONS if dim not in scores]
                    invalid_scores = [
                        f"{dim}={value}"
                        for dim, value in scores.items()
                        if not isinstance(value, (int, float)) or value < 0 or value > 5
                    ]
                    evidence.append(f"能力维度命中：{len(SCORE_DIMENSIONS) - len(missing_dims)}/{len(SCORE_DIMENSIONS)}。")
                    if missing_dims:
                        messages.append(f"失败：缺少能力维度：{', '.join(missing_dims)}")
                    if invalid_scores:
                        messages.append(f"失败：能力分数非法：{', '.join(invalid_scores)}")
        results.append(result_from_messages(case, "04-output-structure", each, sample, messages, evidence, allow_fixtures))
    return results


def evaluate_chinese_encoding(allow_fixtures: bool) -> list[CheckResult]:
    results: list[CheckResult] = []
    files = [PLUGIN_ROOT / ".codex-plugin" / "plugin.json"]
    files.extend((PLUGIN_ROOT / "skills" / skill / "SKILL.md") for skill in EXPECTED_SKILLS)
    each = NODE_WEIGHTS["05-chinese-encoding"] / len(files)
    for path in files:
        if not path.exists():
            results.append(
                CheckResult(
                    case_id=str(path.relative_to(WORKSPACE_ROOT)),
                    node="05-chinese-encoding",
                    passed=False,
                    score=0,
                    max_score=each,
                    messages=["失败：文件缺失。"],
                    severity="P0",
                )
            )
            continue
        text = read_text(path)
        count = mojibake_count(text)
        passed = count == 0
        results.append(
            CheckResult(
                case_id=str(path.relative_to(WORKSPACE_ROOT)),
                node="05-chinese-encoding",
                passed=passed,
                score=each if passed else 0,
                max_score=each,
                messages=["通过：未检测到常见 mojibake 乱码 token。"] if passed else [f"失败：检测到疑似乱码 token {count} 个。"],
                evidence=[f"检查文件：{path}"],
                severity=None if passed else "P1",
            )
        )

    sample_text = "\n".join(case_output(case, allow_fixtures).text for case in all_ai_cases())
    sample_passed = mojibake_count(sample_text) == 0
    results.append(
        CheckResult(
            case_id="evaluation-samples",
            node="05-chinese-encoding",
            passed=sample_passed,
            score=0,
            max_score=0,
            source="system_check",
            messages=["通过：本次参与评测的样本输出未检测到常见乱码 token。"] if sample_passed else ["失败：本次样本输出含疑似乱码 token。"],
            severity=None if sample_passed else "P1",
        )
    )
    return results


def evaluate_radar_history() -> list[CheckResult]:
    case = load_cases("radar-history.json")[0]
    output_root = REPORTS_DIR / "radar-history-run"
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    evidence: list[str] = []
    radar_script = PLUGIN_ROOT / "scripts" / "generate_capability_radar.py"
    fixture_paths = sorted(FIXTURES_DIR.glob("radar-input-*.json"))
    last_result: dict[str, Any] | None = None
    run_count = 0

    for input_path in fixture_paths:
        cmd = [
            sys.executable,
            str(radar_script),
            "--input",
            str(input_path),
            "--output-root",
            str(output_root),
        ]
        child_env = os.environ.copy()
        child_env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            cmd,
            cwd=WORKSPACE_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=child_env,
        )
        if proc.returncode != 0:
            messages.append(f"失败：{input_path.name} 运行失败：{proc.stderr.strip() or proc.stdout.strip()}")
            continue
        run_count += 1
        evidence.append(f"雷达输入运行成功：{input_path.name}")
        try:
            last_result = json.loads(proc.stdout)
        except json.JSONDecodeError:
            messages.append(f"失败：{input_path.name} 没有返回 JSON。")

    history_path = output_root / "history.jsonl"
    latest_path = output_root / "latest.json"
    index_path = output_root / "index.md"
    pngs = sorted(output_root.glob("*.png"))

    if run_count != case["expected_runs"]:
        messages.append(f"失败：期望运行 {case['expected_runs']} 次，实际 {run_count} 次。")
    for path in [history_path, latest_path, index_path]:
        if path.exists():
            evidence.append(f"落地产物存在：{path}")
        else:
            messages.append(f"失败：缺少落地产物 {path.name}。")
    if len(pngs) == case["expected_runs"] and all(path.stat().st_size > 0 for path in pngs):
        evidence.append(f"生成非空雷达图 PNG：{len(pngs)} 张。")
    else:
        messages.append(f"失败：期望 {case['expected_runs']} 张非空 PNG，实际 {len(pngs)} 张。")

    if history_path.exists():
        history = [json.loads(line) for line in read_text(history_path).splitlines() if line.strip()]
        if len(history) != case["expected_history_count"]:
            messages.append(f"失败：history_count 期望 {case['expected_history_count']}，实际 {len(history)}。")
        else:
            evidence.append(f"history.jsonl 完整历史条数：{len(history)}。")
        for record in history:
            scores = record.get("scores", {})
            total = sum(int(scores.get(dim, 0)) for dim in SCORE_DIMENSIONS)
            if record.get("total_score") != total:
                messages.append(f"失败：{record.get('timestamp')} total_score 错误。")
        if case.get("expects_clamp") and history and history[-1].get("scores", {}).get("需求分析能力") == 5:
            evidence.append("越界分数已被 clamp 到 5。")
        elif case.get("expects_clamp"):
            messages.append("失败：越界分数没有被 clamp 到 5。")

    if latest_path.exists():
        latest = load_json(latest_path)
        latest_count = len(latest.get("items", []))
        if latest_count == case["expected_latest_count"]:
            evidence.append(f"latest.json 最近窗口条数正确：{latest_count}。")
        else:
            messages.append(f"失败：latest_count 期望 {case['expected_latest_count']}，实际 {latest_count}。")

    if last_result and last_result.get("comparison", {}).get("has_previous"):
        evidence.append("最后一次雷达运行包含历史对比。")
    elif last_result:
        messages.append("失败：最后一次雷达运行没有历史对比。")

    write_capability_radar_report(output_root)
    passed = not messages
    return [
        CheckResult(
            case_id=case["case_id"],
            node="06-radar-history",
            passed=passed,
            score=NODE_WEIGHTS["06-radar-history"] if passed else 0,
            max_score=NODE_WEIGHTS["06-radar-history"],
            source="system_check",
            messages=messages or ["通过：雷达图、历史记录、latest 窗口和横向对比均已生成。"],
            evidence=evidence,
            severity=None if passed else "P0",
        )
    ]


def write_capability_radar_report(output_root: Path) -> Path:
    latest_path = output_root / "latest.json"
    report_path = REPORTS_DIR / "capability-radar-report.md"
    lines = ["# AIPM Capability Radar Report", ""]
    if not latest_path.exists():
        lines.append("No latest.json was generated.")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return report_path

    latest = load_json(latest_path)
    items = latest.get("items", [])
    if not items:
        lines.append("No radar records found.")
    else:
        last = items[-1]
        image = Path(last.get("radar_image", ""))
        if image.exists():
            rel_image = image.relative_to(report_path.parent).as_posix() if image.is_relative_to(report_path.parent) else image.as_posix()
            lines.append(f"![Latest capability radar]({rel_image})")
            lines.append("")
        lines.append(f"- Latest timestamp: {last.get('timestamp')}")
        lines.append(f"- Latest total score: {last.get('total_score')}/50")
        lines.append(f"- Latest radar image: `{last.get('radar_image')}`")
        lines.append(f"- History file: `{output_root / 'history.jsonl'}`")
        lines.append(f"- Latest window: `{latest_path}`")
        lines.append(f"- Index file: `{output_root / 'index.md'}`")
        lines.append("")
        lines.append("## Recent Comparison")
        lines.append("")
        lines.append("| Time | Total | Strengths | Weaknesses |")
        lines.append("|---|---:|---|---|")
        for record in items:
            strengths = ", ".join(record.get("strengths") or [])
            weaknesses = ", ".join(record.get("weaknesses") or [])
            lines.append(f"| {record.get('timestamp')} | {record.get('total_score')}/50 | {strengths} | {weaknesses} |")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def evaluate_e2e(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("e2e.json")
    each = NODE_WEIGHTS["07-e2e"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "07-e2e", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        found, missing_steps, ev = check_required(output, case.get("expected_steps", []), "E2E 节点")
        evidence.extend(ev)
        if missing_steps:
            messages.append(f"失败：缺少 E2E 节点：{', '.join(missing_steps)}")
        blocks = extract_json_blocks(output)
        scores = find_scores(blocks) if blocks else None
        if "能力雷达图数据" in output:
            evidence.append("命中 `能力雷达图数据`。")
        if "能力雷达图数据" not in output or (blocks and scores is None):
            messages.append("失败：E2E 输出没有可用能力雷达图数据。")
        results.append(result_from_messages(case, "07-e2e", each, sample, messages, evidence, allow_fixtures))
    return results


def evaluate_real_sessions() -> list[CheckResult]:
    cases = all_case_map()
    fixtures = collect_fixture_outputs(cases)
    session_files = sorted(path for path in SESSION_RUNS_DIR.glob("*.json") if path.is_file()) if SESSION_RUNS_DIR.exists() else []
    messages: list[str] = []
    evidence: list[str] = []
    structured_count = 0
    convertible_count = 0
    convertible_case_ids: set[str] = set()

    if not SESSION_RUNS_DIR.exists():
        messages.append(f"缺少真实 session 目录：{SESSION_RUNS_DIR}")
    elif not session_files:
        messages.append(f"尚未采集真实 session JSON：{SESSION_RUNS_DIR}")
        evidence.append("目录存在，但目前没有可检查的 *.json session。")

    for path in session_files:
        structured, convertible, session_messages, session_evidence, case_id = inspect_session_file(path, cases, fixtures)
        if structured:
            structured_count += 1
        if convertible:
            convertible_count += 1
            if case_id:
                convertible_case_ids.add(case_id)
        if session_messages:
            messages.append(f"{path.name}: {'; '.join(session_messages)}")
        evidence.append(f"{path.name}: structured={structured}, convertible={convertible}")
        evidence.extend(f"{path.name}: {item}" for item in session_evidence[:3])

    if session_files and convertible_count == 0:
        messages.append("存在 session 文件，但没有任何一条能安全转换为 samples/<case_id>.txt。")

    sample_targets = [str(SAMPLES_DIR / f"{case_id}.txt") for case_id in sorted(convertible_case_ids)]
    if sample_targets:
        evidence.append("可转换样本目标：" + ", ".join(sample_targets[:5]))

    passed = bool(session_files) and convertible_count > 0 and not messages
    return [
        CheckResult(
            case_id="real_session_collection",
            node="08-real-session",
            passed=passed,
            score=NODE_WEIGHTS["08-real-session"] if passed else 0,
            max_score=NODE_WEIGHTS["08-real-session"],
            source="system_check",
            messages=messages or ["通过：真实 session 存在、结构完整，并且可转换为严格评测样本。"],
            evidence=evidence,
            severity=None if passed else "P2",
            metadata={
                "real_session_count": len(session_files),
                "structured_session_count": structured_count,
                "convertible_sample_count": convertible_count,
                "convertible_case_ids": sorted(convertible_case_ids),
            },
        )
    ]


def evaluate_portfolio_explainer(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("portfolio-explainer.json")
    each = NODE_WEIGHTS["09-portfolio-explainer"] / len(cases)
    results: list[CheckResult] = []
    for case in cases:
        guard = source_guard(case, "09-portfolio-explainer", each, allow_fixtures)
        if guard:
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        hits = 0
        total = 0
        for signal, aliases in case.get("signal_groups", PORTFOLIO_SIGNAL_GROUPS).items():
            total += 1
            hit, term = hit_group(output, aliases)
            if hit:
                hits += 1
                evidence.append(f"作品集讲解信号 `{signal}` 命中 `{term}`: {snippet(output, term)}")
            else:
                messages.append(f"失败：缺少作品集讲解信号 `{signal}`，可接受表达：{', '.join(aliases)}")
        forbidden, ev = check_forbidden(output, case.get("forbidden_terms", []))
        evidence.extend(ev)
        if forbidden:
            messages.append(f"失败：出现模块边界禁止词：{', '.join(forbidden)}")
        results.append(
            CheckResult(
                case_id=case["case_id"],
                node="09-portfolio-explainer",
                passed=not messages,
                score=each if not messages else each * (hits / total if total else 0),
                max_score=each,
                source=sample.source,
                source_path=sample.path,
                messages=messages or ["通过：作品集讲解覆盖了核心表达信号。"],
                evidence=evidence,
                warnings=["警告：本 case 使用内置样例，只能作为冒烟测试。"] if sample.source == "embedded_sample" else [],
                severity=None if not messages else "P2",
                metadata={"signal_hits": hits, "signal_total": total},
            )
        )
    return results


def evaluate_self_iteration(allow_fixtures: bool) -> list[CheckResult]:
    cases = load_cases("self-iteration.json")
    each = NODE_WEIGHTS["10-self-iteration"] / 3
    results: list[CheckResult] = []

    backlog_path = (
        FIXTURES_DIR / "self-iteration-backlog.jsonl"
        if allow_fixtures
        else IMPROVEMENT_BACKLOG_PATH
    )
    active_lessons_path = (
        FIXTURES_DIR / "self-iteration-active-lessons.md"
        if allow_fixtures
        else ACTIVE_LESSONS_PATH
    )

    backlog_records, backlog_errors = jsonl_records(backlog_path)
    backlog_messages = list(backlog_errors)
    backlog_evidence: list[str] = []
    valid_backlog = []
    for item in backlog_records:
        missing = [field for field in ["weakness", "evidence", "coach_improvement", "target_skill", "expected_next_behavior", "eval_signal"] if not item.get(field)]
        if not missing:
            valid_backlog.append(item)
    if valid_backlog:
        backlog_evidence.append(f"有效短板候选记录数：{len(valid_backlog)}")
        backlog_evidence.append(f"最近短板：{str(valid_backlog[-1].get('weakness'))[:120]}")
    else:
        backlog_messages.append("improvement-backlog 未记录具备 weakness/evidence/target_skill/expected_next_behavior/eval_signal 的有效短板。")
    results.append(
        CheckResult(
            case_id="self_iteration_backlog",
            node="10-self-iteration",
            passed=not backlog_messages,
            score=each if not backlog_messages else 0,
            max_score=each,
            source="system_check",
            messages=backlog_messages or ["通过：improvement-backlog 已记录可执行短板。"],
            evidence=backlog_evidence,
            severity=None if not backlog_messages else "P2",
            metadata={"backlog_valid_items": len(valid_backlog)},
        )
    )

    active_messages: list[str] = []
    active_evidence: list[str] = []
    active_text = ""
    if active_lessons_path.exists():
        active_text = read_text(active_lessons_path)
        rule_count = active_lesson_rule_count(active_text)
        required_terms = ["Promotion Guard", "Active Rules", "Weakness", "Coach behavior", "Next behavior", "Evaluation signal"]
        missing_terms = [term for term in required_terms if term not in active_text]
        if rule_count:
            active_evidence.append(f"active-lessons 生效规则数量：{rule_count}")
        else:
            active_messages.append("active-lessons 没有任何 Rule ID。")
        if missing_terms:
            active_messages.append(f"active-lessons 缺少规则字段：{', '.join(missing_terms)}")
    else:
        rule_count = 0
        active_messages.append(f"缺少 active-lessons 文件：{active_lessons_path}")
    results.append(
        CheckResult(
            case_id="self_iteration_active_lessons",
            node="10-self-iteration",
            passed=not active_messages,
            score=each if not active_messages else 0,
            max_score=each,
            source="system_check",
            messages=active_messages or ["通过：active-lessons 已吸收可执行规则。"],
            evidence=active_evidence,
            severity=None if not active_messages else "P2",
            metadata={"active_lesson_rule_count": rule_count},
        )
    )

    for case in cases:
        guard = source_guard(case, "10-self-iteration", each, allow_fixtures)
        if guard:
            guard.max_score = each
            results.append(guard)
            continue
        sample = case_output(case, allow_fixtures)
        output = sample.text
        messages: list[str] = []
        evidence: list[str] = []
        hits = 0
        total = 0
        behavior_groups = case.get("behavior_groups", SELF_ITERATION_BEHAVIOR_GROUPS)
        for signal, aliases in behavior_groups.items():
            total += 1
            hit, term = hit_group(output, aliases)
            if hit:
                hits += 1
                evidence.append(f"上轮要求补强行为 `{signal}` 命中 `{term}`: {snippet(output, term)}")
            else:
                messages.append(f"失败：下一轮回答未覆盖 `{signal}`，可接受表达：{', '.join(aliases)}")
        if "aipm-portfolio-explainer" not in active_text:
            messages.append("active-lessons 当前未包含 aipm-portfolio-explainer 规则，无法证明下一轮行为来自生效规则。")
        results.append(
            CheckResult(
                case_id=case["case_id"],
                node="10-self-iteration",
                passed=not messages,
                score=each if not messages else each * (hits / total if total else 0),
                max_score=each,
                source=sample.source,
                source_path=sample.path,
                messages=messages or ["通过：下一轮回答覆盖了上轮要求补强的行为。"],
                evidence=evidence,
                warnings=["警告：本 case 使用内置样例，只能作为冒烟测试。"] if sample.source == "embedded_sample" else [],
                severity=None if not messages else "P2",
                metadata={"behavior_hits": hits, "behavior_total": total, "covered_previous_weakness": hits == total and total > 0},
            )
        )
    return results


def summarize(results: list[CheckResult], allow_fixtures: bool) -> dict[str, Any]:
    node_totals: dict[str, dict[str, float | int]] = {}
    for result in results:
        item = node_totals.setdefault(result.node, {"score": 0.0, "max_score": 0.0, "passed": 0, "total": 0})
        item["score"] = float(item["score"]) + result.score
        item["max_score"] = float(item["max_score"]) + result.max_score
        item["passed"] = int(item["passed"]) + (1 if result.passed else 0)
        item["total"] = int(item["total"]) + 1

    total_score = round(sum(result.score for result in results), 2)
    max_score = round(sum(result.max_score for result in results), 2)
    normalized = round((total_score / max_score) * 100, 2) if max_score else 0.0

    ai_results = [result for result in results if result.source in {"real_sample", "embedded_sample", "missing_sample"}]
    real_results = [result for result in ai_results if result.source == "real_sample"]
    embedded_results = [result for result in ai_results if result.source == "embedded_sample"]
    missing_results = [result for result in ai_results if result.source == "missing_sample"]

    real_score = None
    if real_results:
        real_raw = sum(result.score for result in real_results)
        real_max = sum(result.max_score for result in real_results)
        real_score = round((real_raw / real_max) * 100, 2) if real_max else None

    defects = [
        {
            "severity": result.severity,
            "node": result.node,
            "case_id": result.case_id,
            "source": result.source,
            "messages": result.messages,
            "evidence": result.evidence,
        }
        for result in results
        if result.severity
    ]

    p0_count = sum(1 for defect in defects if defect["severity"] == "P0")
    p1_count = sum(1 for defect in defects if defect["severity"] == "P1")
    p2_count = sum(1 for defect in defects if defect["severity"] == "P2")
    one_vote_veto = p0_count > 0

    if not allow_fixtures and not real_results:
        trust_level = "NOT_REAL_RUN_NO_REAL_SAMPLES"
        level = "不是一次真实评测：缺少真实 AI 教练回答样本。"
    elif allow_fixtures and not real_results and embedded_results:
        trust_level = "FIXTURE_SMOKE_ONLY"
        level = "样例冒烟测试通过时，只能说明评测脚本能跑通，不能说明 AI 教练真实表现。"
    elif missing_results:
        trust_level = "PARTIAL_REAL_EVAL_MISSING_SAMPLES"
        level = "部分真实评测：仍有 case 缺少真实回答样本。"
    elif embedded_results:
        trust_level = "PARTIAL_REAL_EVAL_WITH_FIXTURES"
        level = "部分真实评测：混用了内置样例，不能作为正式 100 分。"
    elif normalized >= 90 and not one_vote_veto and p1_count == 0:
        trust_level = "REAL_EVAL_HIGH_CONFIDENCE"
        level = "真实评测高可信：可进入真实用户试运行。"
    elif normalized >= 85 and not one_vote_veto:
        trust_level = "REAL_EVAL_TRIAL_READY"
        level = "真实评测基本可信：可小范围试用，但需修复缺陷。"
    else:
        trust_level = "REAL_EVAL_NEEDS_FIXES"
        level = "真实评测未达标：需要继续修复。"

    mechanism_usable = node_totals.get("00-environment", {}).get("passed") == 1 and node_totals.get("06-radar-history", {}).get("passed") == 1
    real_eval_complete = bool(real_results) and not embedded_results and not missing_results

    session_meta: dict[str, Any] = {}
    for result in results:
        if result.case_id == "real_session_collection":
            session_meta = result.metadata
            break

    portfolio_results = [result for result in results if result.node == "09-portfolio-explainer"]
    portfolio_hits = sum(int(result.metadata.get("signal_hits", 0)) for result in portfolio_results)
    portfolio_total = sum(int(result.metadata.get("signal_total", 0)) for result in portfolio_results)
    portfolio_hit_rate = round((portfolio_hits / portfolio_total) * 100, 1) if portfolio_total else 0.0

    active_lesson_rule_count_value = 0
    previous_weakness_covered = False
    behavior_hits = 0
    behavior_total = 0
    for result in results:
        if result.case_id == "self_iteration_active_lessons":
            active_lesson_rule_count_value = int(result.metadata.get("active_lesson_rule_count", 0))
        if result.case_id == "self_iteration_next_answer_001":
            behavior_hits = int(result.metadata.get("behavior_hits", 0))
            behavior_total = int(result.metadata.get("behavior_total", 0))
            previous_weakness_covered = bool(result.metadata.get("covered_previous_weakness"))

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "mode": "fixture_smoke" if allow_fixtures else "strict_real_samples",
        "score": normalized,
        "real_sample_score": real_score,
        "raw_score": total_score,
        "max_score": max_score,
        "trust_level": trust_level,
        "level": level,
        "sample_summary": {
            "ai_case_count": len(ai_results),
            "real_samples": len(real_results),
            "embedded_samples": len(embedded_results),
            "missing_samples": len(missing_results),
            "system_checks": len([result for result in results if result.source == "system_check"]),
        },
        "node_totals": node_totals,
        "defects": defects,
        "defect_counts": {"P0": p0_count, "P1": p1_count, "P2": p2_count, "P3": sum(1 for d in defects if d["severity"] == "P3")},
        "one_vote_veto": one_vote_veto,
        "acceptance": {
            "mechanism_usable": mechanism_usable,
            "real_eval_complete": real_eval_complete,
            "trial_ready": real_eval_complete and normalized >= 85 and not one_vote_veto and p1_count == 0,
            "daily_coach_ready": real_eval_complete and normalized >= 90 and not one_vote_veto and p1_count == 0,
        },
        "observability": {
            "real_session_count": int(session_meta.get("real_session_count", 0)),
            "structured_session_count": int(session_meta.get("structured_session_count", 0)),
            "convertible_sample_count": int(session_meta.get("convertible_sample_count", 0)),
            "convertible_case_ids": session_meta.get("convertible_case_ids", []),
            "portfolio_explainer_hit_rate": portfolio_hit_rate,
            "portfolio_signal_hits": portfolio_hits,
            "portfolio_signal_total": portfolio_total,
            "self_iteration_rule_count": active_lesson_rule_count_value,
            "previous_weakness_covered": previous_weakness_covered,
            "self_iteration_behavior_hits": behavior_hits,
            "self_iteration_behavior_total": behavior_total,
        },
    "reports": {
            "markdown": str(REPORTS_DIR / "latest-report.md"),
            "json": str(REPORTS_DIR / "latest-report.json"),
            "mode_markdown": str(REPORTS_DIR / ("fixture-smoke-report.md" if allow_fixtures else "strict-real-samples-report.md")),
            "mode_json": str(REPORTS_DIR / ("fixture-smoke-report.json" if allow_fixtures else "strict-real-samples-report.json")),
            "capability_radar_report": str(REPORTS_DIR / "capability-radar-report.md"),
        },
        "results": [result.__dict__ for result in results],
    }


def write_markdown_report(path: Path, summary: dict[str, Any]) -> None:
    sample = summary["sample_summary"]
    obs = summary["observability"]
    lines = [
        "# AIPM Coach Evaluation Report",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Mode: `{summary['mode']}`",
        f"- Trust level: `{summary['trust_level']}`",
        f"- Score: {summary['score']}/100",
        f"- Real-sample score: {summary['real_sample_score'] if summary['real_sample_score'] is not None else 'N/A'}",
        f"- Conclusion: {summary['level']}",
        f"- One-vote veto: {summary['one_vote_veto']}",
        "",
        "## Sample Source Summary",
        "",
        f"- AI answer test cases: {sample['ai_case_count']}",
        f"- Real AI answers: {sample['real_samples']}",
        f"- Embedded fixture samples: {sample['embedded_samples']}",
        f"- Missing samples: {sample['missing_samples']}",
        f"- System checks: {sample['system_checks']}",
        "",
        "## Architecture Observability",
        "",
        f"- Real sessions: {obs['real_session_count']}",
        f"- Structured sessions: {obs['structured_session_count']}",
        f"- Convertible eval samples: {obs['convertible_sample_count']}",
        f"- Portfolio explainer hit rate: {obs['portfolio_explainer_hit_rate']}% ({obs['portfolio_signal_hits']}/{obs['portfolio_signal_total']})",
        f"- Self-iteration active rules: {obs['self_iteration_rule_count']}",
        f"- Previous weakness covered this round: {obs['previous_weakness_covered']} ({obs['self_iteration_behavior_hits']}/{obs['self_iteration_behavior_total']})",
        "",
    ]
    if summary["trust_level"] == "NOT_REAL_RUN_NO_REAL_SAMPLES":
        lines.extend(
            [
                "> This is not a real evaluation because no real AI coach answers were found in `samples/`.",
                "> Default strict mode does not use case `sample_output` as if it were real output.",
                "",
            ]
        )
    if summary["trust_level"] == "FIXTURE_SMOKE_ONLY":
        lines.extend(
            [
                "> This is a fixture smoke test. It only proves the evaluator can run against built-in examples.",
                "> It does not prove the real AI coach scored 100.",
                "",
            ]
        )

    lines.extend(["## Node Results", "", "| Node | Passed | Score |", "|---|---:|---:|"])
    for node in NODE_WEIGHTS:
        item = summary["node_totals"].get(node, {"passed": 0, "total": 0, "score": 0, "max_score": 0})
        lines.append(f"| {node} | {item['passed']}/{item['total']} | {float(item['score']):.2f}/{float(item['max_score']):.2f} |")

    lines.extend(
        [
            "",
            "## Acceptance",
            "",
            f"- Mechanism usable: {summary['acceptance']['mechanism_usable']}",
            f"- Real evaluation complete: {summary['acceptance']['real_eval_complete']}",
            f"- Trial ready: {summary['acceptance']['trial_ready']}",
            f"- Daily coach ready: {summary['acceptance']['daily_coach_ready']}",
            "",
            "## Case Results",
            "",
            "| Case | Node | Source | Result | Messages | Evidence |",
            "|---|---|---|---|---|---|",
        ]
    )
    for result in summary["results"]:
        source = SOURCE_LABELS.get(result["source"], result["source"])
        status = "PASS" if result["passed"] else "FAIL"
        warnings = " ".join(result.get("warnings") or [])
        messages = " ".join(result.get("messages") or [])
        evidence = " ".join((result.get("evidence") or [])[:3])
        combined = f"{messages} {warnings}".strip()
        lines.append(f"| `{result['case_id']}` | `{result['node']}` | {source} | {status} | {combined} | {evidence} |")

    lines.extend(["", "## Defects", ""])
    if not summary["defects"]:
        lines.append("No defects detected.")
    else:
        for defect in summary["defects"]:
            messages = "; ".join(defect["messages"])
            lines.append(f"- {defect['severity']} `{defect['node']}` `{defect['case_id']}` [{SOURCE_LABELS.get(defect['source'], defect['source'])}]: {messages}")

    lines.extend(
        [
            "",
            "## Capability Radar",
            "",
            f"- Radar report: `{summary['reports']['capability_radar_report']}`",
            f"- Radar output directory: `{REPORTS_DIR / 'radar-history-run'}`",
            "",
            "## How To Add Real Samples",
            "",
            "Save the real AI coach answer exactly as returned:",
            "",
            "```text",
            "tests/aipm-coach-eval/samples/<case_id>.txt",
            "```",
            "",
            "Then run strict mode again:",
            "",
            "```powershell",
            "python tests\\aipm-coach-eval\\run_eval.py",
            "```",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_run_history(summary: dict[str, Any]) -> list[dict[str, Any]]:
    history_path = REPORTS_DIR / "run-history.jsonl"
    item = {
        "generated_at": summary["generated_at"],
        "mode": summary["mode"],
        "trust_level": summary["trust_level"],
        "score": summary["score"],
        "real_samples": summary["sample_summary"]["real_samples"],
        "embedded_samples": summary["sample_summary"]["embedded_samples"],
        "missing_samples": summary["sample_summary"]["missing_samples"],
        "real_sessions": summary["observability"]["real_session_count"],
        "convertible_samples": summary["observability"]["convertible_sample_count"],
        "portfolio_hit_rate": summary["observability"]["portfolio_explainer_hit_rate"],
        "self_iteration_rules": summary["observability"]["self_iteration_rule_count"],
        "previous_weakness_covered": summary["observability"]["previous_weakness_covered"],
        "mechanism_usable": summary["acceptance"]["mechanism_usable"],
        "real_eval_complete": summary["acceptance"]["real_eval_complete"],
    }
    history_path.parent.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    rows = [json.loads(line) for line in read_text(history_path).splitlines() if line.strip()]
    return rows[-20:]


def html_path_link(path_text: str) -> str:
    path = Path(path_text)
    label = html.escape(str(path))
    if path.exists():
        return f'<a href="{path.as_posix()}">{label}</a>'
    return f"<code>{label}</code>"


def mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def trust_label(trust_level: str) -> str:
    return TRUST_LABELS.get(trust_level, trust_level)


def workflow_stage_rows(summary: dict[str, Any]) -> list[str]:
    results = summary["results"]
    rows: list[str] = []
    for stage in WORKFLOW_STAGES:
        selected = []
        if "nodes" in stage:
            selected.extend(result for result in results if result["node"] in stage["nodes"])
        if "case_ids" in stage:
            ids = set(stage["case_ids"])
            selected.extend(result for result in results if result["case_id"] in ids)

        # Preserve order while removing duplicates.
        deduped = []
        seen = set()
        for result in selected:
            key = (result["case_id"], result["node"])
            if key not in seen:
                deduped.append(result)
                seen.add(key)
        selected = deduped

        total = len(selected)
        passed = sum(1 for result in selected if result["passed"])
        real = sum(1 for result in selected if result["source"] == "real_sample")
        embedded = sum(1 for result in selected if result["source"] == "embedded_sample")
        missing = sum(1 for result in selected if result["source"] == "missing_sample")
        success = round((passed / total) * 100, 1) if total else 0
        status_class = "pass" if total and passed == total and missing == 0 else ("warn" if total and passed else "fail")
        if not total:
            status = "未覆盖"
        elif missing:
            status = "缺真实样本"
        elif embedded and not real:
            status = "样例通过"
        elif passed == total:
            status = "真实通过" if real else "通过"
        else:
            status = "存在失败"

        evidence_items = []
        for result in selected[:4]:
            first_msg = (result.get("messages") or [""])[0]
            evidence_items.append(f"{result['case_id']}：{first_msg}")
        evidence = "<br>".join(html.escape(item) for item in evidence_items) or "暂无证据"

        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(stage['name'])}</strong><br><span class=\"muted\">{html.escape(', '.join(stage['skills']))}</span></td>"
            f"<td>{html.escape(stage['description'])}</td>"
            f"<td><span class=\"case-state {status_class}\">{html.escape(status)}</span></td>"
            f"<td>{passed}/{total}</td>"
            f"<td>{success}%</td>"
            f"<td>真实 {real} / 内置 {embedded} / 缺失 {missing}</td>"
            f"<td>{evidence}</td>"
            "</tr>"
        )
    return rows


def embedded_sample_blocks(summary: dict[str, Any]) -> str:
    case_map = {case["case_id"]: case for case in all_ai_cases()}
    embedded = [result for result in summary["results"] if result["source"] == "embedded_sample"]
    if not embedded:
        return "<p class=\"muted\">本次没有使用内置样例。</p>"
    blocks = []
    for result in embedded:
        case = case_map.get(result["case_id"], {})
        user_input = html.escape(str(case.get("user_input", "系统检查或无用户输入")))
        sample_output = html.escape(str(case.get("sample_output", "")))
        stage = html.escape(str(case.get("stage", result["node"])))
        blocks.append(
            "<details class=\"sample-detail\">"
            f"<summary><code>{html.escape(result['case_id'])}</code> <span class=\"muted\">{stage}</span></summary>"
            "<div class=\"sample-grid\">"
            f"<div><h3>用户输入</h3><pre>{user_input}</pre></div>"
            f"<div><h3>内置样例输出</h3><pre>{sample_output}</pre></div>"
            "</div>"
            "</details>"
        )
    return "\n".join(blocks)


def write_html_dashboard(path: Path, summary: dict[str, Any], history: list[dict[str, Any]]) -> None:
    sample = summary["sample_summary"]
    obs = summary["observability"]
    rows = []
    for result in summary["results"]:
        source = SOURCE_LABELS.get(result["source"], result["source"])
        status = "PASS" if result["passed"] else "FAIL"
        status_class = "pass" if result["passed"] else "fail"
        source_class = "warn" if result["source"] == "embedded_sample" else ("fail" if result["source"] == "missing_sample" else "pass")
        messages = "<br>".join(html.escape(x) for x in (result.get("messages") or []))
        evidence = "<br>".join(html.escape(x) for x in (result.get("evidence") or [])[:5])
        warnings = "<br>".join(html.escape(x) for x in (result.get("warnings") or []))
        warning_html = f'<br><span class="warn">{warnings}</span>' if warnings else ""
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(result['case_id'])}</code></td>"
            f"<td>{html.escape(result['node'])}</td>"
            f'<td><span class="case-state {source_class}">{html.escape(source)}</span></td>'
            f'<td><span class="case-state {status_class}">{status}</span></td>'
            f"<td>{messages}{warning_html}</td>"
            f"<td>{evidence}</td>"
            "</tr>"
        )

    node_rows = []
    for node in NODE_WEIGHTS:
        item = summary["node_totals"].get(node, {"passed": 0, "total": 0, "score": 0, "max_score": 0})
        node_rows.append(
            "<tr>"
            f"<td>{html.escape(node)}</td>"
            f"<td>{item['passed']}/{item['total']}</td>"
            f"<td>{float(item['score']):.2f}/{float(item['max_score']):.2f}</td>"
            "</tr>"
        )

    workflow_rows = workflow_stage_rows(summary)
    embedded_blocks = embedded_sample_blocks(summary)

    history_rows = []
    for item in reversed(history):
        history_rows.append(
            "<tr>"
            f"<td>{html.escape(item['generated_at'])}</td>"
            f"<td>{html.escape(mode_label(item['mode']))}</td>"
            f"<td>{html.escape(trust_label(item['trust_level']))}</td>"
            f"<td>{item['score']}</td>"
            f"<td>{item['real_samples']}</td>"
            f"<td>{item['embedded_samples']}</td>"
            f"<td>{item['missing_samples']}</td>"
            "</tr>"
        )

    plan_sections = "".join(
        f"<li>{html.escape(item)}</li>" for item in PORTFOLIO_EXPRESSION_PLAN["architecture_changes"]
    )
    training_tasks = "".join(
        f"<li>{html.escape(item)}</li>" for item in PORTFOLIO_EXPRESSION_PLAN["training_tasks"]
    )
    signals = "".join(
        f"<li>{html.escape(item)}</li>" for item in PORTFOLIO_EXPRESSION_PLAN["evaluation_signals"]
    )

    radar_report = summary["reports"]["capability_radar_report"]
    mode_report = summary["reports"]["mode_markdown"]
    knowledge_note = WORKSPACE_ROOT / "coach-data" / "knowledge-notes" / "2026-05-11-07-15-ai-coach-eval-credibility-upgrade.md"
    knowledge_index = WORKSPACE_ROOT / "coach-data" / "knowledge-index.md"
    capability_report = WORKSPACE_ROOT / "coach-data" / "capability-radar" / "report.md"
    capability_png = WORKSPACE_ROOT / "coach-data" / "capability-radar" / "2026-05-11-07-15-capability-radar.png"

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIPM Coach Evaluation Dashboard</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #17202a;
      --muted: #667085;
      --line: #d9dee7;
      --accent: #2563eb;
      --ok: #047857;
      --bad: #b42318;
      --warn: #b54708;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font: 14px/1.5 "Microsoft YaHei", "Segoe UI", Arial, sans-serif; color: var(--text); background: var(--bg); }}
    header {{ padding: 24px 32px; background: #111827; color: white; }}
    header h1 {{ margin: 0 0 6px; font-size: 24px; }}
    header p {{ margin: 0; color: #cbd5e1; }}
    main {{ padding: 24px 32px 48px; max-width: 1440px; margin: 0 auto; }}
    section {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 18px; margin-bottom: 18px; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    h3 {{ margin: 14px 0 8px; font-size: 15px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; }}
    .metric {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fbfcfe; min-height: 76px; }}
    .metric strong {{ display: block; font-size: 22px; margin-top: 4px; }}
    .metric-link {{ display: block; color: var(--text); text-decoration: none; }}
    .metric-link:hover {{ border-color: var(--accent); box-shadow: 0 0 0 2px rgba(37, 99, 235, .12); text-decoration: none; }}
    .muted {{ color: var(--muted); }}
    .trust {{ display: inline-block; padding: 4px 8px; border-radius: 6px; background: #eff6ff; color: #1d4ed8; font-weight: 600; }}
    .pass {{ color: var(--ok); font-weight: 700; }}
    .fail {{ color: var(--bad); font-weight: 700; }}
    .warn {{ color: var(--warn); font-weight: 600; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; vertical-align: top; text-align: left; word-break: break-word; }}
    th {{ background: #f8fafc; color: #344054; }}
    code {{ background: #f2f4f7; padding: 1px 4px; border-radius: 4px; }}
    pre {{ white-space: pre-wrap; word-break: break-word; background: #f8fafc; border: 1px solid var(--line); border-radius: 6px; padding: 10px; margin: 6px 0 12px; max-height: 360px; overflow: auto; }}
    details.sample-detail {{ border: 1px solid var(--line); border-radius: 8px; margin: 10px 0; background: #fbfcfe; }}
    details.sample-detail summary {{ cursor: pointer; padding: 10px 12px; font-weight: 700; }}
    details.sample-detail[open] summary {{ border-bottom: 1px solid var(--line); }}
    .sample-grid {{ display: grid; grid-template-columns: minmax(220px, .75fr) minmax(360px, 1.25fr); gap: 14px; padding: 12px; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .radar {{ max-width: 520px; width: 100%; border: 1px solid var(--line); border-radius: 8px; background: white; }}
    .actions {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 14px; }}
    .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 34px; padding: 7px 12px; border-radius: 6px; border: 1px solid var(--line); background: white; color: var(--text); font-weight: 600; cursor: pointer; }}
    .button.primary {{ background: var(--accent); border-color: var(--accent); color: white; }}
    .case-state {{ display: inline-block; min-width: 72px; padding: 2px 6px; border-radius: 999px; text-align: center; font-size: 12px; font-weight: 700; }}
    .case-state.pass {{ background: #ecfdf3; color: var(--ok); }}
    .case-state.fail {{ background: #fef3f2; color: var(--bad); }}
    .case-state.warn {{ background: #fffaeb; color: var(--warn); }}
    ul {{ margin-top: 8px; padding-left: 20px; }}
    @media (max-width: 900px) {{ .grid, .two {{ grid-template-columns: 1fr; }} main {{ padding: 16px; }} }}
  </style>
</head>
<body>
<header>
  <h1>AIPM Coach 自动评测 Dashboard</h1>
  <p>每次运行 <code>run_eval.py</code> 后会写入最新状态。本页不自动刷新，避免闪烁；需要查看新结果时点击刷新。</p>
</header>
<main>
  <section>
    <h2>本次评测状态</h2>
    <div class="grid">
      <div class="metric"><span class="muted">评测模式</span><strong>{html.escape(mode_label(summary['mode']))}</strong></div>
      <div class="metric"><span class="muted">可信等级</span><strong class="trust">{html.escape(trust_label(summary['trust_level']))}</strong></div>
      <div class="metric"><span class="muted">总分</span><strong>{summary['score']}/100</strong></div>
      <div class="metric"><span class="muted">真实样本分</span><strong>{summary['real_sample_score'] if summary['real_sample_score'] is not None else 'N/A'}</strong></div>
      <div class="metric"><span class="muted">AI case 总数</span><strong>{sample['ai_case_count']}</strong></div>
      <div class="metric"><span class="muted">真实回答</span><strong>{sample['real_samples']}</strong></div>
      <a class="metric metric-link" href="#embedded-samples"><span class="muted">内置样例</span><strong>{sample['embedded_samples']}</strong><span class="muted">点击查看样例内容</span></a>
      <div class="metric"><span class="muted">缺少样本</span><strong>{sample['missing_samples']}</strong></div>
      <div class="metric"><span class="muted">真实 session 数</span><strong>{obs['real_session_count']}</strong></div>
      <div class="metric"><span class="muted">可转评测样本数</span><strong>{obs['convertible_sample_count']}</strong></div>
      <div class="metric"><span class="muted">作品集讲解命中率</span><strong>{obs['portfolio_explainer_hit_rate']}%</strong></div>
      <div class="metric"><span class="muted">自我迭代规则数量</span><strong>{obs['self_iteration_rule_count']}</strong></div>
      <div class="metric"><span class="muted">上轮短板本轮覆盖</span><strong>{'是' if obs['previous_weakness_covered'] else '否'}</strong><span class="muted">{obs['self_iteration_behavior_hits']}/{obs['self_iteration_behavior_total']}</span></div>
    </div>
    <p><strong>结论：</strong>{html.escape(summary['level'])}</p>
    <p class="muted">生成时间：{html.escape(summary['generated_at'])}</p>
    <div class="actions">
      <button class="button primary" onclick="window.location.reload()">刷新当前页面</button>
      <a class="button" href="{html.escape(Path(summary['reports']['mode_json']).as_posix())}">查看本模式 JSON</a>
      <a class="button" href="{html.escape(Path(summary['reports']['mode_markdown']).as_posix())}">查看本模式 Markdown</a>
    </div>
  </section>

  <section>
    <h2>关键报告入口</h2>
    <ul>
      <li>本模式 Markdown 报告：{html_path_link(mode_report)}</li>
      <li>评测雷达报告：{html_path_link(radar_report)}</li>
      <li>08 知识笔记：{html_path_link(str(knowledge_note))}</li>
      <li>知识索引：{html_path_link(str(knowledge_index))}</li>
      <li>11 能力雷达报告：{html_path_link(str(capability_report))}</li>
      <li>11 能力雷达 PNG：{html_path_link(str(capability_png))}</li>
    </ul>
  </section>

  <section>
    <h2>能力图与横向对比</h2>
    <div class="two">
      <div>
        <img class="radar" src="{capability_png.as_posix()}" alt="AIPM capability radar">
      </div>
      <div>
        <p>本轮短板：<strong>作品集表达能力</strong>。评测端已经把补强计划、证据链和落地产物链接固定展示，后续每次迭代都能看到表达材料是否越来越完整。</p>
        <p>能力图用于横向比较，不再只看数字。</p>
      </div>
    </div>
  </section>

  <section>
    <h2>{html.escape(PORTFOLIO_EXPRESSION_PLAN['title'])}</h2>
    <p><strong>问题：</strong>{html.escape(PORTFOLIO_EXPRESSION_PLAN['problem'])}</p>
    <p><strong>目标：</strong>{html.escape(PORTFOLIO_EXPRESSION_PLAN['goal'])}</p>
    <h3>架构补强</h3>
    <ul>{plan_sections}</ul>
    <h3>训练任务</h3>
    <ul>{training_tasks}</ul>
    <h3>评测信号</h3>
    <ul>{signals}</ul>
  </section>

  <section>
    <h2>插件 Workflow 多 Skill 状态</h2>
    <p class="muted">这里按 AI 教练真实工作流展示，而不是按脚本内部编号展示。每一行对应插件的一个业务环节，展示它是否响应、如何响应、成功率，以及失败原因。</p>
    <table>
      <thead><tr><th>工作流环节</th><th>职责</th><th>响应状态</th><th>通过数</th><th>成功率</th><th>样本来源</th><th>证据摘要</th></tr></thead>
      <tbody>{''.join(workflow_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>评测脚本节点映射</h2>
    <p class="muted">这是底层自动评测节点，用于追踪规则覆盖。主要看上面的 workflow 表判断插件业务环节是否正常。</p>
    <table>
      <thead><tr><th>节点</th><th>通过数</th><th>分数</th></tr></thead>
      <tbody>{''.join(node_rows)}</tbody>
    </table>
  </section>

  <section>
    <h2>迭代历史</h2>
    <table>
      <thead><tr><th>时间</th><th>评测模式</th><th>可信等级</th><th>分数</th><th>真实回答</th><th>内置样例</th><th>缺少样本</th></tr></thead>
      <tbody>{''.join(history_rows)}</tbody>
    </table>
  </section>

  <section id="embedded-samples">
    <h2>内置样例查看</h2>
    <p class="muted">这些内容来自 case JSON 的 <code>sample_output</code>，只用于样例冒烟测试。你可以展开查看样例是否合理，再回到 cases 目录调整。</p>
    {embedded_blocks}
  </section>

  <section>
    <h2>Case 节点状态与证据</h2>
    <p class="muted">这里用于观测每个 case 当前停在哪个节点、使用什么样本来源、通过或失败的原因，以及命中的证据。补充真实回答后重新运行评测，再点击页面上的刷新按钮即可看到变化。</p>
    <table>
      <thead><tr><th>Case</th><th>当前节点</th><th>样本来源</th><th>工作状态</th><th>原因</th><th>证据</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
  </section>
</main>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def run(allow_fixtures: bool) -> dict[str, Any]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[CheckResult] = []
    results.extend(evaluate_environment())
    results.extend(evaluate_router(allow_fixtures))
    results.extend(evaluate_module_boundary(allow_fixtures))
    results.extend(evaluate_workflow_gating(allow_fixtures))
    results.extend(evaluate_output_structure(allow_fixtures))
    results.extend(evaluate_chinese_encoding(allow_fixtures))
    results.extend(evaluate_radar_history())
    results.extend(evaluate_e2e(allow_fixtures))
    results.extend(evaluate_real_sessions())
    results.extend(evaluate_portfolio_explainer(allow_fixtures))
    results.extend(evaluate_self_iteration(allow_fixtures))
    summary = summarize(results, allow_fixtures)
    history = append_run_history(summary)
    write_json(REPORTS_DIR / "latest-report.json", summary)
    write_markdown_report(REPORTS_DIR / "latest-report.md", summary)
    write_html_dashboard(REPORTS_DIR / "dashboard.html", summary, history)
    mode_name = "fixture-smoke" if allow_fixtures else "strict-real-samples"
    write_json(REPORTS_DIR / f"{mode_name}-report.json", summary)
    write_markdown_report(REPORTS_DIR / f"{mode_name}-report.md", summary)
    write_html_dashboard(REPORTS_DIR / f"{mode_name}-dashboard.html", summary, history)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AIPM Coach evaluation harness.")
    parser.add_argument("--allow-fixtures", action="store_true", help="Allow built-in case sample_output values. This is only a smoke test.")
    parser.add_argument("--json", action="store_true", help="Print the full JSON summary.")
    args = parser.parse_args()

    summary = run(allow_fixtures=args.allow_fixtures)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"AIPM Coach eval mode: {summary['mode']}")
        print(f"Trust level: {summary['trust_level']}")
        print(f"Score: {summary['score']}/100")
        print(f"Real AI answers: {summary['sample_summary']['real_samples']}/{summary['sample_summary']['ai_case_count']}")
        print(f"Embedded fixtures: {summary['sample_summary']['embedded_samples']}")
        print(f"Missing samples: {summary['sample_summary']['missing_samples']}")
        print(f"Conclusion: {summary['level']}")
        print(f"Report: {REPORTS_DIR / 'latest-report.md'}")
        print(f"Dashboard: {REPORTS_DIR / 'dashboard.html'}")
        print(f"Radar report: {REPORTS_DIR / 'capability-radar-report.md'}")

    trust = summary["trust_level"]
    failed_real = trust in {"NOT_REAL_RUN_NO_REAL_SAMPLES", "PARTIAL_REAL_EVAL_MISSING_SAMPLES"}
    severe_defects = summary["defect_counts"]["P0"] > 0 or summary["defect_counts"]["P1"] > 0
    return 1 if failed_real or severe_defects else 0


if __name__ == "__main__":
    raise SystemExit(main())
