from plant_robotics.domain.observations import TargetObservation, TrackState


def test_lost_target_is_not_actionable():
    obs = TargetObservation("t1", "left_arm", 10, TrackState.LOST, 10, 10, True)
    assert not obs.safe_to_act


def test_visible_verified_target_passes_observation_gate():
    obs = TargetObservation("t1", "left_arm", 10, TrackState.VISIBLE, 10, 10, True)
    assert obs.safe_to_act


def test_visible_unverified_identity_is_not_actionable():
    obs = TargetObservation("t1", "left_arm", 10, TrackState.VISIBLE, 10, 10, False)
    assert not obs.safe_to_act
