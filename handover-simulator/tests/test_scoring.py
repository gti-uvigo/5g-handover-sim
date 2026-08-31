import pandas as pd
import pytest

import scoring


def test_calculate_score_returns_zero_when_no_connected_gnb(scenario):
    user_data = pd.Series({"Rsrp": -90})
    assert scoring.calculate_score(user_data, scenario, None, alpha=1.0, beta=1.0) == 0


def test_calculate_score_returns_zero_when_no_user_data(scenario):
    assert scoring.calculate_score(None, scenario, 0, alpha=1.0, beta=1.0) == 0


def test_calculate_score_returns_zero_when_rsrp_missing(scenario):
    user_data = pd.Series({"Rsrp": None})
    assert scoring.calculate_score(user_data, scenario, 0, alpha=1.0, beta=1.0) == 0


def test_calculate_score_saturates_power_factor_above_max_rsrp(scenario):
    # Rsrp above -80 (max_rsrp) saturates p to 1, so score == alpha * bw
    user_data = pd.Series({"Rsrp": -70})
    score = scoring.calculate_score(user_data, scenario, connected_gnb=0, alpha=2.0, beta=1.0)
    expected_bw = scenario["bands"][0]["User_Bandwidth_Hz"] / scoring.BW_MAX
    assert score == pytest.approx(2.0 * expected_bw)


def test_calculate_score_scales_linearly_between_min_and_max_rsrp(scenario):
    # Rsrp exactly halfway between min_rsrp (-100) and max_rsrp (-80) -> p == 0.5
    user_data = pd.Series({"Rsrp": -90})
    score = scoring.calculate_score(user_data, scenario, connected_gnb=0, alpha=2.0, beta=1.0)
    expected_bw = scenario["bands"][0]["User_Bandwidth_Hz"] / scoring.BW_MAX
    assert score == pytest.approx(2.0 * expected_bw * 0.5)


def test_calculate_score_uses_the_band_of_the_connected_gnb(scenario):
    user_data = pd.Series({"Rsrp": -70})
    score_gnb0 = scoring.calculate_score(user_data, scenario, connected_gnb=0, alpha=1.0, beta=1.0)
    score_gnb1 = scoring.calculate_score(user_data, scenario, connected_gnb=1, alpha=1.0, beta=1.0)
    # both gNBs share the same User_Bandwidth_Hz in the fixture, so scores match;
    # this pins down that the lookup is by the connected gNB's Band_ID.
    assert score_gnb0 == pytest.approx(score_gnb1)


def test_calculate_algorithm_score_sums_last_rx_bytes_acc_in_mbytes():
    # Each row holds the per-gNB RxBytesAcc values (as calculate_algorithm_score is fed
    # a Series of per-gNB Series when called from the real pipeline).
    gnbs_metrics = pd.DataFrame({
        "RxBytesAcc": [
            pd.Series({"gnb0": 0, "gnb1": 0}),
            pd.Series({"gnb0": 5_000_000, "gnb1": 3_000_000}),
        ]
    })
    score = scoring.calculate_algorithm_score(gnbs_metrics)
    assert score == pytest.approx(8_000_000 / 10**6)
