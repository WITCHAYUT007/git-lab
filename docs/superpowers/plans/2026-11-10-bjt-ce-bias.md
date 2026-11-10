# BJT Common-Emitter DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the smallest working Flask app that computes and cross-checks the DC operating point of a voltage-divider-biased common-emitter stage.

**Architecture:** All engineering math lives in `bjt.py` with no Flask imports. `app.py` is a thin single-route Flask layer that parses/validates the form and renders `templates/index.html`. Server-rendered HTML with one CSS file; no JavaScript, no database.

**Tech Stack:** Python 3.10.11, Flask 3.x, stdlib `unittest`, HTML/CSS.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-ce-bias-design.md`

## Global Constraints

- Python 3.10.11; `Flask>=3.0,<4.0` is the only third-party dependency; tests use stdlib `unittest` only.
- One page, server-rendered; no JavaScript, no storage, no authentication.
- Scope is DC bias only: no AC, transient, circuit editor, or FET.
- UI text is English. Result units: `IB` in µA, `IC`/`IE` in mA, voltages in V, 3 decimals.
- Public inputs, exactly: `vcc`, `r1`, `r2`, `rc`, `re`, `beta`, `vbe` (all float, ohms for resistors).
- Form defaults: `12`, `47000`, `10000`, `4700`, `1000`, `150`, `0.7`.
- `analyze_ce_bias` raises `ValueError` for every invalid input (including wrong types and bools); non-finite numbers are invalid.
- Independent check tolerance: `check_delta <= 1e-6 * max(1.0, max(abs(raw values)))`.
- `POST /` always returns HTTP 200; validation errors render inline, never a traceback or redirect.
- Every commit must leave the full suite green: `.venv\Scripts\python -m unittest discover -v`.
- `tests/` is an importable package (empty `tests/__init__.py`); otherwise Python 3.10 discovery silently reports 0 tests.

## Review Focus

1. **Empty or non-numeric form field** — must show a readable inline error on a 200 response, never a 500 or traceback. (Test in Task 4.)
2. **`VBE >= VCC`** — must be rejected with a `VBE` message; no negative/invalid solve. (Test in Task 1.)
3. **`beta <= 0` or any resistor `<= 0`** — rejected with a field-specific message, not a `ZeroDivisionError`. (Test in Task 1.)
4. **Cutoff boundary `VBB == VBE`** — classified cutoff with zero currents and finite node voltages, no NaN. (Test in Task 3.)
5. **Saturation boundary around `VCE = 0.2 V`** — just above stays active, at/below becomes saturation. (Test in Task 3.)

---

### Task 1: Engineering Core — Validation, Thevenin Solve, Active Result

**Files:**
- Create: `bjt.py`
- Create: `tests/__init__.py` (empty package marker; without it `unittest discover` silently finds 0 tests on Python 3.10)
- Create: `tests/test_bjt.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  @dataclass(frozen=True)
  class BiasResult:
      ib_a: float; ic_a: float; ie_a: float
      vb_v: float; vc_v: float; ve_v: float; vce_v: float
      region: str                # lowercase: "active" | "cutoff" | "saturation"
      warnings: tuple[str, ...]
      check_passed: bool
      check_delta: float

  def analyze_ce_bias(vcc, r1, r2, rc, re, beta, vbe) -> BiasResult
  ```
  In this task `region` is always `"active"`, `warnings` is `()`, `check_passed` is
  `True`, and `check_delta` is `0.0`; Task 2 replaces the check fields and Task 3
  replaces the region fields.

- [ ] **Step 0: Create the virtual environment (once)**

Run: `python -m venv .venv`
Expected: `.venv\` appears; no output.

- [ ] **Step 1: Write the failing test**

Create an empty `tests/__init__.py`, then create `tests/test_bjt.py`:

```python
import unittest

from bjt import analyze_ce_bias

REF1 = dict(vcc=12, r1=47000, r2=10000, rc=4700, re=1000, beta=150, vbe=0.7)
REF2 = dict(vcc=15, r1=33000, r2=6800, rc=2200, re=470, beta=200, vbe=0.65)


class TestActivePoint(unittest.TestCase):
    def test_reference_vector(self):
        r = analyze_ce_bias(**REF1)
        self.assertAlmostEqual(r.ib_a, 8.824501e-6, delta=1e-9)
        self.assertAlmostEqual(r.ic_a, 1.323675e-3, delta=1e-9)
        self.assertAlmostEqual(r.ie_a, 1.332500e-3, delta=1e-9)
        self.assertAlmostEqual(r.vb_v, 2.032500, delta=1e-6)
        self.assertAlmostEqual(r.vc_v, 5.778726, delta=1e-6)
        self.assertAlmostEqual(r.ve_v, 1.332500, delta=1e-6)
        self.assertAlmostEqual(r.vce_v, 4.446227, delta=1e-6)
        self.assertEqual(r.region, "active")
        self.assertEqual(r.warnings, ())
        self.assertTrue(r.check_passed)

    def test_second_reference_vector(self):
        r = analyze_ce_bias(**REF2)
        self.assertAlmostEqual(r.ic_a, 3.821494e-3, delta=1e-9)
        self.assertAlmostEqual(r.vce_v, 4.787631, delta=1e-6)
        self.assertEqual(r.region, "active")


class TestValidation(unittest.TestCase):
    def test_non_numeric_and_bool(self):
        with self.assertRaises(ValueError):
            analyze_ce_bias("12", 47000, 10000, 4700, 1000, 150, 0.7)
        with self.assertRaises(ValueError):
            analyze_ce_bias(True, 47000, 10000, 4700, 1000, 150, 0.7)

    def test_non_finite(self):
        for value in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                analyze_ce_bias(value, 47000, 10000, 4700, 1000, 150, 0.7)

    def test_vcc_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "VCC"):
            analyze_ce_bias(0, 47000, 10000, 4700, 1000, 150, 0.7)

    def test_resistors_must_be_positive(self):
        for field in ("r1", "r2", "rc", "re"):
            with self.subTest(field=field):
                args = dict(REF1, **{field: 0})
                with self.assertRaisesRegex(ValueError, field.upper()):
                    analyze_ce_bias(**args)

    def test_beta_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "beta"):
            analyze_ce_bias(**dict(REF1, beta=0))

    def test_vbe_must_be_between_zero_and_vcc(self):
        for vbe in (0, 12, -0.7):
            with self.subTest(vbe=vbe):
                with self.assertRaisesRegex(ValueError, "VBE"):
                    analyze_ce_bias(**dict(REF1, vbe=vbe))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt'`.

- [ ] **Step 3: Implement `bjt.py`**

In `bjt.py`, `analyze_ce_bias` validates all seven inputs in this order: numeric and not bool,
finite, `vcc > 0`, each resistor `> 0`, `beta > 0`, `0 < vbe < vcc`. Messages name
the field, e.g. `"R1 must be greater than zero."` and
`"VBE must be between zero and VCC."`.

Compute the raw point with the Thevenin reduction exactly as the spec states:

```
vbb = vcc * r2 / (r1 + r2)
rb  = r1 * r2 / (r1 + r2)
ib  = (vbb - vbe) / (rb + (beta + 1) * re)
ic  = beta * ib
ie  = (beta + 1) * ib
ve  = ie * re
vc  = vcc - ic * rc
vb  = vbe + ve
vce = vc - ve
```

Return `BiasResult` with those values, `region="active"`, `warnings=()`,
`check_passed=True`, `check_delta=0.0`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: PASS (all Task 1 tests; existing `test_electrical` still passes).

- [ ] **Step 5: Commit**

```bash
git add bjt.py tests/__init__.py tests/test_bjt.py
git commit -m "feat: solve CE bias operating point"
```

---

### Task 2: Independent Nodal Cross-Check

**Files:**
- Modify: `bjt.py`
- Modify: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `BiasResult`, `analyze_ce_bias` from Task 1.
- Produces: `_solve_nodal(vcc, r1, r2, rc, re, beta, vbe) -> dict[str, float]`
  with keys `ib_a`, `ic_a`, `ie_a`, `vb_v`, `vc_v`, `ve_v`, `vce_v`;
  `analyze_ce_bias` now fills `check_passed` and `check_delta`.

- [ ] **Step 1: Write the failing test**

Add `_solve_nodal` to the existing import, then append to `tests/test_bjt.py`:

```python
from bjt import _solve_nodal, analyze_ce_bias  # replace the existing import line


class TestIndependentCheck(unittest.TestCase):
    def test_nodal_matches_displayed_point(self):
        for ref in (REF1, REF2):
            with self.subTest(ref=ref):
                r = analyze_ce_bias(**ref)
                n = _solve_nodal(**ref)
                self.assertAlmostEqual(n["ic_a"], r.ic_a, delta=1e-9)
                self.assertAlmostEqual(n["vce_v"], r.vce_v, delta=1e-9)

    def test_check_fields_are_computed(self):
        r = analyze_ce_bias(**REF1)
        self.assertTrue(r.check_passed)
        self.assertLess(r.check_delta, 1e-9)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: FAIL — `ImportError: cannot import name '_solve_nodal' from 'bjt'`.

- [ ] **Step 3: Implement `_solve_nodal` and wire the comparison**

Add a private function returning a dict with keys `ib_a`, `ic_a`, `ie_a`,
`vb_v`, `vc_v`, `ve_v`, `vce_v`, solved directly from the nodal equations
(no Thevenin reduction):

```
a11 = 1/r1 + 1/r2 + 1/((beta+1)*re)
b1  = vcc/r1 + vbe/((beta+1)*re)
vb  = b1 / a11
ib  = (vb - vbe) / ((beta+1)*re)
ic  = beta * ib
ie  = (beta + 1) * ib
ve  = ie * re
vc  = vcc - ic * rc
vce = vc - ve
```

In `analyze_ce_bias`, after computing the Thevenin values, compute the nodal
values and:

```
check_delta  = max(abs(nodal[k] - thevenin[k]) for k in the seven keys)
scale        = max(abs(thevenin[k]) for k in the seven keys)
check_passed = check_delta <= 1e-6 * max(1.0, scale)
```

Set these on the returned `BiasResult`. Do not alter the Thevenin values from
Task 1.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bjt.py tests/test_bjt.py
git commit -m "feat: add independent nodal cross-check"
```

---

### Task 3: Region Rules — Cutoff and Saturation

**Files:**
- Modify: `bjt.py`
- Modify: `tests/test_bjt.py`

**Interfaces:**
- Consumes: `analyze_ce_bias` from Task 2.
- Produces: `analyze_ce_bias` sets `region` to `"active"`, `"cutoff"`, or
  `"saturation"` and fills `warnings`; clamping happens only in the returned
  results, never in the raw cross-check.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_bjt.py`:

```python
import math


class TestRegions(unittest.TestCase):
    def test_cutoff_clamps_currents(self):
        r = analyze_ce_bias(12, 100000, 1000, 4700, 1000, 100, 0.7)
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib_a, r.ic_a, r.ie_a), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(r.ve_v, 0.0)
        self.assertAlmostEqual(r.vb_v, 0.118811881, delta=1e-9)
        self.assertAlmostEqual(r.vc_v, 12.0)
        self.assertAlmostEqual(r.vce_v, 12.0)
        self.assertEqual(len(r.warnings), 1)
        self.assertTrue(r.check_passed)

    def test_cutoff_boundary_is_inclusive(self):
        r = analyze_ce_bias(1.4, 10000, 10000, 1000, 100, 100, 0.7)
        self.assertEqual(r.region, "cutoff")
        self.assertEqual(r.ic_a, 0.0)
        for value in (r.ib_a, r.ie_a, r.vb_v, r.vc_v, r.ve_v, r.vce_v):
            self.assertTrue(math.isfinite(value))

    def test_saturation_reports_raw_values(self):
        r = analyze_ce_bias(12, 10000, 10000, 200, 100, 150, 0.7)
        self.assertEqual(r.region, "saturation")
        self.assertAlmostEqual(r.vce_v, 0.107960199, delta=1e-6)
        self.assertEqual(len(r.warnings), 1)
        self.assertTrue(r.check_passed)

    def test_saturation_boundary(self):
        active = analyze_ce_bias(12, 10000, 10000, 197, 100, 150, 0.7)
        saturated = analyze_ce_bias(12, 10000, 10000, 198, 100, 150, 0.7)
        self.assertEqual(active.region, "active")
        self.assertEqual(saturated.region, "saturation")

    def test_extreme_valid_values_stay_finite(self):
        r = analyze_ce_bias(12, 1, 1, 1, 1, 1, 0.5)
        for value in (r.ib_a, r.ic_a, r.ie_a, r.vb_v, r.vc_v, r.ve_v, r.vce_v):
            self.assertTrue(math.isfinite(value))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: FAIL — `test_cutoff_clamps_currents` gets `"active"` instead of `"cutoff"`.

- [ ] **Step 3: Apply region rules**

In `analyze_ce_bias`, after the raw solve and the cross-check:

- If `vbb <= vbe` (cutoff): return `ib_a=ic_a=ie_a=0.0`, `ve_v=0.0`,
  `vb_v=vbb`, `vc_v=vcc`, `vce_v=vcc`, `region="cutoff"`, and one warning:
  `"Transistor is cut off; linear active-region model does not apply."`
- Else if raw `vce <= 0.2` (saturation): keep the raw values,
  `region="saturation"`, and one warning:
  `"Predicted VCE is below VCE(sat); transistor saturates and the model is not valid."`
- Else: `region="active"`, `warnings=()`, raw values.

Keep the `check_*` fields computed from the raw values in every branch.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add bjt.py tests/test_bjt.py
git commit -m "feat: classify cutoff and saturation regions"
```

---

### Task 4: Flask Page — Form, Results, Styles

**Files:**
- Create: `requirements.txt`
- Create: `app.py`
- Create: `templates/base.html`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_app.py`

**Interfaces:**
- Consumes: `analyze_ce_bias`, `BiasResult` from Task 3.
- Produces: `create_app() -> Flask` and module-level `app = create_app()`; route `GET/POST /`.

- [ ] **Step 1: Create `requirements.txt` and install**

```
Flask>=3.0,<4.0
```

Run: `.venv\Scripts\python -m pip install -r requirements.txt`
Expected: `Successfully installed ... flask ...`

- [ ] **Step 2: Write the failing test**

Create `tests/test_app.py`:

```python
import unittest

from app import create_app

REF1 = dict(vcc=12, r1=47000, r2=10000, rc=4700, re=1000, beta=150, vbe=0.7)


class TestPages(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_renders_form_defaults(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        for field in (b'name="vcc"', b'name="r1"', b'name="r2"',
                      b'name="rc"', b'name="re"', b'name="beta"', b'name="vbe"'):
            self.assertIn(field, resp.data)
        self.assertIn(b"47000", resp.data)

    def test_post_reference_vector(self):
        resp = self.client.post("/", data=REF1)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"ACTIVE", resp.data)
        self.assertIn(b"1.324", resp.data)
        self.assertIn(b"mA", resp.data)
        self.assertIn(b"4.446", resp.data)
        self.assertIn(b"PASS", resp.data)

    def test_post_non_numeric_or_empty_is_inline_error(self):
        for bad in ("abc", ""):
            with self.subTest(value=bad):
                resp = self.client.post("/", data=dict(REF1, vcc=bad))
                self.assertEqual(resp.status_code, 200)
                self.assertIn(b"number", resp.data)
                self.assertNotIn(b"Traceback", resp.data)

    def test_post_invalid_vbe_is_inline_error(self):
        resp = self.client.post("/", data=dict(REF1, vbe="12"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"VBE", resp.data)

    def test_post_cutoff_warning(self):
        data = dict(vcc=12, r1=100000, r2=1000, rc=4700, re=1000,
                    beta=100, vbe=0.7)
        resp = self.client.post("/", data=data)
        self.assertIn(b"cut off", resp.data)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`.

- [ ] **Step 4: Implement the Flask layer and page**

`app.py`: module-level `FIELDS` tuple and `DEFAULTS` dict with the spec's
default strings. `create_app()` defines one route:

- `GET /`: render `index.html` with `form=DEFAULTS`, `result=None`, `error=None`.
- `POST /`: take submitted strings for all seven fields; convert with `float`.
  If conversion fails, `error = "All inputs must be numbers."`. Otherwise call
  `analyze_ce_bias(**values)` and catch `ValueError` into `error`. Always
  return `render_template(...)` with status 200, preserving submitted values.

`templates/index.html`: a `<form method="post">` with a labelled number input
per field (`step="any"`, `required`); a Calculate submit button; if `error`,
show it in `<p class="error">`; if `result`, show a region badge
(`{{ result.region|upper }}`, class `region-{{ result.region }}`), a results
table with unit formatting — `ib_a*1e6` µA, `ic_a*1e3` and `ie_a*1e3` mA,
voltages 3 decimals V — the independent check as `PASS`/`FAIL` with
`"%.2e"|format(result.check_delta)`, and every warning in a list. Keep the top
of the page noting the model is DC, linear, active-region.

`templates/base.html`: HTML5 skeleton, `<meta charset="utf-8">`, links
`static/style.css`, and a `{% block content %}{% endblock %}`.

`static/style.css`: readable single-column layout; `.error` in red; region
badge colours for `.region-active`, `.region-cutoff`, `.region-saturation`.

- [ ] **Step 5: Run test to verify it passes**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: PASS (all suites).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt app.py templates static tests/test_app.py
git commit -m "feat: add Flask bias calculator page"
```

---

### Task 5: README, End-to-End Demo, Push

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: everything above.
- Produces: user-facing setup/run/test instructions and the reference example.

- [ ] **Step 1: Rewrite `README.md`**

Remove the existing merge-conflict debris (`DC Circuit Calculatorgit push -u
origin main`, the stray `=======`). Keep a short Thai introduction and add:
what the app computes and its scope (DC, linear active-region model, with
cutoff/saturation warnings); setup (`python -m venv .venv`,
`.venv\Scripts\python -m pip install -r requirements.txt`); run
(`.venv\Scripts\python app.py`, http://127.0.0.1:5000); tests
(`.venv\Scripts\python -m unittest discover -v`); and the reference vector
(12 V, 47 kΩ, 10 kΩ, 4.7 kΩ, 1 kΩ, β=150, VBE=0.7 V → IC 1.324 mA,
VCE 4.446 V, ACTIVE).

- [ ] **Step 2: Run the full suite**

Run: `.venv\Scripts\python -m unittest discover -v`
Expected: PASS, zero failures.

- [ ] **Step 3: Verify the running demo**

Start `.venv\Scripts\python app.py` in the background, then run:

```
curl.exe -s http://127.0.0.1:5000/
curl.exe -s -X POST http://127.0.0.1:5000/ -d "vcc=12&r1=47000&r2=10000&rc=4700&re=1000&beta=150&vbe=0.7"
```

Expected: the GET returns the form; the POST output contains `1.324`, `4.446`,
and `PASS`. Stop the server afterwards.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: document setup, tests, and reference example"
```

- [ ] **Step 5: Push to GitHub**

Run: `git push origin main`
Expected: `main -> main`. If authentication is not available, report the exact
remote error and leave the commits local; do not rewrite history.
