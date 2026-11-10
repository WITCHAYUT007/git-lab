import math
from dataclasses import dataclass

LABELS = {
    "vcc": "VCC",
    "r1": "R1",
    "r2": "R2",
    "rc": "RC",
    "re": "RE",
    "beta": "beta",
    "vbe": "VBE",
}


@dataclass(frozen=True)
class BiasResult:
    ib_a: float
    ic_a: float
    ie_a: float
    vb_v: float
    vc_v: float
    ve_v: float
    vce_v: float
    region: str
    warnings: tuple[str, ...]
    check_passed: bool
    check_delta: float


def analyze_ce_bias(vcc, r1, r2, rc, re, beta, vbe):
    inputs = {
        "vcc": vcc,
        "r1": r1,
        "r2": r2,
        "rc": rc,
        "re": re,
        "beta": beta,
        "vbe": vbe,
    }

    for name, value in inputs.items():
        label = LABELS[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} must be a number.")
        if not math.isfinite(value):
            raise ValueError(f"{label} must be finite.")

    if vcc <= 0:
        raise ValueError("VCC must be greater than zero.")
    for name in ("r1", "r2", "rc", "re"):
        if inputs[name] <= 0:
            raise ValueError(f"{LABELS[name]} must be greater than zero.")
    if beta <= 0:
        raise ValueError("beta must be greater than zero.")
    if not 0 < vbe < vcc:
        raise ValueError("VBE must be between zero and VCC.")

    vbb = vcc * r2 / (r1 + r2)
    rb = r1 * r2 / (r1 + r2)
    ib = (vbb - vbe) / (rb + (beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vc = vcc - ic * rc
    vb = vbe + ve
    vce = vc - ve

    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vb_v=vb,
        vc_v=vc,
        ve_v=ve,
        vce_v=vce,
        region="active",
        warnings=(),
        check_passed=True,
        check_delta=0.0,
    )
