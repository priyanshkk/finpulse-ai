"""Generate the 12-second hero GIF shown in README.md.

The animation is drawn with Pillow from the same numbers the seeded demo uses,
so the visual never depends on a screen-recording tool or a live service.

Usage: python scripts/make_demo.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 960, 540
FPS, SECONDS = 10, 12
BG = "#0b1120"
PANEL = "#111a2e"
PANEL2 = "#16213a"
LINE = "#24324f"
TEXT = "#e8eefc"
MUTED = "#93a4c4"
BLUE = "#38bdf8"
PINK = "#f472b6"
GREEN = "#34d399"
AMBER = "#fbbf24"
VIOLET = "#a78bfa"

KPI_VALUES = (482_640, 124_180, 358_460, 196_320)
KPI_LABELS = ("TOTAL INVOICED", "TOTAL EXPENSES", "NET CASHFLOW", "OUTSTANDING")
CHART = ((52, 24), (68, 31), (45, 38), (82, 29), (63, 44), (91, 35))
CATEGORIES = (
    ("Software", 38200, BLUE),
    ("Travel", 29450, GREEN),
    ("Meals", 21800, AMBER),
    ("Office", 18340, PINK),
    ("Marketing", 9600, VIOLET),
)
RECEIPT = (
    "Blue Tokai",
    "12/04/2026",
    "Coffee beans      2 x 450.00",
    "GST 18%           162.00",
    "TOTAL             1,062.00",
)
FIELDS = (
    ("MERCHANT", "Blue Tokai"),
    ("DATE", "2026-04-12"),
    ("TOTAL", "₹1,062.00"),
    ("TAX", "₹162.00"),
    ("ITEMS", "2 detected"),
)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a readable system font with a safe fallback."""
    roots = ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu", "/System/Library/Fonts")
    names = (("segoeuib.ttf", "DejaVuSans-Bold.ttf"), ("segoeui.ttf", "DejaVuSans.ttf"))[not bold]
    for root in roots:
        for name in names:
            path = Path(root) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def ease(value: float) -> float:
    """Clamp to 0..1 and apply an ease-out curve."""
    value = max(0.0, min(1.0, value))
    return 1 - (1 - value) ** 3


def round_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str | None = None,
    radius: int = 12,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)


def draw_frame(index: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    d = ImageDraw.Draw(image)
    f12, f14 = font(12), font(14)
    fbold = font(17, bold=True)
    fnum = font(20, bold=True)

    # Sidebar
    d.rectangle((0, 0, 190, HEIGHT), fill=PANEL)
    d.line((190, 0, 190, HEIGHT), fill=LINE)
    round_rect(d, (18, 20, 50, 52), BLUE, radius=10)
    d.text((27, 27), "F", font=fbold, fill=BG)
    d.text((60, 24), "FinPulse AI", font=fbold, fill=TEXT)
    for y, label in ((92, "Overview"), (130, "Invoices"), (168, "Expenses"), (206, "Scan receipt")):
        if y == 92:
            round_rect(d, (12, y - 7, 178, y + 29), PANEL2, radius=8)
        d.text((28, y), label, font=f14, fill=TEXT if y == 92 else MUTED)
    d.text((24, 500), "● Offline parser", font=f12, fill=MUTED)

    # Header
    d.text((216, 22), "Overview", font=font(24, bold=True), fill=TEXT)
    d.text((216, 54), "Your business at a glance", font=f12, fill=MUTED)
    round_rect(d, (812, 26, 940, 53), "#064e3b", radius=13)
    d.text((827, 32), "Demo data", font=f12, fill="#6ee7b7")

    # KPI cards
    p0 = ease(index / 22)
    for col, (label, value) in enumerate(zip(KPI_LABELS, KPI_VALUES, strict=True)):
        x = 216 + col * 186
        accent = col == 2
        round_rect(d, (x, 82, x + 172, 170), PANEL2 if accent else PANEL, "#2563eb" if accent else LINE)
        d.text((x + 14, 95), label, font=f12, fill=MUTED)
        shown = f"₹{int(value * p0):,}"
        d.text((x + 14, 116), shown, font=fnum, fill=TEXT)
        d.text((x + 14, 149), f"{14 if col in (0, 2, 3) else 19} records", font=f12, fill="#64748b")

    # Cashflow chart
    round_rect(d, (216, 184, 688, 418), PANEL, LINE)
    d.text((236, 198), "Cashflow", font=fbold, fill=TEXT)
    d.text((572, 202), "● Invoiced  ● Spent", font=f12, fill=MUTED)
    p1 = ease((index - 25) / 35)
    base = 390
    for col, (inv, exp) in enumerate(CHART):
        x = 252 + col * 70
        for offset, value, color in ((0, inv, BLUE), (20, exp, PINK)):
            height = int(value * 1.55 * p1)
            d.rounded_rectangle((x + offset, base - height, x + offset + 18, base), radius=4, fill=color)
        d.text((x + 10, 396), ("Jun", "Jul", "Aug", "Sep", "Oct", "Nov")[col], font=f12, fill=MUTED)

    # Category chart
    round_rect(d, (704, 184, 940, 418), PANEL, LINE)
    d.text((722, 198), "Spend by category", font=fbold, fill=TEXT)
    p2 = ease((index - 40) / 35)
    for row, (label, value, color) in enumerate(CATEGORIES):
        y = 238 + row * 34
        d.text((722, y), label, font=f12, fill=MUTED)
        d.text((900, y), f"₹{value:,}", font=f12, fill=MUTED, anchor="ra")
        round_rect(d, (722, y + 18, 922, y + 26), "#0d1527", radius=4)
        length = int(190 * value / 38200 * p2)
        if length > 0:
            round_rect(d, (722, y + 18, 722 + length, y + 26), color, radius=4)

    # Scan panel
    round_rect(d, (216, 432, 940, 526), PANEL, LINE)
    d.text((236, 444), "Receipt scan → extracted fields", font=f14, fill=TEXT)
    round_rect(d, (236, 468, 520, 516), "#0d1527", LINE, radius=8)
    for row, line in enumerate(RECEIPT):
        d.text((246, 471 + row * 8), line, font=font(8), fill="#cbd5e1")
    if 25 <= index <= 62:
        scan_y = 470 + ((index - 25) % 38) * 1.2
        d.line((236, scan_y, 520, scan_y), fill=GREEN, width=2)
    p3 = ease((index - 58) / 30)
    for row, (label, value) in enumerate(FIELDS):
        x = 540 + (row % 3) * 132
        y = 468 + (row // 3) * 26
        alpha = p3 if row < 3 else ease((index - 70 - (row - 3) * 8) / 12)
        if alpha <= 0:
            continue
        round_rect(d, (x, y, x + 124, y + 22), PANEL2, LINE, radius=6)
        d.text((x + 8, y + 3), label, font=font(8), fill=MUTED)
        d.text((x + 8, y + 12), value, font=font(9, bold=True), fill=GREEN if alpha > 0.6 else MUTED)

    # Saved toast
    p4 = ease((index - 92) / 10)
    if p4 > 0:
        y = int(80 - 40 * p4)
        round_rect(d, (700, y, 930, y + 32), "#064e3b", radius=8)
        d.text((720, y + 8), "✓ Saved as expense", font=f14, fill="#d1fae5")

    return image


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "docs" / "assets" / "demo.gif"
    out.parent.mkdir(parents=True, exist_ok=True)
    frames = [draw_frame(i) for i in range(FPS * SECONDS)]
    palette = frames[0].quantize(colors=64)
    frames = [frame.quantize(palette=palette) for frame in frames]
    frames[0].save(
        out, save_all=True, append_images=frames[1:], duration=1000 // FPS, loop=0, optimize=True, disposal=2
    )
    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB, {SECONDS}s)")


if __name__ == "__main__":
    main()
