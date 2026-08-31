import pandas as pd
import pytest

import simulator_3gpp


def make_gnb_trace(times, rsrp_values, throughput=10.0e6):
    return pd.DataFrame({
        "Time": times,
        "Rsrp": rsrp_values,
        "Throughput": [throughput] * len(times),
        "TxPacketsDiff": [1] * len(times),
        "TxBytesDiff": [100] * len(times),
        "RxPacketsDiff": [1] * len(times),
        "RxBytesDiff": [100] * len(times),
        "LatencySum": [0.01] * len(times),
        "JitterSum": [0.001] * len(times),
        "LostPacketsDiff": [0] * len(times),
        "Distance": [50.0] * len(times),
        "UE Position": ["(0,0)"] * len(times),
        "System Time": times,
    })


def test_simulate_user_first_interval_has_no_connection_yet():
    # The connection decision made during interval N only takes effect in interval N+1,
    # so the very first result always reports no gNB regardless of signal strength.
    times = [0.0, 0.1]
    dataframes = [
        make_gnb_trace(times, rsrp_values=[-70, -70]),
        make_gnb_trace(times, rsrp_values=[-90, -90]),
    ]
    simDataframes = [dataframes]

    result = simulator_3gpp.simulate_user(
        user=0, simDataframes=simDataframes, intervals=times,
        Hys=2, A3Offset=3, NrMeasureInt=0.1, interval=0.1,
        DECISION_PARAMETER="Rsrp", TTT=0.1, penalty_time=0.05,
        packetSize=100, penalty_dict={"Latency": 0.02},
    )

    assert result[0]["GNodeB"] is None
    assert result[1]["GNodeB"] == 0  # connects to the stronger gNB (index 0) one interval later


def test_simulate_user_stays_connected_without_a3_trigger():
    # gNB1 is close to gNB0 in strength but never crosses the A3 threshold, so no handover occurs.
    times = [0.0, 0.1, 0.2, 0.3]
    dataframes = [
        make_gnb_trace(times, rsrp_values=[-70, -70, -70, -70]),
        make_gnb_trace(times, rsrp_values=[-72, -72, -72, -72]),
    ]
    simDataframes = [dataframes]

    result = simulator_3gpp.simulate_user(
        user=0, simDataframes=simDataframes, intervals=times,
        Hys=2, A3Offset=3, NrMeasureInt=0.1, interval=0.1,
        DECISION_PARAMETER="Rsrp", TTT=0.1, penalty_time=0.05,
        packetSize=100, penalty_dict={"Latency": 0.02},
    )

    assert all(r["GNodeB"] == 0 for r in result[1:])
    assert all(r["Handovers"] == 0 for r in result)


def test_simulate_user_performs_handover_when_a3_condition_holds_through_ttt():
    # gNB1 briefly dips then becomes strong enough (>= connected + A3Offset + Hys) and
    # stays there through the TTT window, triggering a handover from gNB0 to gNB1.
    times = [round(0.1 * i, 2) for i in range(10)]
    dataframes = [
        make_gnb_trace(times, rsrp_values=[-70] * 10),
        make_gnb_trace(times, rsrp_values=[-90] + [-60] * 9),
    ]
    simDataframes = [dataframes]

    result = simulator_3gpp.simulate_user(
        user=0, simDataframes=simDataframes, intervals=times,
        Hys=1, A3Offset=1, NrMeasureInt=0.1, interval=0.1,
        DECISION_PARAMETER="Rsrp", TTT=0.1, penalty_time=0.05,
        packetSize=100, penalty_dict={"Latency": 0.02},
    )

    connected_gnbs = [r["GNodeB"] for r in result]
    assert connected_gnbs[1] == 0  # starts on gNB 0
    assert connected_gnbs[-1] == 1  # ends up handed over to gNB 1
    assert any(r["Handovers"] for r in result)
