# BJT Common-Emitter DC Bias Web App — Design

- **Date:** 2026-11-10
- **Course:** ENG29 2121 (lab)
- **Status:** Approved by lab owner (chat, 2026-11-10)

## Intent

Deliver the smallest working Flask application that computes the DC operating
point of a voltage-divider-biased common-emitter (CE) stage. The app must show
results with units, validate input, warn when the transistor is outside the
active region, and cross-check its answer with an independent engineering
calculation. It must run on localhost and be committed to GitHub today.

## Goals

- Seven inputs: `VCC`, `R1`, `R2`, `RC`, `RE`, `beta`, `VBE`.
- DC operating point: `IB`, `IC`, `IE`, `VB`, `VC`, `VE`, `VCE` with units.
- Input validation with readable inline errors (never a traceback).
- Region classification (active / cutoff / saturation) with warnings.
- Independent cross-check (nodal analysis) shown on the results page.
- Separate Python logic, Flask routes, templates, CSS, and tests.

## Non-goals

- AC analysis, transient analysis, frequency response.
- Full circuit editor, schematic capture, netlists.
- FET/MOSFET devices.
- Persistence, database, authentication, JavaScript.

## Anti-goals

- Returning physically wrong numbers without a warning.
- Crashing or showing a stack trace on bad input.
- Requiring anything beyond `pip install -r requirements.txt` to run.

## Constraints

- Python 3.10.11, pip 23.0.1 (Flask not yet installed).
- Flask for the web layer; stdlib `unittest` for tests (matches the existing repo).
- One page, server-rendered, no JavaScript.
- UI text in English.

## Approaches Considered

| Approach | Trade-off | Verdict |
| --- | --- | --- |
| A. Server-rendered Flask, one POST route, logic in its own module | Smallest real Flask app; fully testable without a browser | **Chosen** |
| B. Client-side JavaScript calculator | Fails the "real Flask application" deliverable | Rejected |
| C. Flask JSON API + `fetch` front-end | Extra moving parts for a single form; harder to test | Rejected |

## Engineering Specification

### Inputs and validation

| Input | Unit | Rule |
| --- | --- | --- |
| `VCC` | V | finite number, `> 0` |
| `R1`, `R2`, `RC`, `RE` | Ω | finite number, `> 0` |
| `beta` | — | finite number, `> 0` |
| `VBE` | V | finite number, `0 < VBE < VCC` |

Booleans are not numbers. All errors raise `ValueError` with a readable message
from `bjt.py`; the Flask layer catches them and renders them inline.

### Primary calculation (Thevenin reduction)

```
VBB = VCC * R2 / (R1 + R2)
RB  = R1 * R2 / (R1 + R2)
IB  = (VBB - VBE) / (RB + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VC  = VCC - IC * RC
VB  = VBE + VE
VCE = VC - VE
```

### Independent calculation (nodal analysis)

Solve for node voltages `VB`, `VC` directly, without the Thevenin reduction:

```
(1) (VB - VCC)/R1 + VB/R2 + (VB - VBE)/((beta+1)*RE) = 0
(2) (VC - VCC)/RC + beta*(VB - VBE)/((beta+1)*RE)    = 0
```

This is a 2x2 linear system, solved in closed form. Then `IB =
(VB - VBE)/((beta+1)*RE)`, `IC = beta*IB`, `IE = (beta+1)*IB`, and the node
voltages come straight from the solution.

The comparison runs on the **raw linear solution**, before any region
clamping, using a relative tolerance of `1e-6`. The result page shows
`PASS`/`FAIL` and the absolute difference for the worst node/current.

### Region rules (applied after the comparison)

| Condition | Region | Displayed values | Warning |
| --- | --- | --- | --- |
| `VBB <= VBE` | cutoff | `IB = IC = IE = 0`, `VE = 0`, `VB = VBB`, `VC = VCC`, `VCE = VCC` | "Transistor is cut off; linear active-region model does not apply." |
| `VCE <= 0.2 V` | saturation | raw linear-model values | "Predicted VCE is below VCE(sat); transistor saturates and the model is not valid." |
| otherwise | active | raw linear-model values | none |

### Reference vector (hand-checked)

`VCC=12 V, R1=47 kΩ, R2=10 kΩ, RC=4.7 kΩ, RE=1 kΩ, beta=150, VBE=0.7 V`

```
VBB = 2.1053 V    RB = 8.2456 kΩ
IB  = 8.825 µA    IC = 1.3237 mA   IE = 1.3326 mA
VB  = 2.0325 V    VC = 5.7785 V    VE = 1.3326 V   VCE = 4.4459 V
region = ACTIVE   independent check = PASS
```

This vector is asserted in `tests/test_bjt.py`.

### Outputs

- `IB` in µA, `IC` and `IE` in mA (3 decimals).
- `VB`, `VC`, `VE`, `VCE` in V (3 decimals).
- Region badge and warning list.
- Independent-check status and delta.

## Application Structure

```
app.py                    Flask app, GET/POST "/"
bjt.py                    engineering logic, no Flask imports
templates/base.html       page layout
templates/index.html      input form, results, warnings
static/style.css          styling
tests/test_bjt.py         engineering logic and reference vectors
tests/test_app.py         routes, validation, rendering
requirements.txt          Flask
README.md                 setup, run, test, reference example
```

### Routes

- `GET /` — render the form with defaults: `12, 47000, 10000, 4700, 1000, 150, 0.7`.
- `POST /` — validate, analyze, render the same page with results/errors and
  the submitted values. Always HTTP 200 so the form stays usable (no redirect,
  no session/flash dependency).

### `bjt.py` public surface

```python
@dataclass(frozen=True)
class BiasResult:
    ib_a: float; ic_a: float; ie_a: float
    vb_v: float; vc_v: float; ve_v: float; vce_v: float
    region: str                 # "active" | "cutoff" | "saturation"
    warnings: tuple[str, ...]
    check_passed: bool
    check_delta: float

def analyze_ce_bias(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult: ...
```

## UI Sketch

```
┌ BJT Common-Emitter DC Bias ─────────────────────┐
│ VCC[12] R1[47000] R2[10000] RC[4700]            │
│ RE[1000] β[150] VBE[0.7]          [Calculate]   │
├─────────────────────────────────────────────────┤
│ ● ACTIVE                                        │
│ IB 8.83 µA   IC 1.324 mA   IE 1.333 mA          │
│ VB 2.03 V    VC 5.78 V     VE 1.33 V            │
│ VCE 4.45 V                                      │
│ Independent check: PASS (Δ = 2e-13)             │
│ ⚠ warnings appear here                          │
└─────────────────────────────────────────────────┘
```

## Tests

`tests/test_bjt.py`
- Reference vector above (all values, within 1e-3 relative / 1e-6 absolute).
- A second valid vector in the active region.
- Cutoff case clamps currents and warns.
- Saturation case reports raw values and warns.
- Thevenin vs nodal agreement on both valid vectors.
- Validation: non-numeric, bool, NaN/inf, `VCC<=0`, any `R<=0`, `beta<=0`,
  `VBE<=0`, `VBE>=VCC`.

`tests/test_app.py`
- `GET /` returns 200 and contains the form fields.
- `POST /` with the reference vector shows mA/V values and `PASS`.
- `POST /` with invalid input shows an error message and no traceback (200).
- `POST /` cutoff case shows the cutoff warning.

Run with `python -m unittest -v`.

## Running

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py            # http://127.0.0.1:5000
```

## Git

Small lab change on a clean, in-sync `main`; work directly on `main` rather
than a worktree. Commits: design doc, then the app (logic + web + tests),
then README. Push to `origin/main` if credentials allow.

## Left to the Builder

- Exact CSS styling and spacing.
- Wording of validation messages (must stay specific to the field).
- Decimal formatting edge cases (very small/large values).
- README phrasing; keep the reference example.
