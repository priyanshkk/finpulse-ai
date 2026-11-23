"""Dependency-free SVG charts rendered server-side (no CDN, works offline)."""

from __future__ import annotations

from decimal import Decimal

from ..schemas import Point, Slice

PALETTE = ("#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#fb7185")
_MAX_BARS = 6


def _scale(value: Decimal, maximum: Decimal, height: float) -> float:
    if maximum <= 0:
        return 0.0
    return float(value) / float(maximum) * height


def cashflow_svg(points: list[Point], width: int = 640, height: int = 240) -> str:
    """Return an SVG grouped bar chart of invoiced vs spent per month."""
    if not points:
        return '<svg role="img" aria-label="No cashflow data"></svg>'
    maximum = max((max(point.invoiced, point.spent) for point in points), default=Decimal("1"))
    if maximum <= 0:
        maximum = Decimal("1")
    group_width = width / len(points)
    bar_width = min(26.0, group_width / 3)
    baseline = height - 34
    plot_height = baseline - 18

    bars: list[str] = []
    labels: list[str] = []
    for index, point in enumerate(points):
        center = group_width * (index + 0.5)
        invoiced = _scale(point.invoiced, maximum, plot_height)
        spent = _scale(point.spent, maximum, plot_height)
        bars.append(
            f'<rect x="{center - bar_width - 2:.1f}" y="{baseline - invoiced:.1f}" '
            f'width="{bar_width:.1f}" height="{invoiced:.1f}" rx="4" fill="#38bdf8">'
            f"<title>{point.label}: invoiced {point.invoiced}</title></rect>"
        )
        bars.append(
            f'<rect x="{center + 2:.1f}" y="{baseline - spent:.1f}" '
            f'width="{bar_width:.1f}" height="{spent:.1f}" rx="4" fill="#f472b6">'
            f"<title>{point.label}: spent {point.spent}</title></rect>"
        )
        labels.append(
            f'<text x="{center:.1f}" y="{height - 10}" text-anchor="middle" class="axis">{point.label}</text>'
        )

    grid = "".join(
        f'<line x1="0" y1="{baseline - plot_height * step / 4:.1f}" x2="{width}" '
        f'y2="{baseline - plot_height * step / 4:.1f}" class="grid"/>'
        for step in range(5)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Monthly cashflow chart" '
        f'class="chart"><title>Monthly cashflow</title>{grid}{"".join(bars)}{"".join(labels)}</svg>'
    )


def category_svg(slices: list[Slice], width: int = 320, row_height: int = 34) -> str:
    """Return an SVG horizontal bar chart of spend by category."""
    if not slices:
        return '<svg role="img" aria-label="No expense data"></svg>'
    maximum = max((entry.value for entry in slices), default=Decimal("1"))
    if maximum <= 0:
        maximum = Decimal("1")
    height = row_height * len(slices) + 12
    rows: list[str] = []
    for index, entry in enumerate(slices[:_MAX_BARS]):
        y = 8 + index * row_height
        fill = PALETTE[index % len(PALETTE)]
        length = _scale(entry.value, maximum, width - 150)
        rows.append(
            f'<text x="0" y="{y + 14}" class="axis">{entry.label}</text>'
            f'<rect x="96" y="{y + 3}" width="{length:.1f}" height="14" rx="7" fill="{fill}">'
            f"<title>{entry.label}: {entry.value}</title></rect>"
            f'<text x="{width - 4}" y="{y + 14}" text-anchor="end" class="axis">{entry.value}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Spend by category" '
        f'class="chart">' + "".join(rows) + "</svg>"
    )
