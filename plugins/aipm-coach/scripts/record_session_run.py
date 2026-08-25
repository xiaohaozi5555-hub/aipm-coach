#!/usr/bin/env python
"""Finalize one AIPM Coach workflow run for evaluation.

This is the single closing command for a complete coach workflow:

1. validate and save the draft session into coach-data/session-runs/
2. convert it into tests/aipm-coach-eval/samples/<case_id>.txt when possible
3. optionally refresh the strict evaluation report

The script intentionally keeps every validated session even when the eval sample
for the same case already exists. Strict eval currently reads one sample file per
case, while the session directory is the durable "one coach use, one record" log.
"""

from __future__ import annotations

import argparse
import json
import locale
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
SAVE_SESSION_SCRIPT = WORKSPACE_ROOT / "plugins" / "aipm-coach" / "scripts" / "save_session_run.py"
SESSION_TO_SAMPLE_SCRIPT = WORKSPACE_ROOT / "tests" / "aipm-coach-eval" / "scripts" / "session_to_sample.py"
RUN_EVAL_SCRIPT = WORKSPACE_ROOT / "tests" / "aipm-coach-eval" / "run_eval.py"
DEFAULT_SESSION_RUNS_DIR = WORKSPACE_ROOT / "coach-data" / "session-runs"
DEFAULT_SAMPLES_DIR = WORKSPACE_ROOT / "tests" / "aipm-coach-eval" / "samples"
DEFAULT_DRAFTS_DIR = WORKSPACE_ROOT / "coach-data" / "session-drafts"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest_draft_path(draft_dir: Path) -> Path:
    files = sorted(draft_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"No draft session JSON files found in {draft_dir}")
    return files[0]


def run_command(command: list[str], *, force_utf8: bool = False) -> subprocess.CompletedProcess[str]:
    env = None
    encoding = locale.getpreferredencoding(False)
    if force_utf8:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        encoding = "utf-8"
    return subprocess.run(
        command,
        cwd=str(WORKSPACE_ROOT),
        env=env,
        text=True,
        encoding=encoding,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def command_summary(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "command": result.args,
        "exit_code": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Record one completed AIPM Coach workflow run.")
    parser.add_argument("--input", help="Draft session JSON produced by the completed workflow.")
    parser.add_argument("--latest-draft", action="store_true", help="Use the newest JSON draft in --draft-dir.")
    parser.add_argument("--draft-dir", default=str(DEFAULT_DRAFTS_DIR), help="Directory searched by --latest-draft.")
    parser.add_argument("--force-session", action="store_true", help="Overwrite an existing session with the same run_id.")
    parser.add_argument("--force-sample", action="store_true", help="Overwrite samples/<eval_case_id>.txt when it exists.")
    parser.add_argument("--skip-sample", action="store_true", help="Only save the session; do not convert to an eval sample.")
    parser.add_argument("--run-eval", action="store_true", help="Refresh strict eval after saving/converting.")
    parser.add_argument("--session-output-dir", default=str(DEFAULT_SESSION_RUNS_DIR), help="Directory for saved session JSON files.")
    parser.add_argument("--sample-output-dir", default=str(DEFAULT_SAMPLES_DIR), help="Directory for generated eval sample text files.")
    parser.add_argument("--json", action="store_true", help="Print a machine-readable summary.")
    args = parser.parse_args()

    if bool(args.input) == bool(args.latest_draft):
        print("Choose exactly one of --input or --latest-draft.", file=sys.stderr)
        return 2

    try:
        input_path = latest_draft_path(Path(args.draft_dir).resolve()) if args.latest_draft else Path(str(args.input)).resolve()
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    draft = read_json(input_path)
    if not isinstance(draft, dict):
        print("Draft session must be a JSON object.", file=sys.stderr)
        return 2

    run_id = str(draft.get("run_id", "")).strip()
    eval_case_id = str(draft.get("eval_case_id", "")).strip()
    session_output_dir = Path(args.session_output_dir).resolve()
    sample_output_dir = Path(args.sample_output_dir).resolve()
    session_path = session_output_dir / f"{run_id}.json"
    sample_path = sample_output_dir / f"{eval_case_id}.txt"

    summary: dict[str, Any] = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "input": str(input_path),
        "run_id": run_id,
        "eval_case_id": eval_case_id,
        "session_path": str(session_path),
        "sample_path": str(sample_path),
        "session_saved": False,
        "sample_status": "not_started",
        "eval_status": "not_requested",
        "commands": [],
    }

    save_command = [
        sys.executable,
        str(SAVE_SESSION_SCRIPT),
        "--input",
        str(input_path),
        "--output-dir",
        str(session_output_dir),
    ]
    if args.force_session:
        save_command.append("--force")
    save_result = run_command(save_command, force_utf8=True)
    summary["commands"].append(command_summary(save_result))
    if save_result.returncode != 0:
        summary["session_status"] = "failed"
        if args.json:
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(save_result.stdout, end="")
            print(save_result.stderr, end="", file=sys.stderr)
        return save_result.returncode

    summary["session_saved"] = True
    summary["session_status"] = "saved"

    if args.skip_sample:
        summary["sample_status"] = "skipped_by_flag"
    elif sample_path.exists() and sample_path.read_text(encoding="utf-8", errors="replace").strip() and not args.force_sample:
        summary["sample_status"] = "skipped_existing_sample"
    else:
        sample_command = [
            sys.executable,
            str(SESSION_TO_SAMPLE_SCRIPT),
            "--session",
            str(session_path),
            "--output-dir",
            str(sample_output_dir),
        ]
        if args.force_sample:
            sample_command.append("--force")
        sample_result = run_command(sample_command, force_utf8=True)
        summary["commands"].append(command_summary(sample_result))
        if sample_result.returncode == 0:
            summary["sample_status"] = "written"
        else:
            summary["sample_status"] = "failed"
            if args.json:
                print(json.dumps(summary, ensure_ascii=False, indent=2))
            else:
                print(save_result.stdout, end="")
                print(sample_result.stdout, end="")
                print(sample_result.stderr, end="", file=sys.stderr)
            return sample_result.returncode

    if args.run_eval:
        eval_result = run_command([sys.executable, str(RUN_EVAL_SCRIPT)])
        summary["commands"].append(command_summary(eval_result))
        summary["eval_status"] = "refreshed"
        summary["eval_exit_code"] = eval_result.returncode

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Saved session: {session_path}")
        print(f"Eval case: {eval_case_id}")
        print(f"Sample status: {summary['sample_status']}")
        if args.run_eval:
            print(f"Strict eval refreshed with exit code: {summary.get('eval_exit_code')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
