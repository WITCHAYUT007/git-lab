import math

from flask import Flask, redirect, render_template, request, url_for

import spice_engine
from bjt import analyze_ce_bias, analyze_emitter_bias, analyze_fixed_bias
from charts import bode_svg, waveform_svg

FIELD_META = (
    ("vcc", "VCC", "V", "Supply Voltage"),
    ("r1", "R1", "Ω", "Upper Divider"),
    ("r2", "R2", "Ω", "Lower Divider"),
    ("rb", "RB", "Ω", "Base Resistor"),
    ("rc", "RC", "Ω", "Collector Resistor"),
    ("re", "RE", "Ω", "Emitter Resistor"),
    ("beta", "β", "", "Current Gain"),
    ("vbe", "VBE", "V", "Base–Emitter Voltage"),
)

FIELDS = tuple(name for name, _, _, _ in FIELD_META)

DEFAULTS = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rb": "1000000",
    "rc": "4700",
    "re": "1000",
    "beta": "150",
    "vbe": "0.7",
}

MODES = (
    ("divider", "Voltage Divider Bias"),
    ("fixed", "Fixed Bias"),
    ("emitter", "Emitter Bias"),
)

MODE_LABELS = dict(MODES)

MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "rc", "re", "beta", "vbe"),
}

SOLVERS = {
    "divider": analyze_ce_bias,
    "fixed": analyze_fixed_bias,
    "emitter": analyze_emitter_bias,
}

SIM_DEFAULTS = {
    "vcc": "12",
    "r1": "100000",
    "r2": "22000",
    "rc": "2200",
    "re": "1000",
    "rl": "10000",
    "cin_uf": "10",
    "cout_uf": "10",
    "amp_mv": "10",
    "freq_hz": "1000",
}

SIM_FIELDS = (
    ("vcc", "VCC", "V", "Supply voltage"),
    ("r1", "R1", "Ω", "Upper divider"),
    ("r2", "R2", "Ω", "Lower divider"),
    ("rc", "RC", "Ω", "Collector resistor"),
    ("re", "RE", "Ω", "Emitter resistor"),
    ("rl", "RL", "Ω", "AC load"),
    ("cin_uf", "Cin", "µF", "Input coupling"),
    ("cout_uf", "Cout", "µF", "Output coupling"),
    ("amp_mv", "Amplitude", "mV peak", "Source amplitude"),
    ("freq_hz", "Frequency", "Hz", "Source frequency"),
)


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(value):
        return "—"
    return f"{value:g}"


def _resistance(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(value):
        return "—"
    if value >= 1e6:
        return f"{value / 1e6:g} MΩ"
    if value >= 1e3:
        return f"{value / 1e3:g} kΩ"
    return f"{value:g} Ω"


def _display(form):
    return {
        "vcc": _number(form["vcc"]),
        "beta": _number(form["beta"]),
        "vbe": _number(form["vbe"]),
        "r1": _resistance(form["r1"]),
        "r2": _resistance(form["r2"]),
        "rb": _resistance(form["rb"]),
        "rc": _resistance(form["rc"]),
        "re": _resistance(form["re"]),
    }


def create_app():
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        form = dict(DEFAULTS)
        mode = "divider"
        result = None
        error = None

        if request.method == "POST":
            form = {name: request.form.get(name, "") for name in FIELDS}
            raw_mode = request.form.get("mode")
            action = request.form.get("action", "calculate")

            # A missing mode keeps Lab 2 behaviour. A present but unknown mode
            # is an error and must never fall through to the divider solver.
            if raw_mode not in (None, "") and raw_mode not in MODE_LABELS:
                error = (
                    f"Unknown bias mode {raw_mode!r}. "
                    "Choose Voltage Divider, Fixed, or Emitter Bias."
                )
            elif raw_mode in MODE_LABELS:
                mode = raw_mode

            if error is None and action == "mode":
                for name in MODE_FIELDS[mode]:
                    if not form[name].strip():
                        form[name] = DEFAULTS[name]
            elif error is None:
                try:
                    values = {
                        name: float(form[name]) for name in MODE_FIELDS[mode]
                    }
                except ValueError:
                    error = f"All {MODE_LABELS[mode]} inputs must be numbers."
                else:
                    try:
                        result = SOLVERS[mode](**values)
                    except ValueError as exc:
                        error = str(exc)

        return render_template(
            "index.html",
            form=form,
            result=result,
            error=error,
            fields=[meta for meta in FIELD_META if meta[0] in MODE_FIELDS[mode]],
            modes=MODES,
            mode=mode,
            mode_label=MODE_LABELS[mode],
            display=_display(form),
            sim=None,
            sim_form=dict(SIM_DEFAULTS),
            sim_error=None,
            sim_analysis="dc",
            sim_fields=SIM_FIELDS,
            analyses=spice_engine.ANALYSIS_LABELS,
        )

    @app.route("/simulate", methods=["GET", "POST"])
    def simulate():
        if request.method == "GET":
            return redirect(url_for("index"))

        form = {name: request.form.get(name, "") for name in SIM_DEFAULTS}
        analysis = request.form.get("analysis", "dc")
        sim = None
        sim_error = None

        if analysis not in spice_engine.ANALYSIS_LABELS:
            sim_error = f"Unknown analysis mode {analysis!r}. Choose DC, AC, or Transient."
        else:
            try:
                result = spice_engine.run(analysis, form)
            except spice_engine.SpiceError as exc:
                sim_error = str(exc)
            else:
                chart = None
                if result.ac is not None:
                    chart = bode_svg(result.ac)
                elif result.tran is not None:
                    chart = waveform_svg(result.tran)

                reference = None
                try:
                    reference = analyze_ce_bias(
                        float(form["vcc"]),
                        float(form["r1"]),
                        float(form["r2"]),
                        float(form["rc"]),
                        float(form["re"]),
                        100,
                        0.7,
                    )
                except (TypeError, ValueError):
                    reference = None

                if analysis == "dc":
                    metrics = [
                        ("VB", result.derived["vb_v"], "V"),
                        ("VE", result.derived["ve_v"], "V"),
                        ("VC", result.derived["vc_v"], "V"),
                        ("VCE", result.derived["vce_v"], "V"),
                        ("IC", result.derived["ic_ma"], "mA"),
                    ]
                    note = (
                        "SPICE uses the BJT model below; the Lab 3 reference "
                        "assumes fixed β = 100 and VBE = 0.70 V. Different "
                        "assumptions, so exact equality is not required."
                    )
                elif analysis == "ac":
                    metrics = [
                        ("Midband gain", result.derived["midband_gain_db"], "dB"),
                        ("Midband frequency", result.derived["midband_freq_hz"], "Hz"),
                        ("Lower cutoff fL", result.derived["f_low_hz"], "Hz"),
                        ("Upper cutoff fH", result.derived["f_high_hz"], "Hz"),
                    ]
                    note = (
                        "Gain = Vout(dB) − Vin(dB) measured at the source node "
                        "vin_s. Phase = Vout(deg) − Vin(deg)."
                    )
                else:
                    metrics = [
                        ("Vin peak", result.derived["vin_peak_mv"], "mV"),
                        ("Vout peak", result.derived["vout_peak_mv"], "mV"),
                        ("Correlation", result.derived["correlation"], ""),
                        ("Samples", result.derived["samples"], "points"),
                    ]
                    note = str(result.derived["phase_note"])

                sim = {
                    "result": result,
                    "chart": chart,
                    "reference": reference,
                    "analysis_label": spice_engine.ANALYSIS_LABELS[analysis],
                    "model": spice_engine.MODEL_NAME,
                    "model_line": spice_engine.MODEL_LINE,
                    "metrics": metrics,
                    "note": note,
                }

        legacy = dict(DEFAULTS)
        return render_template(
            "index.html",
            form=legacy,
            result=None,
            error=None,
            fields=[meta for meta in FIELD_META if meta[0] in MODE_FIELDS["divider"]],
            modes=MODES,
            mode="divider",
            mode_label=MODE_LABELS["divider"],
            display=_display(legacy),
            sim=sim,
            sim_form=form,
            sim_error=sim_error,
            sim_analysis=analysis,
            sim_fields=SIM_FIELDS,
            analyses=spice_engine.ANALYSIS_LABELS,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=False)
