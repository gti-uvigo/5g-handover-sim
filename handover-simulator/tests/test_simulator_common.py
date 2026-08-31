import math

import numpy as np
import pandas as pd
import pytest

import simulator_common
import utils


def make_ue_row(gnodeb, throughput=10.0e6, latency=0.01, rx_packets_diff=100,
                 lost_packets=1, tx_bytes_diff=2000, tx_packets_diff=20,
                 rx_bytes_diff=1500, jitter=0.001):
    return {
        "GNodeB": gnodeb,
        "Throughput": throughput,
        "Latency": latency,
        "RxPacketsDiff": rx_packets_diff,
        "LostPackets": lost_packets,
        "TxBytesDiff": tx_bytes_diff,
        "TxPacketsDiff": tx_packets_diff,
        "RxBytesDiff": rx_bytes_diff,
        "Jitter": jitter,
    }


def test_simulate_gnb_aggregates_connected_ue_metrics(scenario):
    intervals = [0, 1]
    # UE0 is connected to gNB 0 for both intervals; UE1 is connected to gNB 1 (never gNB 0).
    ue0_df = pd.DataFrame([make_ue_row(0), make_ue_row(0)])
    ue1_df = pd.DataFrame([make_ue_row(1), make_ue_row(1)])
    ueResults_df = [ue0_df, ue1_df]

    gnb_results = simulator_common.simulate_gnb(
        gnb=0, intervals=intervals, nUEs=2, ueResults_df=ueResults_df,
        scenario=scenario, packetSize=100
    )

    gnb_capacity = utils.get_datarate(scenario["bands"][0]["GNB_Bandwidth_Hz"])
    assert len(gnb_results) == 2
    first, second = gnb_results
    assert first["ConnectedUEs"] == 1
    assert first["GnbCapacity"] == pytest.approx(gnb_capacity)
    assert first["MeanThroughput"] == pytest.approx(10.0e6)
    assert first["Occupation"] == pytest.approx(10.0e6 / gnb_capacity)
    # low occupation -> no simulated loss, only the channel loss from the input row is kept
    assert first["LostPackets"] == 1
    assert first["RxPacketsDiff"] == 100

    # accumulated counters: first interval has nothing accumulated yet (based on prior intervals)
    assert first["RxPacketsAcc"] == 0
    assert second["RxPacketsAcc"] == 100


def test_simulate_gnb_returns_zeroed_row_when_no_ue_connected(scenario):
    intervals = [0]
    ue0_df = pd.DataFrame([make_ue_row(1)])  # connected to gNB 1, never gNB 0
    ueResults_df = [ue0_df]

    gnb_results = simulator_common.simulate_gnb(
        gnb=0, intervals=intervals, nUEs=1, ueResults_df=ueResults_df,
        scenario=scenario, packetSize=100
    )

    assert len(gnb_results) == 1
    assert gnb_results[0]["ConnectedUEs"] == 0
    assert gnb_results[0]["Throughput"] == 0


def test_simulate_user_restricted_zeroes_metrics_when_unconnected():
    ue_data = pd.DataFrame([
        {"GNodeB": float("nan"), "Throughput": 10.0e6, "Latency": 0.01,
         "RxPacketsDiff": 50, "RxBytesDiff": 5000, "LostPackets": 0},
    ])
    ueResults_df = [ue_data]
    gnb_results_list = [pd.DataFrame([{"Occupation": 0.0}])]

    result = simulator_common.simulate_user_restricted(
        ueResults_df, gnb_results_list, ue=0, intervals=[0], packetSize=100
    )

    assert result.iloc[0]["Latency"] == 0
    assert result.iloc[0]["PLostPackets"] == 0
    assert result.iloc[0]["SimLatency"] == 0


def test_simulate_user_restricted_applies_gnb_occupation_when_connected():
    ue_data = pd.DataFrame([
        {"GNodeB": 0.0, "Throughput": 10.0e6, "Latency": 0.005,
         "RxPacketsDiff": 50, "RxBytesDiff": 5000, "LostPackets": 0},
    ])
    ueResults_df = [ue_data]
    gnb_results_list = [pd.DataFrame([{"Occupation": 0.5}])]

    result = simulator_common.simulate_user_restricted(
        ueResults_df, gnb_results_list, ue=0, intervals=[0], packetSize=100
    )

    row = result.iloc[0]
    # queueing delay was added on top of the original channel latency
    assert row["Latency"] > 0.005
    assert "SimLatency" in row
