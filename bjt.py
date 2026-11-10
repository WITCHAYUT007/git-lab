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

RESULT_FIELDS = ("ib_a", "ic_a", "ie_a", "vb_v", "vc_v", "ve_v", "vce_v")


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


def _solve_nodal(vcc, r1, r2, rc, re, beta, vbe):
    """Solve the same DC point by nodal analysis, without Thevenin reduction."""
    a11 = 1 / r1 + 1 / r2 + 1 / ((beta + 1) * re)
    b1 = vcc / r1 + vbe / ((beta + 1) * re)
    vb = b1 / a11
    ib = (vb - vbe) / ((beta + 1) * re)
    ic = beta * ib
    ie = (beta + 1) * ib
    ve = ie * re
    vc = vcc - ic * rc
    vce = vc - ve
    return {
        "ib_a": ib,
        "ic_a": ic,
        "ie_a": ie,
        "vb_v": vb,
        "vc_v": vc,
        "ve_v": ve,
        "vce_v": vce,
    }


def _worst_residual(vcc, r1, r2, rc, re, beta, vbe, values):
    """Worst KCL/model residual of a solved point, in amps or volts."""
    residuals = (
        (values["vb_v"] - vcc) / r1 + values["vb_v"] / r2 + values["ib_a"],
        (values["vc_v"] - vcc) / rc + values["ic_a"],
        values["ie_a"] * re - values["ve_v"],
        values["vb_v"] - values["ve_v"] - vbe,
        values["ic_a"] - beta * values["ib_a"],
        values["ie_a"] - (beta + 1) * values["ib_a"],
    )
    return max(abs(value) for value in residuals)


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

    thevenin = {
        "ib_a": ib,
        "ic_a": ic,
        "ie_a": ie,
        "vb_v": vb,
        "vc_v": vc,
        "ve_v": ve,
        "vce_v": vce,
    }
    nodal = _solve_nodal(vcc, r1, r2, rc, re, beta, vbe)
    residual = _worst_residual(vcc, r1, r2, rc, re, beta, vbe, thevenin)
    check_delta = max(
        max(abs(nodal[k] - thevenin[k]) for k in RESULT_FIELDS),
        residual,
    )
    scale = max(abs(thevenin[k]) for k in RESULT_FIELDS)
    check_passed = check_delta <= 1e-6 * max(1.0, scale)

    if vbb <= vbe:
        return BiasResult(
            ib_a=0.0,
            ic_a=0.0,
            ie_a=0.0,
            vb_v=vbb,
            vc_v=vcc,
            ve_v=0.0,
            vce_v=vcc,
            region="cutoff",
            warnings=(
                "Transistor is cut off; linear active-region model does not apply.",
            ),
            check_passed=check_passed,
            check_delta=check_delta,
        )

    if vce <= 0.2:
        region = "saturation"
        warnings = (
            "Predicted VCE is below VCE(sat); transistor saturates and the model is not valid.",
        )
    else:
        region = "active"
        warnings = ()

    return BiasResult(
        ib_a=ib,
        ic_a=ic,
        ie_a=ie,
        vb_v=vb,
        vc_v=vc,
        ve_v=ve,
        vce_v=vce,
        region=region,
        warnings=warnings,
        check_passed=check_passed,
        check_delta=check_delta,
    )
