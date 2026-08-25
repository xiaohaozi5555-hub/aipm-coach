#!/usr/bin/env python
"""Verify the distributable AIPM Coach repository structure."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "aipm-coach"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"

EXPECTED_SKILLS = {
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


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    if not MANIFEST.exists():
        fail(errors, f"missing manifest: {MANIFEST}")
    if not MARKETPLACE.exists():
        fail(errors, f"missing marketplace: {MARKETPLACE}")
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))

    if manifest.get("name") != "aipm-coach":
        fail(errors, "manifest name must be aipm-coach")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", str(manifest.get("version", ""))):
        fail(errors, "manifest version is not strict semver")
    if manifest.get("skills") != "./skills/":
        fail(errors, "manifest skills path must be ./skills/")

    entries = marketplace.get("plugins") or []
    matching = [entry for entry in entries if entry.get("name") == "aipm-coach"]
    if len(matching) != 1:
        fail(errors, "marketplace must contain exactly one aipm-coach entry")
    elif matching[0].get("source", {}).get("path") != "./plugins/aipm-coach":
        fail(errors, "marketplace source path must be ./plugins/aipm-coach")

    skill_root = PLUGIN_ROOT / "skills"
    actual_skills = {path.name for path in skill_root.iterdir() if path.is_dir()}
    missing = sorted(EXPECTED_SKILLS - actual_skills)
    unexpected = sorted(actual_skills - EXPECTED_SKILLS)
    if missing:
        fail(errors, f"missing skills: {', '.join(missing)}")
    if unexpected:
        fail(errors, f"unexpected skills: {', '.join(unexpected)}")

    for name in sorted(EXPECTED_SKILLS):
        skill_file = skill_root / name / "SKILL.md"
        agent_file = skill_root / name / "agents" / "openai.yaml"
        if not skill_file.exists():
            fail(errors, f"missing {skill_file.relative_to(ROOT)}")
            continue
        text = skill_file.read_text(encoding="utf-8")
        if not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", text):
            fail(errors, f"front matter name mismatch: {skill_file.relative_to(ROOT)}")
        if not agent_file.exists():
            fail(errors, f"missing {agent_file.relative_to(ROOT)}")

    forbidden = []
    for path in ROOT.rglob("*"):
        if path.name == "__pycache__" or path.suffix == ".pyc" or ".bak-" in path.name:
            forbidden.append(str(path.relative_to(ROOT)))
    if forbidden:
        fail(errors, f"forbidden generated files: {', '.join(forbidden)}")

    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1

    print(f"PASS: plugin manifest and marketplace are valid")
    print(f"PASS: {len(EXPECTED_SKILLS)}/{len(EXPECTED_SKILLS)} expected skills are present")
    print("PASS: no backup, bytecode, or __pycache__ files are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
