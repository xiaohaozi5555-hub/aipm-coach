#!/usr/bin/env python
"""Promote evidence-backed AIPM Coach improvement items into active lessons."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BACKLOG = WORKSPACE_ROOT / "coach-data" / "improvement-backlog.jsonl"
DEFAULT_ACTIVE = WORKSPACE_ROOT / "coach-data" / "coach-policy" / "active-lessons.md"

KNOWN_SKILLS = {
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
}

START_MARKER = "<!-- BEGIN AUTO-GENERATED LESSONS -->"
END_MARKER = "<!-- END AUTO-GENERATED LESSONS -->"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "；".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = normalize_text(value)
    return [text] if text else []


def stable_id(item: dict[str, Any]) -> str:
    basis = "|".join(
        [
            normalize_text(item.get("timestamp")),
            normalize_text(item.get("target_skill")),
            normalize_text(item.get("weakness")),
            normalize_text(item.get("expected_next_behavior")),
        ]
    )
    return "coach-lesson-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]


def normalize_item(raw: dict[str, Any]) -> dict[str, Any]:
    item = dict(raw)
    item.setdefault("id", stable_id(item))
    item.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    item.setdefault("status", "candidate")
    item.setdefault("created_by", "aipm-gap-evaluator")
    item["evidence"] = normalize_list(item.get("evidence"))
    item["eval_signal"] = normalize_list(item.get("eval_signal"))
    return item


def extract_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [normalize_item(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    for key in ("coach_self_improvement", "coach_self_improvements", "coach_improvement_suggestions"):
        nested = value.get(key)
        if isinstance(nested, list):
            return [normalize_item(item) for item in nested if isinstance(item, dict)]
        if isinstance(nested, dict):
            return [normalize_item(nested)]
    if any(key in value for key in ("weakness", "coach_improvement", "target_skill", "expected_next_behavior")):
        return [normalize_item(value)]
    return []


def load_backlog(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
        if isinstance(parsed, dict):
            items.append(normalize_item(parsed))
    return items


def append_backlog(path: Path, items: list[dict[str, Any]]) -> int:
    if not items:
        return 0
    existing_ids = {item.get("id") for item in load_backlog(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            if item["id"] in existing_ids:
                continue
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")
            existing_ids.add(item["id"])
            count += 1
    return count


def validation_errors(item: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_text = ["weakness", "coach_improvement", "target_skill", "expected_next_behavior"]
    for field in required_text:
        if not normalize_text(item.get(field)):
            errors.append(f"missing {field}")
    target_skill = normalize_text(item.get("target_skill"))
    if target_skill not in KNOWN_SKILLS:
        errors.append(f"unknown target_skill: {target_skill}")
    if not normalize_list(item.get("evidence")):
        errors.append("missing evidence")
    if not normalize_list(item.get("eval_signal")):
        errors.append("missing eval_signal")
    return errors


def promotable_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    promoted: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in items:
        if item.get("status") == "rejected":
            continue
        errors = validation_errors(item)
        if errors:
            continue
        if item["id"] in seen_ids:
            continue
        seen_ids.add(item["id"])
        promoted.append(item)
    return promoted


def render_lessons(items: list[dict[str, Any]]) -> str:
    if not items:
        return "\nNo active lessons yet.\n"

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(normalize_text(item["target_skill"]), []).append(item)

    lines: list[str] = [""]
    for skill in sorted(grouped):
        lines.append(f"### {skill}")
        lines.append("")
        for item in grouped[skill]:
            lines.extend(
                [
                    f"- **Rule ID:** `{item['id']}`",
                    f"- **Weakness:** {normalize_text(item.get('weakness'))}",
                    f"- **Coach behavior:** {normalize_text(item.get('coach_improvement'))}",
                    f"- **Next behavior:** {normalize_text(item.get('expected_next_behavior'))}",
                    f"- **Evaluation signal:** {normalize_text(item.get('eval_signal'))}",
                    f"- **Evidence:** {normalize_text(item.get('evidence'))}",
                    "",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def default_active_doc() -> str:
    return f"""# AIPM Coach Active Lessons

This file is the durable policy memory for AIPM Coach self-improvement.

Every AIPM Coach run should read this file before routing or answering. These lessons are not user capability scores; they are behavior rules the coach must apply in the next run.

## Promotion Guard

Only promote a backlog item into this file when all conditions are true:

- `weakness` is specific and tied to the current evaluation.
- `evidence` is non-empty and points to observable output, saved files, radar history, session data, or eval reports.
- `coach_improvement` states how the coach should change its behavior.
- `target_skill` names one concrete skill that must change behavior.
- `expected_next_behavior` is executable in the next coaching run.
- `eval_signal` is non-empty and can be checked in a later evaluation.

Do not promote vague advice, stylistic preferences without evidence, or rules without a target skill.

## Active Rules

{START_MARKER}
{END_MARKER}
"""


def update_active_lessons(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    current = path.read_text(encoding="utf-8") if path.exists() else default_active_doc()
    if START_MARKER not in current or END_MARKER not in current:
        current = default_active_doc()
    before, rest = current.split(START_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    new_content = before + START_MARKER + "\n" + render_lessons(items) + "\n" + END_MARKER + after
    path.write_text(new_content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Append and promote AIPM Coach improvement lessons.")
    parser.add_argument("--input", help="JSON file containing one item, a list, or coach_self_improvement field.")
    parser.add_argument("--backlog", default=str(DEFAULT_BACKLOG), help="Improvement backlog JSONL path.")
    parser.add_argument("--active", default=str(DEFAULT_ACTIVE), help="Active lessons Markdown path.")
    parser.add_argument("--promote-only", action="store_true", help="Only rebuild active lessons from backlog.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary.")
    args = parser.parse_args()

    backlog_path = Path(args.backlog).resolve()
    active_path = Path(args.active).resolve()

    appended = 0
    if args.input and not args.promote_only:
        items = extract_items(read_json(Path(args.input).resolve()))
        appended = append_backlog(backlog_path, items)

    backlog = load_backlog(backlog_path)
    valid = promotable_items(backlog)
    update_active_lessons(active_path, valid)

    invalid_count = len(backlog) - len(valid)
    summary = {
        "backlog": str(backlog_path),
        "active_lessons": str(active_path),
        "appended": appended,
        "backlog_items": len(backlog),
        "promoted_items": len(valid),
        "invalid_or_rejected_items": invalid_count,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"Backlog: {backlog_path}")
        print(f"Active lessons: {active_path}")
        print(f"Appended: {appended}")
        print(f"Promoted: {len(valid)}")
        print(f"Invalid or rejected: {invalid_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
