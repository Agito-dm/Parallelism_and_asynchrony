import html
import json
from pathlib import Path
from typing import Any


def export_stats_to_json(stats: dict[str, Any], filename: str | Path) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(
            stats,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


def export_stats_to_html(stats: dict[str, Any], filename: str | Path) -> None:
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    html_content = render_stats_html(stats)

    path.write_text(
        html_content,
        encoding="utf-8",
    )


def render_stats_html(stats: dict[str, Any]) -> str:
    total_pages = stats.get("total_pages", 0)
    successful = stats.get("successful", 0)
    failed = stats.get("failed", 0)
    duration_seconds = stats.get("duration_seconds", 0.0)
    pages_per_second = stats.get("pages_per_second", 0.0)
    started_at = stats.get("started_at")
    finished_at = stats.get("finished_at")

    status_codes = stats.get("status_codes", {}) or {}
    top_domains = stats.get("top_domains", {}) or {}

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <title>Crawler Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 32px;
            line-height: 1.5;
        }}
        h1, h2 {{
            color: #222;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 24px;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 8px 12px;
            text-align: left;
        }}
        th {{
            background: #f2f2f2;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
            margin-bottom: 24px;
        }}
        .metric {{
            border: 1px solid #ccc;
            border-radius: 6px;
            padding: 12px;
            background: #fafafa;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
        }}
        .bar-container {{
            width: 100%;
            background: #eee;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bar {{
            height: 14px;
            background: #999;
        }}
    </style>
</head>
<body>
    <h1>Crawler Report</h1>

    <h2>Summary</h2>
    <div class="metric-grid">
        {render_metric("Total pages", total_pages)}
        {render_metric("Successful", successful)}
        {render_metric("Failed", failed)}
        {render_metric("Duration seconds", round_float(duration_seconds))}
        {render_metric("Pages per second", round_float(pages_per_second))}
    </div>

    <h2>Timing</h2>
    <table>
        <tbody>
            <tr>
                <th>Started at</th>
                <td>{escape_value(started_at)}</td>
            </tr>
            <tr>
                <th>Finished at</th>
                <td>{escape_value(finished_at)}</td>
            </tr>
        </tbody>
    </table>

    <h2>Status codes</h2>
    {render_mapping_table(status_codes, "Status code", "Count")}

    <h2>Top domains</h2>
    {render_mapping_table(top_domains, "Domain", "Count")}
</body>
</html>
"""


def render_metric(label: str, value: Any) -> str:
    return f"""
        <div class="metric">
            <div>{escape_value(label)}</div>
            <div class="metric-value">{escape_value(value)}</div>
        </div>
    """


def render_mapping_table(
    mapping: dict[Any, Any],
    key_label: str,
    value_label: str,
) -> str:
    if not mapping:
        return "<p>No data.</p>"

    max_value = max((_to_number(value) for value in mapping.values()), default=0)

    rows = []

    for key, value in mapping.items():
        numeric_value = _to_number(value)
        percent = 0.0

        if max_value > 0:
            percent = numeric_value / max_value * 100

        rows.append(
            f"""
            <tr>
                <td>{escape_value(key)}</td>
                <td>{escape_value(value)}</td>
                <td>
                    <div class="bar-container">
                        <div class="bar" style="width: {percent:.1f}%"></div>
                    </div>
                </td>
            </tr>
            """
        )

    rows_html = "\n".join(rows)

    return f"""
    <table>
        <thead>
            <tr>
                <th>{escape_value(key_label)}</th>
                <th>{escape_value(value_label)}</th>
                <th>Visualization</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    """


def _to_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def escape_value(value: Any) -> str:
    if value is None:
        return ""

    return html.escape(str(value))


def round_float(value: Any, digits: int = 3) -> Any:
    if isinstance(value, float):
        return round(value, digits)

    return value