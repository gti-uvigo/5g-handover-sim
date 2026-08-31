import math

import pandas as pd
import pytest

import occupation


def test_calculate_occupation():
    assert occupation.calculate_occupation(gnb_capacity=100.0, gnb_traffic=50.0) == pytest.approx(0.5)


def test_calculate_system_waiting_time_below_saturation():
    # M/D/1: Wq = 1/mu + occ / (2*mu*(1-occ))
    gnb_capacity = 1.0e6  # bps
    packet_length = 1000  # bytes
    occupation_value = 0.5
    mu = gnb_capacity / (packet_length * 8)
    expected = 1.0 / mu + (occupation_value / (2.0 * mu * (1 - occupation_value)))
    result = occupation.calculate_system_waiting_time(gnb_capacity, occupation_value, packet_length)
    assert result == pytest.approx(expected)


def test_calculate_system_waiting_time_clamps_occupation_at_saturation():
    gnb_capacity = 1.0e6
    packet_length = 1000
    mu = gnb_capacity / (packet_length * 8)
    clamped_occ = 1 - 1e-5
    expected = 1.0 / mu + (clamped_occ / (2.0 * mu * (1 - clamped_occ)))
    result = occupation.calculate_system_waiting_time(gnb_capacity, occupation=1.0, packet_length=packet_length)
    assert result == pytest.approx(expected)


def test_calculate_latency_sums_waiting_time_and_channel_delay():
    assert occupation.calculate_latency(0.01, 0.02) == pytest.approx(0.03)


def test_calculate_throughput_unrestricted_below_saturation():
    assert occupation.calculate_throughput(occupation=0.5, user_throughput=100.0) == 100.0


def test_calculate_throughput_restricted_above_saturation():
    result = occupation.calculate_throughput(occupation=2.0, user_throughput=100.0)
    assert result == pytest.approx(50.0)


def test_calculate_lost_packets_no_loss_below_saturation():
    assert occupation.calculate_lost_packets(occupation=0.5, rx_packets_diff=100) == 0


def test_calculate_lost_packets_above_saturation_adds_channel_loss():
    # occupation_lost_packets = ceil(100 * (1 - 1/2)) = 50
    result = occupation.calculate_lost_packets(occupation=2.0, rx_packets_diff=100, channel_packets_lost=5)
    assert result == 55


def test_is_gnb_stable_true_below_saturation():
    assert occupation.is_gnb_stable(occupation=0.99) is True


def test_is_gnb_stable_false_at_or_above_saturation():
    assert occupation.is_gnb_stable(occupation=1.0) is False


def test_apply_channel_simulation_below_saturation_preserves_throughput_and_packets():
    interval_data = pd.Series({
        "Latency": 0.005,
        "Throughput": 100.0,
        "RxPacketsDiff": 50,
        "RxBytesDiff": 5000,
        "LostPackets": 2,
    })
    result = occupation.apply_channel_simulation(
        interval_data, occupation=0.5, gnb_capacity=1.0e6, packet_length=100
    )
    assert result["Throughput"] == pytest.approx(100.0)
    assert result["RxPacketsDiff"] == 50
    assert result["RxBytesDiff"] == 5000
    assert result["LostPackets"] == 2
    assert result["Latency"] > 0.005  # queueing delay was added


def test_apply_channel_simulation_above_saturation_drops_packets():
    interval_data = pd.Series({
        "Latency": 0.005,
        "Throughput": 100.0,
        "RxPacketsDiff": 100,
        "RxBytesDiff": 10000,
        "LostPackets": 0,
    })
    result = occupation.apply_channel_simulation(
        interval_data, occupation=2.0, gnb_capacity=1.0e6, packet_length=100
    )
    # occupation_lost_packets = ceil(100 * (1 - 1/2)) = 50, capped at rx_packets_diff (100)
    assert result["RxPacketsDiff"] == 50
    assert result["RxBytesDiff"] == 5000
    assert result["LostPackets"] == 50
    assert result["PLostPackets"] == pytest.approx(50 / 100)


def test_apply_channel_simulation_does_not_mutate_input():
    interval_data = pd.Series({
        "Latency": 0.005,
        "Throughput": 100.0,
        "RxPacketsDiff": 50,
        "RxBytesDiff": 5000,
        "LostPackets": 0,
    })
    occupation.apply_channel_simulation(interval_data, occupation=0.5, gnb_capacity=1.0e6, packet_length=100)
    assert interval_data["Latency"] == 0.005
    assert interval_data["RxPacketsDiff"] == 50
