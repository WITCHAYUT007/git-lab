import unittest

from bjt import _solve_nodal, analyze_ce_bias

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


if __name__ == "__main__":
    unittest.main()
