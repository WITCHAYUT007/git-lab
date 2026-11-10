from flask import Flask, render_template, request

from bjt import analyze_ce_bias

FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

DEFAULTS = {
    "vcc": "12",
    "r1": "47000",
    "r2": "10000",
    "rc": "4700",
    "re": "1000",
    "beta": "150",
    "vbe": "0.7",
}

FIELD_META = (
    ("vcc", "VCC", "V"),
    ("r1", "R1", "Ω"),
    ("r2", "R2", "Ω"),
    ("rc", "RC", "Ω"),
    ("re", "RE", "Ω"),
    ("beta", "β", ""),
    ("vbe", "VBE", "V"),
)


def create_app():
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        form = dict(DEFAULTS)
        result = None
        error = None

        if request.method == "POST":
            form = {name: request.form.get(name, "") for name in FIELDS}
            try:
                values = {name: float(form[name]) for name in FIELDS}
            except ValueError:
                error = "All inputs must be numbers."
            else:
                try:
                    result = analyze_ce_bias(**values)
                except ValueError as exc:
                    error = str(exc)

        return render_template(
            "index.html",
            form=form,
            result=result,
            error=error,
            fields=FIELD_META,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
