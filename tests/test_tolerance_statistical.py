import pytest

from hardware_box.tolerance import analyze_shaft_hole_fit


def test_shaft_hole_fit_reports_worst_case_and_rss_statistics():
    result = analyze_shaft_hole_fit(
        {"nominal": 10.05, "tolerance_plus": 0.02, "tolerance_minus": 0.02, "unit": "mm"},
        {"nominal": 10.00, "tolerance_plus": 0.01, "tolerance_minus": 0.01, "unit": "mm"},
    )
    assert result["fit_type_worst_case"] == "clearance"
    assert result["worst_case_clearance_mm"]["minimum"] == pytest.approx(0.02)
    assert result["worst_case_clearance_mm"]["maximum"] == pytest.approx(0.08)
    stats = result["statistical"]
    assert stats["clearance_sigma_rss_mm"] == pytest.approx((0.02**2 + 0.01**2) ** 0.5 / 3)
    assert 0.0 <= stats["probability_of_interference"] <= 1.0
    assert stats["probability_of_clearance"] + stats["probability_of_interference"] == pytest.approx(1.0)


def test_statistical_fit_handles_zero_tolerances():
    result = analyze_shaft_hole_fit(
        {"nominal": 10.1},
        {"nominal": 10.0},
    )
    assert result["statistical"]["clearance_sigma_rss_mm"] == 0.0
    assert result["statistical"]["probability_of_interference"] == 0.0


@pytest.mark.parametrize("hole,shaft", [
    ({"nominal": -1.0}, {"nominal": 1.0}),
    ({"nominal": 1.0}, {"nominal": 0.0}),
    ({"nominal": 1.0, "tolerance_plus": -0.1}, {"nominal": 1.0}),
])
def test_shaft_hole_fit_rejects_negative_or_invalid_dimensions(hole, shaft):
    with pytest.raises(ValueError):
        analyze_shaft_hole_fit(hole, shaft)


def test_rejects_invalid_sigma_multiplier():
    with pytest.raises(ValueError):
        analyze_shaft_hole_fit({"nominal": 2}, {"nominal": 1}, sigma_multiplier=0)

def test_rejects_dimension_with_nonpositive_lower_limit():
    with pytest.raises(ValueError, match="minimum size must remain greater than zero"):
        analyze_shaft_hole_fit(
            {"nominal": 1.0, "tolerance_minus": 1.0},
            {"nominal": 0.5},
        )


def test_statistical_model_reports_asymmetric_tolerance_shift():
    result = analyze_shaft_hole_fit(
        {"nominal": 10.0, "tolerance_plus": 0.03, "tolerance_minus": 0.01},
        {"nominal": 9.9, "tolerance_plus": 0.01, "tolerance_minus": 0.03},
    )
    stats = result["statistical"]
    assert stats["hole_process_mean_mm"] == pytest.approx(10.01)
    assert stats["shaft_process_mean_mm"] == pytest.approx(9.89)
    assert stats["clearance_mean_mm"] == pytest.approx(0.12)

def test_fit_interval_name_reflects_custom_sigma_multiplier():
    result = analyze_shaft_hole_fit(
        {"nominal": 10.1, "tolerance_plus": 0.03, "tolerance_minus": 0.03},
        {"nominal": 10.0, "tolerance_plus": 0.02, "tolerance_minus": 0.02},
        sigma_multiplier=2.0,
    )
    assert "configured_k_sigma_clearance_mm" in result["statistical"]
    assert "three_sigma_clearance_mm" not in result["statistical"]
