"""Thin adapter that runs the reference CE amplifier through external ngspice.

The Flask route validates and normalises every value before calling ``run()``.
This module owns the netlist, the subprocess call and the parsing of real
ngspice output. No result value is hard-coded here.
"""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORTABLE_EXE = ROOT / "tools" / "ngspice" / (
    "ngspice_con.exe" if os.name == "nt" else "ngspice"
)

MODEL_NAME = "QNPN_ENG29"
MODEL_LINE = ".model QNPN_ENG29 NPN (IS=1e-14 BF=100 VAF=100)"
ANALYSIS_LABELS = {
    "dc": "DC operating point (.op)",
    "ac": "AC frequency response (.ac)",
    "tran": "Transient waveform (.tran)",
}

NUMBER_RE = re.compile(r"^[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?$")


class SpiceError(Exception):
    """Raised for bad inputs, a failed run, or unreadable solver output."""


@dataclass(frozen=True)
class SpiceResult:
    analysis: str
    engine: str
    version: str
    netlist: str
    log_excerpt: str
    op: dict[str, float] | None
    ac: list[dict[str, float]] | None
    tran: list[dict[str, float]] | None
    derived: dict[str, float | str]


def find_engine() -> Path:
    """Locate ngspice without ever allowing a free-form command string."""
    override = os.environ.get("NGSPICE_EXE")
    if override:
        path = Path(override)
        if not path.is_file():
            raise SpiceError(f"NGSPICE_EXE does not point to a file: {override}")
        return path
    if PORTABLE_EXE.is_file():
        return PORTABLE_EXE
    for name in ("ngspice_con", "ngspice"):
        found = shutil.which(name)
        if found:
            return Path(found)
    raise SpiceError(
        "ngspice was not found. Put ngspice_con.exe in tools/ngspice/ "
        "or set the NGSPICE_EXE environment variable."
    )


@lru_cache(maxsize=4)
def engine_version(executable: str) -> str:
    try:
        proc = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    text = f"{proc.stdout}\n{proc.stderr}"
    match = re.search(r"ngspice-([\w.]+)", text)
    return match.group(1) if match else "unknown"


def validate(params: dict[str, object]) -> dict[str, float]:
    """Convert form text to checked floats; SPICE never sees raw strings."""
    limits = {
        "vcc": ("VCC", 1.0, 50.0),
        "r1": ("R1", 1.0, 1e7),
        "r2": ("R2", 1.0, 1e7),
        "rc": ("RC", 1.0, 1e7),
        "re": ("RE", 1.0, 1e7),
        "rl": ("RL", 1.0, 1e7),
        "cin_uf": ("Cin", 0.01, 1000.0),
        "cout_uf": ("Cout", 0.01, 1000.0),
        "amp_mv": ("Source amplitude", 0.1, 1000.0),
        "freq_hz": ("Source frequency", 10.0, 1e7),
    }
    checked: dict[str, float] = {}
    for name, (label, low, high) in limits.items():
        try:
            value = float(params.get(name, ""))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise SpiceError(f"{label} must be a number.")
        if not math.isfinite(value):
            raise SpiceError(f"{label} must be finite.")
        if not low <= value <= high:
            raise SpiceError(f"{label} must be between {low:g} and {high:g}.")
        checked[name] = value
    return checked


def build_netlist(params: dict[str, float], analysis: str) -> str:
    """Build one analysis-specific, checkpointed netlist."""
    if analysis not in ANALYSIS_LABELS:
        raise SpiceError(f"Unknown analysis mode {analysis!r}.")

    amp_v = params["amp_mv"] / 1000.0
    freq = params["freq_hz"]
    lines = [
        "* ENG29 Lab 04 - CE voltage-divider reference (unbypassed RE)",
        f"VCC vcc 0 DC {params['vcc']:g}",
        f"R1 vcc b {params['r1']:g}",
        f"R2 b 0 {params['r2']:g}",
        f"RC vcc c {params['rc']:g}",
        f"RE e 0 {params['re']:g}",
        f"Q1 c b e {MODEL_NAME}",
        f"CIN vin_s b {params['cin_uf']:g}u",
        f"VIN vin_s 0 AC {amp_v:g} SIN(0 {amp_v:g} {freq:g} 0 0)",
        f"COUT c vout {params['cout_uf']:g}u",
        f"RL vout 0 {params['rl']:g}",
        MODEL_LINE,
        ".op",
        ".save V(vin_s) V(vout) V(b) V(e) V(c)",
    ]
    if analysis == "ac":
        lines += [
            ".ac DEC 100 1 10MEG",
            ".print ac VDB(vout) VP(vout)",
            ".print ac VDB(vin_s) VP(vin_s)",
        ]
    elif analysis == "tran":
        tstop = 5.0 / freq
        tstep = tstop / 500.0
        lines += [
            f".tran {tstep:.6g} {tstop:.6g} 0",
            ".print tran V(vin_s) V(vout)",
        ]
    lines.append(".end")
    return "\n".join(lines) + "\n"


def _parse_op(log: str) -> dict[str, float] | None:
    lines = log.splitlines()
    start = None
    for index, line in enumerate(lines):
        if "Node" in line and "Voltage" in line:
            start = index + 1
            break
    if start is None:
        return None

    values: dict[str, float] = {}
    for line in lines[start:]:
        stripped = line.strip()
        if not stripped:
            if values:
                break
            continue
        if stripped.startswith("----") or stripped.lower().startswith("source"):
            if values:
                break
            continue
        parts = stripped.split()
        if len(parts) == 2 and NUMBER_RE.match(parts[1]):
            values[parts[0]] = float(parts[1])
    if not {"vcc", "b", "c", "e"}.issubset(values):
        return None
    return values


def _parse_print_blocks(log: str) -> dict[tuple[str, ...], list[list[float]]]:
    """Collect the paginated ``.print`` tables ngspice writes to the log."""
    blocks: dict[tuple[str, ...], list[list[float]]] = {}
    lines = log.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped.startswith("Index"):
            index += 1
            continue
        columns = tuple(stripped.split()[1:])
        rows: list[list[float]] = []
        cursor = index + 1
        while cursor < len(lines) and (
            not lines[cursor].strip() or lines[cursor].strip().startswith("----")
        ):
            cursor += 1
        while cursor < len(lines):
            item = lines[cursor].strip()
            if not item or item.startswith("----") or item.startswith("Index"):
                break
            parts = item.split()
            if len(parts) != len(columns) + 1:
                break
            try:
                row = [float(part) for part in parts]
            except ValueError:
                break
            rows.append(row)
            cursor += 1
        if rows:
            blocks.setdefault(columns, []).extend(rows)
        index = cursor if cursor > index + 1 else index + 1
    return blocks


def _crossing(
    rows: list[dict[str, float]], target: float, peak_freq: float
) -> tuple[float | None, float | None]:
    low = high = None
    for first, second in zip(rows[:-1], rows[1:]):
        a = first["gain_db"] - target
        b = second["gain_db"] - target
        if a == 0 or a * b < 0:
            ratio = -a / (b - a) if b != a else 0.0
            freq = math.exp(
                math.log(first["freq_hz"])
                + ratio * (math.log(second["freq_hz"]) - math.log(first["freq_hz"]))
            )
            if freq <= peak_freq:
                low = freq if low is None else min(low, freq)
            else:
                high = freq if high is None else max(high, freq)
    return low, high


def _parse_ac(
    log: str,
) -> tuple[list[dict[str, float]], dict[str, float | str]]:
    blocks = _parse_print_blocks(log)
    out_key = next((k for k in blocks if "vdb(vout)" in k), None)
    in_key = next((k for k in blocks if "vdb(vin_s)" in k), None)
    if out_key is None or in_key is None:
        raise SpiceError("AC print tables are missing from the ngspice log.")

    out_by_index = {int(row[0]): row for row in blocks[out_key]}
    rows: list[dict[str, float]] = []
    for vin_row in blocks[in_key]:
        out_row = out_by_index.get(int(vin_row[0]))
        if out_row is None:
            continue
        rows.append(
            {
                "freq_hz": float(vin_row[1]),
                "vin_db": float(vin_row[2]),
                "vin_deg": float(vin_row[3]),
                "vout_db": float(out_row[2]),
                "vout_deg": float(out_row[3]),
                "gain_db": float(out_row[2]) - float(vin_row[2]),
                "phase_deg": float(out_row[3]) - float(vin_row[3]),
            }
        )
    if not rows:
        raise SpiceError("AC output contained no paired frequency rows.")
    rows.sort(key=lambda row: row["freq_hz"])

    peak = max(rows, key=lambda row: row["gain_db"])
    low, high = _crossing(rows, peak["gain_db"] - 3.0, peak["freq_hz"])
    derived: dict[str, float | str] = {
        "midband_gain_db": round(peak["gain_db"], 3),
        "midband_freq_hz": round(peak["freq_hz"], 3),
        "f_low_hz": round(low, 3) if low is not None else "not determined in sweep range",
        "f_high_hz": round(high, 3) if high is not None else "not determined in sweep range",
    }
    return rows, derived


def _parse_tran(log: str) -> tuple[list[dict[str, float]], dict[str, float | str]]:
    blocks = _parse_print_blocks(log)
    key = next(
        (
            k
            for k in blocks
            if "time" in k and "v(vin_s)" in k and "v(vout)" in k
        ),
        None,
    )
    if key is None:
        raise SpiceError("Transient print table is missing from the ngspice log.")
    rows = [
        {"t_s": float(row[1]), "vin_v": float(row[2]), "vout_v": float(row[3])}
        for row in blocks[key]
    ]
    if len(rows) < 10:
        raise SpiceError("Transient output contained too few samples.")

    vin = [row["vin_v"] for row in rows]
    vout = [row["vout_v"] for row in rows]
    vin_mean = sum(vin) / len(vin)
    vout_mean = sum(vout) / len(vout)
    covariance = sum((a - vin_mean) * (b - vout_mean) for a, b in zip(vin, vout))
    vin_var = sum((a - vin_mean) ** 2 for a in vin)
    vout_var = sum((b - vout_mean) ** 2 for b in vout)
    correlation = (
        covariance / math.sqrt(vin_var * vout_var)
        if vin_var > 0 and vout_var > 0
        else 0.0
    )
    if correlation < -0.3:
        phase_note = "inverted (~180 deg): vout falls when vin rises"
    elif correlation > 0.3:
        phase_note = "non-inverted: vout follows vin"
    else:
        phase_note = "phase relation not determined from correlation"
    derived: dict[str, float | str] = {
        "vin_peak_mv": round((max(vin) - min(vin)) / 2 * 1000, 3),
        "vout_peak_mv": round((max(vout) - min(vout)) / 2 * 1000, 3),
        "correlation": round(correlation, 4),
        "phase_note": phase_note,
        "samples": len(rows),
    }
    return rows, derived


def _error_excerpt(log: str) -> str:
    lines = [line.strip() for line in log.splitlines() if line.strip()]
    errors = [line for line in lines if "error" in line.lower() or "aborted" in line.lower()]
    if errors:
        return " | ".join(errors[:4])
    return " | ".join(lines[-4:]) or "ngspice produced an empty log."


def run(analysis: str, params: dict[str, object]) -> SpiceResult:
    """Run one real ngspice batch analysis and parse its printed output."""
    if analysis not in ANALYSIS_LABELS:
        raise SpiceError(
            f"Unknown analysis {analysis!r}. Choose dc, ac, or tran."
        )
    checked = validate(params)
    executable = find_engine()
    version = engine_version(str(executable))
    netlist = build_netlist(checked, analysis)

    with tempfile.TemporaryDirectory(prefix="lab04_ngspice_") as folder:
        work = Path(folder)
        circuit = work / "ce.cir"
        log_path = work / "run.log"
        circuit.write_text(netlist, encoding="ascii")
        command = [str(executable), "-b", "-o", str(log_path), str(circuit)]
        try:
            proc = subprocess.run(
                command,
                cwd=work,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise SpiceError("ngspice timed out after 30 seconds.") from None
        except OSError as exc:
            raise SpiceError(f"Could not start ngspice: {exc}") from None
        log_text = (
            log_path.read_text(encoding="utf-8", errors="replace")
            if log_path.is_file()
            else f"{proc.stdout}\n{proc.stderr}"
        )

    if proc.returncode != 0 or re.search(
        r"(?:^|\n)\s*(?:Error:|Simulation interrupted|run simulation\(s\) aborted)",
        log_text,
    ):
        raise SpiceError(_error_excerpt(log_text))

    op = _parse_op(log_text)
    ac = None
    tran = None
    derived: dict[str, float | str] = {}
    if analysis == "dc":
        if op is None:
            raise SpiceError("The .op operating-point table is missing.")
        current_ma = (op["vcc"] - op["c"]) / checked["rc"] * 1000.0
        derived = {
            "vb_v": round(op["b"], 6),
            "ve_v": round(op["e"], 6),
            "vc_v": round(op["c"], 6),
            "vce_v": round(op["c"] - op["e"], 6),
            "ic_ma": round(current_ma, 6),
        }
    elif analysis == "ac":
        ac, derived = _parse_ac(log_text)
    else:
        tran, derived = _parse_tran(log_text)

    return SpiceResult(
        analysis=analysis,
        engine=str(executable),
        version=version,
        netlist=netlist,
        log_excerpt=log_text[-4000:],
        op=op,
        ac=ac,
        tran=tran,
        derived=derived,
    )
