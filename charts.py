"""Small dependency-free SVG plotters for real ngspice result arrays.

The browser only displays these SVGs; it never re-derives engineering data.
"""

from __future__ import annotations

import math

TEAL = "#018092"
ORANGE = "#a65316"
GRID = "#d7e4ec"
INK = "#123047"
MUTED = "#536e80"


def _downsample(rows: list[dict[str, float]], limit: int = 400) -> list[dict[str, float]]:
    if len(rows) <= limit:
        return rows
    step = math.ceil(len(rows) / limit)
    return rows[::step]


def _linear_ticks(low: float, high: float, count: int = 5) -> list[float]:
    if high <= low:
        return [low]
    return [low + (high - low) * i / (count - 1) for i in range(count)]


def _log_ticks(low: float, high: float) -> list[float]:
    start = math.floor(math.log10(low))
    end = math.ceil(math.log10(high))
    return [10**power for power in range(start, end + 1)]


def _polyline(
    points: list[tuple[float, float]], colour: str, width: float = 2.2
) -> str:
    body = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return (
        f'<polyline fill="none" stroke="{colour}" stroke-width="{width}" '
        f'stroke-linejoin="round" stroke-linecap="round" points="{body}"/>'
    )


def bode_svg(rows: list[dict[str, float]]) -> str:
    """Gain (dB) and phase (deg) against log frequency, from .ac output."""
    data = _downsample(rows)
    if not data:
        return '<p class="chart-empty">No AC data in this run.</p>'

    freqs = [row["freq_hz"] for row in data]
    gains = [row["gain_db"] for row in data]
    phases = [row["phase_deg"] for row in data]
    fmin, fmax = min(freqs), max(freqs)
    gmin, gmax = min(gains) - 1, max(gains) + 1
    pmin, pmax = min(phases) - 5, max(phases) + 5
    if gmin == gmax:
        gmax = gmin + 1
    if pmin == pmax:
        pmax = pmin + 5

    width, height = 900, 430
    left, right, top, gap, bottom = 72, 26, 34, 34, 46
    plot_w = width - left - right
    plot_h = (height - top - bottom - gap) / 2

    def x_pos(freq: float) -> float:
        if fmax <= fmin:
            return left
        return left + (math.log10(freq) - math.log10(fmin)) / (
            math.log10(fmax) - math.log10(fmin)
        ) * plot_w

    def y_pos(value: float, low: float, high: float, offset: float) -> float:
        return offset + plot_h - (value - low) / (high - low) * plot_h

    parts = [
        f'<svg class="plot" viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="bode-title bode-desc">',
        '<title id="bode-title">AC frequency response from ngspice</title>',
        '<desc id="bode-desc">Gain in decibels and phase in degrees versus '
        'frequency in hertz on a logarithmic axis.</desc>',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
    ]
    for panel, (low, high, values, colour, label) in enumerate(
        (
            (gmin, gmax, gains, TEAL, "Gain (dB) = Vout(dB) - Vin(dB)"),
            (pmin, pmax, phases, ORANGE, "Phase (deg) = Vout(deg) - Vin(deg)"),
        )
    ):
        top_y = top + panel * (plot_h + gap)
        parts.append(
            f'<rect x="{left}" y="{top_y:.1f}" width="{plot_w}" '
            f'height="{plot_h:.1f}" fill="#f9fcfd" stroke="{GRID}"/>'
        )
        for tick in _linear_ticks(low, high, 5):
            y = y_pos(tick, low, high, top_y)
            parts.append(
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
                f'stroke="{GRID}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" '
                f'font-size="14" fill="{MUTED}">{tick:.1f}</text>'
            )
        for tick in _log_ticks(fmin, fmax):
            if tick < fmin or tick > fmax:
                continue
            x = x_pos(tick)
            parts.append(
                f'<line x1="{x:.1f}" y1="{top_y:.1f}" x2="{x:.1f}" '
                f'y2="{top_y + plot_h:.1f}" stroke="{GRID}" stroke-width="1"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{top_y + plot_h + 18:.1f}" text-anchor="middle" '
                f'font-size="13" fill="{MUTED}">{tick:g}</text>'
            )
        points = [
            (x_pos(row["freq_hz"]), y_pos(values[i], low, high, top_y))
            for i, row in enumerate(data)
        ]
        parts.append(_polyline(points, colour))
        parts.append(
            f'<text x="{left + 8}" y="{top_y + 16:.1f}" font-size="14" '
            f'fill="{INK}" font-weight="700">{label}</text>'
        )
        parts.append(
            f'<text x="{left - 52}" y="{top_y + plot_h / 2:.1f}" font-size="14" '
            f'fill="{INK}" transform="rotate(-90 {left - 52} {top_y + plot_h / 2:.1f})">'
            f'{"dB" if panel == 0 else "deg"}</text>'
        )
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" text-anchor="middle" '
        f'font-size="14" fill="{INK}">Frequency (Hz, log scale)</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def waveform_svg(rows: list[dict[str, float]]) -> str:
    """Vin and Vout against time, from .tran output."""
    data = _downsample(rows)
    if not data:
        return '<p class="chart-empty">No transient data in this run.</p>'

    times = [row["t_s"] * 1000.0 for row in data]
    volts = [row["vin_v"] * 1000.0 for row in data] + [
        row["vout_v"] * 1000.0 for row in data
    ]
    tmin, tmax = min(times), max(times)
    vmin, vmax = min(volts) - 1, max(volts) + 1
    if vmin == vmax:
        vmax = vmin + 1

    width, height = 900, 320
    left, right, top, bottom = 72, 26, 30, 46
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_pos(time_ms: float) -> float:
        if tmax <= tmin:
            return left
        return left + (time_ms - tmin) / (tmax - tmin) * plot_w

    def y_pos(value: float) -> float:
        return top + plot_h - (value - vmin) / (vmax - vmin) * plot_h

    parts = [
        f'<svg class="plot" viewBox="0 0 {width} {height}" role="img" '
        'aria-labelledby="tran-title tran-desc">',
        '<title id="tran-title">Transient waveforms from ngspice</title>',
        '<desc id="tran-desc">Input and output voltage in millivolts versus '
        'time in milliseconds.</desc>',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" '
        f'fill="#f9fcfd" stroke="{GRID}"/>',
    ]
    for tick in _linear_ticks(vmin, vmax, 5):
        y = y_pos(tick)
        parts.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" '
            f'font-size="14" fill="{MUTED}">{tick:.0f}</text>'
        )
    for tick in _linear_ticks(tmin, tmax, 6):
        x = x_pos(tick)
        parts.append(
            f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_h}" '
            f'stroke="{GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{top + plot_h + 18:.1f}" text-anchor="middle" '
            f'font-size="13" fill="{MUTED}">{tick:.2f}</text>'
        )

    vin_points = [
        (x_pos(row["t_s"] * 1000.0), y_pos(row["vin_v"] * 1000.0)) for row in data
    ]
    vout_points = [
        (x_pos(row["t_s"] * 1000.0), y_pos(row["vout_v"] * 1000.0)) for row in data
    ]
    parts.append(_polyline(vin_points, TEAL))
    parts.append(_polyline(vout_points, ORANGE))
    parts.append(
        f'<text x="{left - 52}" y="{top + plot_h / 2:.1f}" font-size="14" '
        f'fill="{INK}" transform="rotate(-90 {left - 52} {top + plot_h / 2:.1f})">'
        'Voltage (mV)</text>'
    )
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 8}" text-anchor="middle" '
        f'font-size="14" fill="{INK}">Time (ms)</text>'
    )
    parts.append(
        f'<line x1="{left + 12}" y1="{top + 12}" x2="{left + 44}" y2="{top + 12}" '
        f'stroke="{TEAL}" stroke-width="3"/>'
    )
    parts.append(
        f'<text x="{left + 50}" y="{top + 16}" font-size="14" fill="{INK}">Vin</text>'
    )
    parts.append(
        f'<line x1="{left + 100}" y1="{top + 12}" x2="{left + 132}" y2="{top + 12}" '
        f'stroke="{ORANGE}" stroke-width="3"/>'
    )
    parts.append(
        f'<text x="{left + 138}" y="{top + 16}" font-size="14" fill="{INK}">Vout</text>'
    )
    parts.append("</svg>")
    return "".join(parts)
