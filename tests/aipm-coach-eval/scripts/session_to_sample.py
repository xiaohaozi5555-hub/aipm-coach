#!/usr/bin/env python
"""Convert a real AIPM Coach session run into an eval sample text file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EVAL_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = EVAL_ROOT.parents[1]
SESSION_RUNS_DIR = WORKSPACE_ROOT / "coach-data" / "session-runs"
SAMPLES_DIR = EVAL_ROOT / "samples"
CASES_DIR = EVAL_ROOT / "cases"

CASE_FILES = [
    "router.json",
    "module-boundary.json",
    "workflow-gating.json",
    "output-structure.json",
    "e2e.json",
    "portfolio-explainer.json",
    "self-iteration.json",
]

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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def read_json(path: Path) -> Any:
    return json.loads(read_text(path))


def load_cases() -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for filename in CASE_FILES:
        for case in read_json(CASES_DIR / filename):
            cases[str(case["case_id"])] = case
    return cases


def latest_session_path() -> Path:
    files = sorted(SESSION_RUNS_DIR.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No session JSON files found in {SESSION_RUNS_DIR}")
    return files[0]


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


def build_raw_answer(session: dict[str, Any]) -> str:
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
        keys = called_modules or list(outputs.keys())
        for key in keys:
            if key in outputs:
                text = module_raw_output(outputs[key])
                if text:
                    chunks.append(text)

    return "\n\n".join(chunks).strip()


def collect_fixture_outputs(cases: dict[str, dict[str, Any]]) -> set[str]:
    fixtures: set[str] = set()
    for case in cases.values():
        text = scalar_text(case.get("sample_output"))
        if text:
            fixtures.add(text)
    return fixtures


def validate_session(session: dict[str, Any], cases: dict[str, dict[str, Any]], raw_answer: str) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_SESSION_FIELDS:
        if field not in session:
            errors.append(f"missing required field: {field}")

    eval_case_id = str(session.get("eval_case_id", "")).strip()
    if eval_case_id not in cases:
        errors.append(f"eval_case_id is not defined in eval cases: {eval_case_id}")

    if session.get("fixture_source") or session.get("from_fixture"):
        errors.append("fixture sessions cannot be converted to real samples")

    if str(session.get("session_source", "real_workflow_run")) != "real_workflow_run":
        errors.append("session_source must be real_workflow_run")

    if not raw_answer:
        errors.append("no full_raw_answer or module raw output found")

    case_fixture = scalar_text(cases.get(eval_case_id, {}).get("sample_output"))
    if raw_answer and case_fixture and raw_answer == case_fixture:
        errors.append("raw answer exactly matches this case's sample_output; refusing to treat fixture as real")

    if raw_answer in collect_fixture_outputs(cases):
        errors.append("raw answer exactly matches an embedded case sample_output; refusing to write sample")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a saved AIPM Coach session JSON into samples/<case_id>.txt.")
    parser.add_argument("--session", help="Path to coach-data/session-runs/<run_id>.json.")
    parser.add_argument("--latest", action="store_true", help="Use the newest session JSON in coach-data/session-runs.")
    parser.add_argument("--output-dir", default=str(SAMPLES_DIR), help="Eval samples directory.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing sample file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print the target without writing.")
    args = parser.parse_args()

    if bool(args.session) == bool(args.latest):
        print("Choose exactly one of --session or --latest.", file=sys.stderr)
        return 2

    session_path = latest_session_path() if args.latest else Path(str(args.session)).resolve()
    session = read_json(session_path)
    if not isinstance(session, dict):
        print("Session file must contain a JSON object.", file=sys.stderr)
        return 2

    cases = load_cases()
    raw_answer = build_raw_answer(session)
    errors = validate_session(session, cases, raw_answer)
    if errors:
        print("Cannot convert session to real sample:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    case_id = str(session["eval_case_id"]).strip()
    output_path = Path(args.output_dir).resolve() / f"{case_id}.txt"
    if output_path.exists() and read_text(output_path).strip() and not args.force:
        print(f"Refusing to overwrite existing sample: {output_path}", file=sys.stderr)
        return 3

    if args.dry_run:
        print(f"OK: {session_path} -> {output_path}")
        print(f"Characters: {len(raw_answer)}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(raw_answer.rstrip() + "\n", encoding="utf-8")
    print(f"Wrote real eval sample: {output_path}")
    print(f"Source session: {session_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
