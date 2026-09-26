"""Writes each experiment's results to experiments/results/ as JSON (full
raw trial records + computed metrics, for later re-analysis) and a short
Markdown summary (for quick reading / pasting into the paper)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _trial_payload(trial: Any) -> dict:
    return trial.as_dict() if hasattr(trial, "as_dict") else trial


def _render_metrics_markdown(metrics: dict, depth: int = 0) -> list[str]:
    """Renders a (possibly nested) metrics dict as nested Markdown bullets
    rather than dumping Python repr of dicts/lists into a table cell."""
    lines: list[str] = []
    indent = "  " * depth
    for key, value in metrics.items():
        if isinstance(value, dict):
            lines.append(f"{indent}- **{key}**:")
            lines.extend(_render_metrics_markdown(value, depth + 1))
        elif isinstance(value, (list, tuple)) and any(isinstance(v, dict) for v in value):
            lines.append(f"{indent}- **{key}**:")
            for i, item in enumerate(value):
                lines.append(f"{indent}  - [{i}]:")
                lines.extend(_render_metrics_markdown(item, depth + 2) if isinstance(item, dict) else [f"{indent}    {item}"])
        else:
            lines.append(f"{indent}- **{key}**: {value}")
    return lines


def write_report(
    experiment_id: str,
    title: str,
    config: dict,
    metrics: dict,
    trials: list[Any] | None = None,
    notes: str = "",
) -> Path:
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{experiment_id}_{_slug(title)}"

    payload = {
        "experiment_id": experiment_id,
        "title": title,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "metrics": metrics,
        "notes": notes,
        "trials": [_trial_payload(t) for t in (trials or [])],
    }
    json_path = _RESULTS_DIR / f"{base}.json"
    json_path.write_text(json.dumps(payload, indent=2, default=str))

    lines = [f"# {experiment_id}: {title}", "", f"Generated: {payload['generated_at']}", ""]
    if config:
        lines += ["## Config", ""]
        lines += [f"- **{k}**: {v}" for k, v in config.items()]
        lines.append("")
    lines += ["## Metrics", ""]
    lines += _render_metrics_markdown(metrics)
    if notes:
        lines += ["", "## Notes", "", notes]
    lines += ["", f"Full per-trial records: `{json_path.name}`"]
    md_path = _RESULTS_DIR / f"{base}.md"
    md_path.write_text("\n".join(lines) + "\n")

    return json_path


def write_blocked(experiment_id: str, title: str, reason: str, unblock_condition: str) -> Path:
    """For experiments that cannot run in this environment (E16-E18, E23,
    E8's human-timing portion) - keeps the results/ directory a complete,
    honest map of all 33 rather than silently omitting the blocked ones."""
    return write_report(
        experiment_id,
        title,
        config={},
        metrics={"status": "blocked"},
        trials=[],
        notes=f"**Blocked**: {reason}\n\n**Unblock when**: {unblock_condition}",
    )
