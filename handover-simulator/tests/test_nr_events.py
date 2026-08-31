import nrEvents


def test_check_A3_event_triggers_when_best_meets_threshold():
    # best_rsrp >= connected_rsrp + A3Offset + Hys
    assert nrEvents.check_A3_event(best_rsrp=-70, connected_rsrp=-80, A3Offset=5, Hys=2) is True


def test_check_A3_event_does_not_trigger_below_threshold():
    assert nrEvents.check_A3_event(best_rsrp=-85, connected_rsrp=-80, A3Offset=5, Hys=2) is False


def test_check_A3_event_boundary_is_inclusive():
    # best_rsrp exactly equal to threshold should trigger (>=)
    assert nrEvents.check_A3_event(best_rsrp=-73, connected_rsrp=-80, A3Offset=5, Hys=2) is True


def test_check_A3_2_event_triggers_when_target_drops_below_threshold():
    # target_rsrp < connected_rsrp + A3Offset - Hys
    assert nrEvents.check_A3_2_event(target_rsrp=-90, connected_rsrp=-80, A3Offset=5, Hys=2) is True


def test_check_A3_2_event_does_not_trigger_above_threshold():
    assert nrEvents.check_A3_2_event(target_rsrp=-70, connected_rsrp=-80, A3Offset=5, Hys=2) is False


def test_check_A3_2_event_boundary_is_exclusive():
    # target_rsrp exactly equal to threshold should NOT trigger (strict <)
    assert nrEvents.check_A3_2_event(target_rsrp=-77, connected_rsrp=-80, A3Offset=5, Hys=2) is False
