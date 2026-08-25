#!/usr/bin/env python
"""Validate and save a real AIPM Coach workflow session run."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SESSION_RUNS_DIR = WORKSPACE_ROOT / "coach-data" / "session-runs"
EVAL_CASES_DIR = WORKSPACE_ROOT / "tests" / "aipm-coach-eval" / "cases"

REQUIRED_FIELDS = [
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

CASE_FILES = [
    "router.json",
    "module-boundary.json",
    "workflow-gating.json",
    "output-structure.json",
    "e2e.json",
    "portfolio-explainer.json",
    "self-iteration.json",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_cases() -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for filename in CASE_FILES:
        path = EVAL_CASES_DIR / filename
        if not path.exists():
            continue
        for case in read_json(path):
            cases[str(case["case_id"])] = case
    return cases


def normalize_run_id(value: str) -> str:
    run_id = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{2,120}", run_id):
        raise ValueError(
            "run_id must be 3-121 characters and may only contain letters, numbers, dot, underscore, or hyphen."
        )
    return run_id


def walk_keys(value: Any) -> list[str]:
    keys: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(walk_keys(item))
    return keys


def validate_session(session: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in session:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    try:
        session["run_id"] = normalize_run_id(str(session["run_id"]))
    except ValueError as exc:
        errors.append(str(exc))

    if not str(session["timestamp"]).strip():
        errors.append("timestamp must be non-empty")
    if not str(session["user_input"]).strip():
        errors.append("user_input must be non-empty")
    if not isinstance(session["called_modules"], list) or not session["called_modules"]:
        errors.append("called_modules must be a non-empty list")
    if not isinstance(session["module_outputs"], (dict, list)) or not session["module_outputs"]:
        errors.append("module_outputs must be a non-empty dict or list")
    if not isinstance(session["reflection_questions"], list) or not session["reflection_questions"]:
        errors.append("reflection_questions must be a non-empty list")
    if not isinstance(session["learning_evaluation"], (dict, str)) or not session["learning_evaluation"]:
        errors.append("learning_evaluation must be a non-empty object or string")
    if not isinstance(session["gap_evaluation"], (dict, str)) or not session["gap_evaluation"]:
        errors.append("gap_evaluation must be a non-empty object or string")
    if not isinstance(session["radar_scores"], dict) or not session["radar_scores"]:
        errors.append("radar_scores must be a non-empty object")
    if not isinstance(session["radar_artifacts"], (dict, list)) or not session["radar_artifacts"]:
        errors.append("radar_artifacts must be a non-empty dict or list")

    cases = load_cases()
    eval_case_id = str(session["eval_case_id"]).strip()
    if eval_case_id not in cases:
        errors.append(f"eval_case_id is not defined in eval cases: {eval_case_id}")

    forbidden_keys = {key for key in walk_keys(session) if key == "sample_output"}
    if forbidden_keys:
        errors.append("session data must not include case sample_output; it cannot be used as a real run")

    source = str(session.get("session_source", "")).strip()
    if source and source != "real_workflow_run":
        errors.append("session_source must be real_workflow_run when provided")

    if session.get("fixture_source") or session.get("from_fixture"):
        errors.append("fixture sessions cannot be saved as real runs")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Save a validated AIPM Coach real workflow session.")
    parser.add_argument("--input", required=True, help="Draft session JSON file.")
    parser.add_argument("--output-dir", default=str(SESSION_RUNS_DIR), help="Directory for saved session JSON files.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing run_id JSON file.")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    session = read_json(input_path)
    if not isinstance(session, dict):
        print("Session must be a JSON object.", file=sys.stderr)
        return 2

    errors = validate_session(session)
    if errors:
        print("Invalid session run:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    session.setdefault("session_source", "real_workflow_run")
    session.setdefault("saved_at", datetime.now(timezone.utc).isoformat())
    session.setdefault("source_file", str(input_path))

    output_dir = Path(args.output_dir).resolve()
    output_path = output_dir / f"{session['run_id']}.json"
    if output_path.exists() and not args.force:
        print(f"Refusing to overwrite existing session: {output_path}", file=sys.stderr)
        return 3

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(".json.tmp")
    write_json(tmp_path, session)
    shutil.move(str(tmp_path), str(output_path))

    print(f"Saved session run: {output_path}")
    print(f"Eval case: {session['eval_case_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
