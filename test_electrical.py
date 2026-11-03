import unittest
from electrical import analyze_dc


class TestDCAnalyzer(unittest.TestCase):
    def test_known_values(self):
        result = analyze_dc(12, 6)
        self.assertAlmostEqual(result["current_a"], 2.0)
        self.assertAlmostEqual(result["power_w"], 24.0)

    def test_zero_voltage(self):
        result = analyze_dc(0, 10)
        self.assertAlmostEqual(result["current_a"], 0.0)
        self.assertAlmostEqual(result["power_w"], 0.0)

    def test_negative_voltage(self):
        result = analyze_dc(-12, 6)
        self.assertAlmostEqual(result["current_a"], -2.0)
        self.assertAlmostEqual(result["power_w"], 24.0)

    def test_non_positive_resistance(self):
        for resistance in (0, -1):
            with self.subTest(resistance=resistance):
                with self.assertRaises(ValueError):
                    analyze_dc(12, resistance)

    def test_non_numeric_input(self):
        with self.assertRaises(TypeError):
            analyze_dc("12", 6)


if __name__ == "__main__":
    unittest.main()