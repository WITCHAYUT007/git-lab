import math

from flask import Flask, render_template, request

from bjt import analyze_ce_bias, analyze_emitter_bias, analyze_fixed_bias

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

        display = {
            "vcc": _number(form["vcc"]),
            "beta": _number(form["beta"]),
            "vbe": _number(form["vbe"]),
            "r1": _resistance(form["r1"]),
            "r2": _resistance(form["r2"]),
            "rb": _resistance(form["rb"]),
            "rc": _resistance(form["rc"]),
            "re": _resistance(form["re"]),
        }

        return render_template(
            "index.html",
            form=form,
            result=result,
            error=error,
            fields=[meta for meta in FIELD_META if meta[0] in MODE_FIELDS[mode]],
            modes=MODES,
            mode=mode,
            mode_label=MODE_LABELS[mode],
            display=display,
        )

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
