#!/usr/bin/env python
"""Prepare and check the first three real E2E samples for AIPM Coach eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = EVAL_ROOT / "cases" / "e2e.json"
SAMPLES_DIR = EVAL_ROOT / "samples"
PROMPTS_PATH = SAMPLES_DIR / "e2e-collection-prompts.md"

CASE_INPUTS: dict[str, dict[str, str]] = {
    "e2e_project_agent_001": {
        "title": "项目 Agent 设计闭环",
        "user_prompt": (
            "AIPM教练，我想做一个面向产品经理的需求澄清 Agent，"
            "能把用户一句话需求拆成目标、用户、场景、约束、验收标准，"
            "但我不知道该怎么设计 workflow、prompt、评估指标和项目交付路径。"
            "请你按完整教练流程指导我，并在后续带我完成知识记录、复盘、学习吸收评估和能力雷达。"
        ),
        "collection_note": (
            "重点覆盖 router -> guide -> portfolio_explainer -> recorder -> reflection -> "
            "learning_evaluator -> gap_evaluator -> radar。真实样本应包含作品集转化讲解和最终能力雷达数据。"
        ),
    },
    "e2e_portfolio_001": {
        "title": "作品集表达闭环",
        "user_prompt": (
            "AIPM教练，我想把 AIPM Coach 自动评测这件事包装成作品集案例，"
            "但担心只是在展示脚本和分数，不能体现产品判断、取舍、验证证据和面试表达。"
            "请你用专家讨论方式帮我判断叙事主线、亮点、风险和取舍，并继续走完记录、复盘、学习评估和能力雷达。"
        ),
        "collection_note": (
            "重点覆盖 router -> expert_discussion -> portfolio_explainer -> recorder -> reflection -> "
            "learning_evaluator -> gap_evaluator -> radar。真实样本应体现作品集转化讲解和作品集表达建议。"
        ),
    },
    "e2e_tool_issue_001": {
        "title": "工具环境问题闭环",
        "user_prompt": (
            "AIPM教练，我在 VPS 的 Windows 环境里预览前端项目，"
            "用户在大陆本地电脑打不开 localhost:3000。"
            "请你帮我排查 localhost、127.0.0.1、端口、dev server、PowerShell npm.ps1 限制和安全隧道的关系，"
            "并解释原理，然后继续完成知识记录、复盘、学习吸收评估和能力雷达。"
        ),
        "collection_note": (
            "重点覆盖 router -> guide -> explainer -> recorder -> reflection -> "
            "learning_evaluator -> gap_evaluator -> radar。真实样本应包含排障步骤和原理解释。"
        ),
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def e2e_cases() -> list[dict[str, Any]]:
    cases = read_json(CASES_PATH)
    return [case for case in cases if case["case_id"] in CASE_INPUTS]


def sample_path(case_id: str) -> Path:
    return SAMPLES_DIR / f"{case_id}.txt"


def sample_status(case_id: str) -> tuple[bool, int]:
    path = sample_path(case_id)
    if not path.exists():
        return False, 0
    text = path.read_text(encoding="utf-8-sig", errors="replace").strip()
    return bool(text), len(text)


def render_prompts(cases: list[dict[str, Any]]) -> str:
    lines = [
        "# E2E Real Sample Collection Prompts",
        "",
        "这些 prompts 用于采集首批 3 个真实 E2E 样本。把 AIPM Coach 的完整原始回答保存到对应 `samples/<case_id>.txt`，不要改写或补写。",
        "",
    ]
    for case in cases:
        case_id = case["case_id"]
        item = CASE_INPUTS[case_id]
        target = sample_path(case_id).relative_to(EVAL_ROOT)
        expected_steps = " -> ".join(case.get("expected_steps", []))
        lines.extend(
            [
                f"## {case_id}: {item['title']}",
                "",
                f"- Target file: `{target}`",
                f"- Expected E2E markers: `{expected_steps}`",
                f"- Collection note: {item['collection_note']}",
                "",
                "### Prompt",
                "",
                "```text",
                item["user_prompt"],
                "```",
                "",
                "### Minimum save requirement",
                "",
                "- 保存完整原始回答，包含路由、主教练模块、08 记录、09 复盘、10 学习吸收评估、11 差距评估和能力雷达数据。",
                "- 回答中需要能命中 case 的 expected steps，以及 `能力雷达图数据` 和可解析的 `scores` JSON。",
                "",
            ]
        )
    return "\n".join(lines)


def write_prompts(cases: list[dict[str, Any]]) -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    PROMPTS_PATH.write_text(render_prompts(cases) + "\n", encoding="utf-8")


def print_status(cases: list[dict[str, Any]]) -> bool:
    all_ready = True
    print("AIPM Coach E2E real sample status")
    print(f"Cases: {CASES_PATH}")
    print(f"Samples: {SAMPLES_DIR}")
    print("")
    for case in cases:
        case_id = case["case_id"]
        exists, length = sample_status(case_id)
        status = "READY" if exists else "MISSING"
        all_ready = all_ready and exists
        target = sample_path(case_id)
        expected_steps = " -> ".join(case.get("expected_steps", []))
        print(f"- {status} {case_id}")
        print(f"  target: {target}")
        print(f"  expected: {expected_steps}")
        print(f"  chars: {length}")
    print("")
    print(f"Prompt sheet: {PROMPTS_PATH}")
    print("Rerun strict eval: python tests\\aipm-coach-eval\\run_eval.py")
    return all_ready


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare and check AIPM Coach E2E real samples.")
    parser.add_argument("--write-prompts", action="store_true", help="Write samples/e2e-collection-prompts.md.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any E2E sample is missing.")
    args = parser.parse_args()

    cases = e2e_cases()
    if args.write_prompts:
        write_prompts(cases)
    ready = print_status(cases)
    return 1 if args.strict and not ready else 0


if __name__ == "__main__":
    raise SystemExit(main())
