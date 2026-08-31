import os

import pandas as pd
import pytest

import utils


def test_get_datarate():
    assert utils.get_datarate(20.0e6) == pytest.approx(80.0e6)


def test_get_datarate_zero_bandwidth():
    assert utils.get_datarate(0.0) == 0.0


def test_apply_penalty_full_time_applies_full_penalty():
    # Real call sites (simulator_3gpp.py, simulator_3gpp_rel16.py, simulator_sbgh.py) always
    # pass a single-row Series (from `.iloc[index]`) as connected_gnb.
    connected_gnb = pd.Series({"Latency": 0.010, "Throughput": 100.0})
    penalty_dict = {"Latency": 0.020}
    result = utils.apply_penalty(connected_gnb, penalty_dict, time=1.0, interval=0.5)
    assert result["Latency"] == pytest.approx(0.030)


def test_apply_penalty_partial_time_scales_penalty():
    connected_gnb = pd.Series({"Latency": 0.010})
    penalty_dict = {"Latency": 0.020}
    # time < interval -> penalty scaled by time/interval
    result = utils.apply_penalty(connected_gnb, penalty_dict, time=0.25, interval=0.5)
    assert result["Latency"] == pytest.approx(0.010 + 0.020 * 0.5)


def test_apply_penalty_ignores_keys_not_in_connected_gnb():
    connected_gnb = pd.Series({"Latency": 0.010})
    penalty_dict = {"Jitter": 0.005}
    result = utils.apply_penalty(connected_gnb, penalty_dict, time=1.0, interval=0.5)
    assert "Jitter" not in result
    assert result["Latency"] == pytest.approx(0.010)


def test_apply_penalty_none_connected_gnb_returns_none():
    assert utils.apply_penalty(None, {"Latency": 0.02}, time=1.0, interval=0.5) is None


def test_apply_penalty_none_penalty_dict_returns_input_unchanged():
    connected_gnb = pd.Series({"Latency": 0.010})
    result = utils.apply_penalty(connected_gnb, None, time=1.0, interval=0.5)
    assert result["Latency"] == pytest.approx(0.010)


def test_get_gnb_data():
    df0 = pd.DataFrame({"Rsrp": [-90, -85]})
    df1 = pd.DataFrame({"Rsrp": [-70, -65]})
    dataframes = [df0, df1]
    row = utils.get_gnb_data(1, dataframes, 0)
    assert row["Rsrp"] == -70


@pytest.mark.parametrize(
    "value, expected",
    [
        (500, "500.00 Hz"),
        (1500, "1.50 kHz"),
        (2_500_000, "2.50 MHz"),
        (3_500_000_000, "3.50 GHz"),
    ],
)
def test_format_frequency_numeric(value, expected):
    assert utils.format_frequency(value) == expected


def test_format_frequency_non_numeric():
    assert utils.format_frequency("not-a-number") == "Invalid input. Please provide a numeric value."


def test_parse_scenario_file(tmp_path):
    scenario_file = tmp_path / "scenario.txt"
    scenario_file.write_text(
        "# comment line, should be ignored\n"
        "\n"
        "!0.0 1000.0 0.0 1000.0\n"
        "*0 2000000000 5000000 20000000\n"
        "0 100.0 200.0 10.0 0 30.0 macro\n"
    )

    scenario_info = utils.parse_scenario_file(str(scenario_file))

    assert scenario_info["scenario_dimensions"] == {
        "min_x": 0.0,
        "max_x": 1000.0,
        "min_y": 0.0,
        "max_y": 1000.0,
    }
    assert scenario_info["bands"] == [
        {
            "Band_ID": 0,
            "Central_Frequency_Hz": 2000000000.0,
            "User_Bandwidth_Hz": 5000000.0,
            "GNB_Bandwidth_Hz": 20000000.0,
        }
    ]
    assert scenario_info["gnbs"] == [
        {
            "GNB_ID": 0,
            "Position_X": "100.0",
            "Position_Y": "200.0",
            "Position_Z": "10.0",
            "Band_ID": 0,
            "Transmission_Power_dBm": "30.0",
            "Type": "macro",
        }
    ]


def test_load_dataframes(tmp_path):
    for ue in range(2):
        for gnb in range(2):
            folder = tmp_path / str(ue) / str(gnb)
            folder.mkdir(parents=True)
            pd.DataFrame({"Rsrp": [ue * 10 + gnb]}).to_csv(folder / "traces.csv", index=False)

    dataframes = utils.load_dataframes(str(tmp_path), nUEs=2, nGnb=2)

    assert len(dataframes) == 2
    assert len(dataframes[0]) == 2
    assert dataframes[1][1]["Rsrp"].iloc[0] == 11


def test_load_dataframes_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        utils.load_dataframes(str(tmp_path), nUEs=1, nGnb=1)
