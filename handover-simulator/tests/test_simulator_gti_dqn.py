import pandas as pd
import pytest

from simulator_gti_dqn import weighted_avg


def test_weighted_avg_computes_scalar_weighted_average():
    df = pd.DataFrame({"value": [10.0, 20.0], "weight": [1.0, 3.0]})
    result = weighted_avg(df, "value", "weight")
    expected = (10.0 * 1.0 + 20.0 * 3.0) / (1.0 + 3.0)
    assert result == pytest.approx(expected)


def test_weighted_avg_equal_weights_matches_plain_mean():
    df = pd.DataFrame({"value": [10.0, 20.0, 30.0], "weight": [1.0, 1.0, 1.0]})
    result = weighted_avg(df, "value", "weight")
    assert result == pytest.approx(df["value"].mean())


def test_weighted_avg_zero_total_weight_yields_nan():
    df = pd.DataFrame({"value": [10.0, -10.0], "weight": [0.0, 0.0]})
    result = weighted_avg(df, "value", "weight")
    assert pd.isna(result)
