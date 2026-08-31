import numpy as np
import pandas as pd
import pytest

from environment import Environment


def make_gnb_df(throughput, rsrp, n_rows=2):
    return pd.DataFrame({
        "Throughput": [throughput] * n_rows,
        "Rsrp": [rsrp] * n_rows,
        "LatencySum": [0.01] * n_rows,
        "JitterSum": [0.001] * n_rows,
        "RxPackets": [10] * n_rows,
        "RxBytes": [1000] * n_rows,
        "TxPackets": [10] * n_rows,
        "TxBytes": [1000] * n_rows,
        "LostPacketsDiff": [0] * n_rows,
        "Distance": [100.0] * n_rows,
    })


def make_environment(scenario, ue_throughputs_rsrp, interval_duration=1.0, packet_size=100):
    """ue_throughputs_rsrp: list (per UE) of list (per gNB) of (throughput, rsrp) tuples."""
    dataframe = [
        [make_gnb_df(thr, rsrp) for thr, rsrp in per_gnb]
        for per_gnb in ue_throughputs_rsrp
    ]
    nUes = len(ue_throughputs_rsrp)
    return Environment(
        dataframe=dataframe, intervals=[0, 1], scenario=scenario,
        nUes=nUes, interval_duration=interval_duration, packet_size=packet_size,
    )


def test_init_sets_expected_defaults(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    assert env.ue_actions == [-1]
    assert env.connections == [-1]
    assert env.gnb_occupation == [0, 0]
    assert env.current_interval == 0
    assert env.timer == 0


def test_get_current_interval(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.current_interval = 1
    assert env.get_current_interval() == (1, 1)


def test_set_action(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.set_action(0, 1)
    assert env.ue_actions[0] == 1


def test_reset_restores_initial_state(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.set_action(0, 1)
    env.connections[0] = 1
    env.gnb_occupation[0] = 0.9
    env.current_interval = 1
    env.timer = 5

    env.reset()

    assert env.ue_actions == [-1]
    assert env.connections == [-1]
    assert env.gnb_occupation == [0, 0]
    assert env.current_interval == 0
    assert env.timer == 0


def test_is_done_true_on_last_interval(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.current_interval = 1  # last index of intervals=[0, 1]
    assert env.is_done() is True


def test_is_done_false_before_last_interval(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.current_interval = 0
    assert env.is_done() is False


def test_calculate_datarate_occupation_sums_only_connected_ues(scenario):
    env = make_environment(scenario, [
        [(10.0e6, -70), (0, -140)],
        [(50.0e6, -70), (0, -140)],
    ])
    env.connections = [0, -1]  # only UE0 counted for gNB0
    occupation = env.calculate_datarate_occupation(0)
    gnb_capacity = 20.0e6 * 4  # GNB_Bandwidth_Hz * SPECTRAL_EFFICIENCY
    assert occupation == pytest.approx(10.0e6 / gnb_capacity)


def test_calculate_bandwidth_occupation_based_on_ue_actions(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]] * 3)
    env.ue_actions = [0, 0, 1]
    occupation_gnb0 = env.calculate_bandwidth_occupation(0)
    user_bw = scenario["bands"][0]["User_Bandwidth_Hz"]
    gnb_bw = scenario["bands"][0]["GNB_Bandwidth_Hz"]
    assert occupation_gnb0 == pytest.approx((2 * user_bw) / gnb_bw)


def test_calculate_bandwidth_occupation_consolidated_based_on_connections(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]] * 3)
    env.connections = [0, -1, -1]
    occupation_gnb0 = env.calculate_bandwidth_occupation_consolidated(0)
    user_bw = scenario["bands"][0]["User_Bandwidth_Hz"]
    gnb_bw = scenario["bands"][0]["GNB_Bandwidth_Hz"]
    assert occupation_gnb0 == pytest.approx(user_bw / gnb_bw)


def test_get_observation_discretizes_rsrp_and_occupation(scenario):
    # Bucketing is by successive `< threshold` checks (-60/-80/-100/-120), so a value
    # that is *more* negative than -60 (e.g. -90) hits the first branch (bucket 0),
    # while a value *less* negative than -60 (e.g. -50) falls through to the last (bucket 4).
    env = make_environment(scenario, [[(10.0e6, -50), (0, -90)]])
    env.connections[0] = 1
    env.gnb_occupation = [0, 0.6]  # bucket 0, bucket 2

    observation = env.get_observation(0)

    # [rsrp_gnb0_bucket, rsrp_gnb1_bucket, connection, occupation_gnb0_bucket, occupation_gnb1_bucket]
    np.testing.assert_array_equal(observation, np.array([4, 0, 1, 0, 2], dtype=np.float32))


def test_step_admits_ues_sequentially_and_updates_occupation(scenario):
    env = make_environment(scenario, [
        [(10.0e6, -70), (0, -140)],
        [(50.0e6, -70), (0, -140)],
    ])
    env.ue_actions = [0, 0]

    env.step()

    gnb_capacity = 20.0e6 * 4
    assert env.connections == [0, 0]
    assert env.gnb_occupation[0] == pytest.approx((10.0e6 + 50.0e6) / gnb_capacity)
    assert env.gnb_occupation[1] == 0
    assert env.current_interval == 1
    assert env.timer == pytest.approx(1.0)


def test_step_rejects_ue_when_gnb_would_be_overloaded(scenario):
    env = make_environment(scenario, [
        [(70.0e6, -70), (0, -140)],
        [(70.0e6, -70), (0, -140)],
    ])
    env.ue_actions = [0, 0]

    env.step()

    # UE0 fits alone (70e6 / 80e6 < 0.99), but admitting UE1 on top would exceed capacity
    assert env.connections == [0, -1]


def test_get_reward_mismatch_between_action_and_connection_is_penalized(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.ue_actions[0] = 0
    env.connections[0] = -1
    assert env.get_reward(0) == -1


def test_get_reward_unconnected_ue_is_penalized(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.ue_actions[0] = -1
    env.connections[0] = -1
    assert env.get_reward(0) == -1


def test_get_reward_overloaded_gnb_is_penalized(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.ue_actions[0] = 0
    env.connections[0] = 0
    env.gnb_occupation[0] = 1.0
    assert env.get_reward(0) == -1


def test_get_reward_scales_with_throughput(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.ue_actions[0] = 0
    env.connections[0] = 0
    env.gnb_occupation[0] = 0.5
    assert env.get_reward(0) == pytest.approx(10.0e6 / 3.85e8)


def test_get_reward_degrades_when_consolidated_and_over_capacity(scenario):
    env = make_environment(scenario, [[(10.0e6, -70), (0, -140)]])
    env.consolidate_directly = True
    env.ue_actions[0] = 0
    env.connections[0] = 0
    env.gnb_occupation[0] = 2.0

    reward = env.get_reward(0)

    base_reward = 10.0e6 / 3.85e8
    expected = base_reward * (1 / 2.0)
    assert reward == pytest.approx(expected)
