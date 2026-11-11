import unittest
from hardware_box.tolerance import analyze_tolerance_stack, analyze_clearance_fit


class ToleranceTests(unittest.TestCase):
    def test_stack_worst_case_and_rss(self):
        result = analyze_tolerance_stack([
            {"name": "A", "nominal": 10.0, "tolerance_plus": 0.1, "tolerance_minus": 0.1, "unit": "mm"},
            {"name": "B", "nominal": 0.5, "tolerance_plus": 0.05, "tolerance_minus": 0.02, "unit": "mm", "coefficient": -1},
        ])
        self.assertAlmostEqual(result["nominal_mm"], 9.5)
        self.assertAlmostEqual(result["worst_case"]["plus_mm"], 0.12)
        self.assertAlmostEqual(result["worst_case"]["minus_mm"], 0.15)
        self.assertAlmostEqual(result["rss_independent"]["plus_mm"], (0.1**2 + 0.02**2) ** 0.5)

    def test_unit_conversion_from_inches(self):
        result = analyze_tolerance_stack([{"nominal": 1, "tolerance_plus": 0.001, "unit": "in"}])
        self.assertAlmostEqual(result["nominal_mm"], 25.4)
        self.assertAlmostEqual(result["worst_case"]["plus_mm"], 0.0254)

    def test_clearance_fit(self):
        result = analyze_clearance_fit(
            {"nominal": 10.1, "tolerance_plus": 0.02, "tolerance_minus": 0.02},
            {"nominal": 10.0, "tolerance_plus": 0.01, "tolerance_minus": 0.01},
        )
        self.assertEqual(result["fit_type"], "clearance")
        self.assertAlmostEqual(result["minimum_clearance_mm"], 0.07)

    def test_transition_fit(self):
        result = analyze_clearance_fit(
            {"nominal": 10.0, "tolerance_plus": 0.05, "tolerance_minus": 0.05},
            {"nominal": 10.0, "tolerance_plus": 0.05, "tolerance_minus": 0.05},
        )
        self.assertEqual(result["fit_type"], "transition")

    def test_interference_fit(self):
        result = analyze_clearance_fit(
            {"nominal": 9.9, "tolerance_plus": 0.01, "tolerance_minus": 0.01},
            {"nominal": 10.0, "tolerance_plus": 0.01, "tolerance_minus": 0.01},
        )
        self.assertEqual(result["fit_type"], "interference")
        self.assertLess(result["maximum_clearance_mm"], 0)

    def test_invalid_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            analyze_tolerance_stack([{"nominal": 10, "tolerance_plus": -0.1}])
        with self.assertRaises(ValueError):
            analyze_tolerance_stack([{"nominal": float("nan")}])
        with self.assertRaises(ValueError):
            analyze_tolerance_stack([])


if __name__ == "__main__":
    unittest.main()
