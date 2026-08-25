#!/usr/bin/env python
"""Generate AIPM capability radar charts and maintain local history."""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


DIMENSIONS = [
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


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def parse_time(value: str | None) -> datetime:
    if not value:
        return datetime.now().astimezone()
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.now().astimezone()


def filename_stamp(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d-%H-%M")


def clamp_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 0
    return max(0, min(5, score))


def normalize_record(raw: dict[str, Any], radar_dir: Path) -> dict[str, Any]:
    dt = parse_time(raw.get("timestamp"))
    timestamp = dt.isoformat(timespec="seconds")
    scores = raw.get("scores") or {}
    normalized_scores = {name: clamp_score(scores.get(name, 0)) for name in DIMENSIONS}
    stamp = filename_stamp(dt)
    image_path = radar_dir / f"{stamp}-capability-radar.png"
    record = {
        "timestamp": timestamp,
        "source_note": str(raw.get("source_note") or ""),
        "total_score": sum(normalized_scores.values()),
        "scores": normalized_scores,
        "strengths": list(raw.get("strengths") or []),
        "weaknesses": list(raw.get("weaknesses") or []),
        "summary": str(raw.get("summary") or ""),
        "next_tasks": list(raw.get("next_tasks") or []),
        "radar_image": str(image_path).replace("\\", "/"),
    }
    return record


def read_json_lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def write_json_lines(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )


def wrap_label(label: str) -> str:
    replacements = {
        "Prompt 指令设计能力": "Prompt\n指令设计",
        "AI 工作流理解": "AI 工作流\n理解",
    }
    return replacements.get(label, label.replace("能力", "\n能力"))


def draw_radar(record: dict[str, Any], output_path: Path) -> None:
    width, height = 1200, 900
    center = (width // 2, 375)
    radius = 245
    img = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(img)
    font_title = load_font(34)
    font_label = load_font(19)
    font_small = load_font(17)
    font_legend = load_font(20)

    # Background grid.
    for x in range(0, width, 40):
        draw.line([(x, 0), (x, height)], fill="#f4f7fb", width=1)
    for y in range(0, height, 40):
        draw.line([(0, y), (width, y)], fill="#f4f7fb", width=1)

    angles = [(-math.pi / 2) + (2 * math.pi * i / len(DIMENSIONS)) for i in range(len(DIMENSIONS))]

    def point(angle: float, value: float) -> tuple[float, float]:
        return (
            center[0] + math.cos(angle) * radius * value,
            center[1] + math.sin(angle) * radius * value,
        )

    # Polygon levels.
    for level in range(1, 6):
        value = level / 5
        pts = [point(angle, value) for angle in angles]
        draw.polygon(pts, outline="#d6dee8")
        label_pos = point(-math.pi / 2, value)
        draw.text((label_pos[0] + 8, label_pos[1] - 10), str(level), fill="#7a8699", font=font_small)

    # Axis and labels.
    for angle, label in zip(angles, DIMENSIONS):
        end = point(angle, 1)
        draw.line([center, end], fill="#d6dee8", width=1)
        label_point = point(angle, 1.18)
        wrapped = wrap_label(label)
        bbox = draw.multiline_textbbox((0, 0), wrapped, font=font_label, spacing=2)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.multiline_text(
            (label_point[0] - tw / 2, label_point[1] - th / 2),
            wrapped,
            fill="#253041",
            font=font_label,
            align="center",
            spacing=2,
        )

    # Score polygon.
    scores = record["scores"]
    score_points = [point(angle, scores[label] / 5) for angle, label in zip(angles, DIMENSIONS)]
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    odraw = ImageDraw.Draw(overlay)
    odraw.polygon(score_points, fill=(37, 99, 235, 70), outline=(37, 99, 235, 255))
    for pt in score_points:
        odraw.ellipse((pt[0] - 5, pt[1] - 5, pt[0] + 5, pt[1] + 5), fill=(37, 99, 235, 255))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    title = "AIPM 能力雷达图"
    subtitle = f"{record['timestamp']}   总分 {record['total_score']}/50"
    draw.text((40, 32), title, fill="#111827", font=font_title)
    draw.text((42, 82), subtitle, fill="#4b5563", font=font_legend)

    legend_x, legend_y = 40, 735
    draw.rounded_rectangle((legend_x, legend_y, width - 40, height - 35), radius=12, fill="#f8fafc", outline="#e5e7eb")
    draw.text((legend_x + 20, legend_y + 18), "本轮摘要", fill="#111827", font=font_legend)
    summary = record.get("summary") or "暂无摘要"
    draw.text((legend_x + 20, legend_y + 52), summary[:72], fill="#374151", font=font_small)
    strengths = "、".join(record.get("strengths") or ["暂无"])
    weaknesses = "、".join(record.get("weaknesses") or ["暂无"])
    draw.text((legend_x + 20, legend_y + 88), f"优势：{strengths}", fill="#166534", font=font_small)
    draw.text((legend_x + 20, legend_y + 120), f"短板：{weaknesses}", fill="#991b1b", font=font_small)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


def compare_scores(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    if not previous:
        return {"has_previous": False, "improved": [], "declined": [], "stable": []}
    improved = []
    declined = []
    stable = []
    prev_scores = previous.get("scores", {})
    curr_scores = current.get("scores", {})
    for dimension in DIMENSIONS:
        before = int(prev_scores.get(dimension, 0))
        after = int(curr_scores.get(dimension, 0))
        item = {"dimension": dimension, "before": before, "after": after, "delta": after - before}
        if after > before:
            improved.append(item)
        elif after < before:
            declined.append(item)
        else:
            stable.append(item)
    return {"has_previous": True, "improved": improved, "declined": declined, "stable": stable}


def rebuild_index(path: Path, records: list[dict[str, Any]]) -> None:
    lines = [
        "# AIPM Capability Radar Index",
        "",
        "| 时间 | 总分 | 主要优势 | 主要短板 | 摘要 | 图片 |",
        "|---|---:|---|---|---|---|",
    ]
    for record in records:
        strengths = ", ".join(record.get("strengths") or [])
        weaknesses = ", ".join(record.get("weaknesses") or [])
        summary = re.sub(r"\s+", " ", record.get("summary") or "")
        image = record.get("radar_image", "")
        lines.append(
            f"| {record.get('timestamp', '')} | {record.get('total_score', 0)}/50 | "
            f"{strengths} | {weaknesses} | {summary} | {image} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AIPM capability radar chart and update history.")
    parser.add_argument("--input", required=True, help="Path to input JSON score file.")
    parser.add_argument("--output-root", default="coach-data/capability-radar", help="Radar history directory.")
    args = parser.parse_args()

    input_path = Path(args.input)
    radar_dir = Path(args.output_root)
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    record = normalize_record(raw, radar_dir)

    radar_dir.mkdir(parents=True, exist_ok=True)
    history_path = radar_dir / "history.jsonl"
    latest_path = radar_dir / "latest.json"
    index_path = radar_dir / "index.md"

    history = read_json_lines(history_path)
    previous = history[-1] if history else None
    comparison = compare_scores(previous, record)
    history.append(record)

    write_json_lines(history_path, history)
    latest_items = history[-5:]
    latest_path.write_text(
        json.dumps({"recent_limit": 5, "items": latest_items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    rebuild_index(index_path, history)
    draw_radar(record, Path(record["radar_image"]))

    result = {
        "record": record,
        "comparison": comparison,
        "history_count": len(history),
        "latest_count": len(latest_items),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
