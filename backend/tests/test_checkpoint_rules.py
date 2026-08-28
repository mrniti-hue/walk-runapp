from datetime import datetime, timedelta, timezone

from app.services.checkpoint_rules import (
    evaluate_position,
    find_quorum_completion,
    first_dwell_satisfied_at,
)

CHECKPOINT = dict(checkpoint_lat=13.7437, checkpoint_lng=100.4888, radius_m=40, max_accuracy_m=50)


def t(seconds: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)


def test_accepts_fix_inside_radius_with_good_accuracy():
    result = evaluate_position(**CHECKPOINT, lat=13.7437, lng=100.4888, accuracy_m=15)
    assert result.accepted
    assert result.reject_reason is None


def test_rejects_low_accuracy_before_checking_distance():
    result = evaluate_position(**CHECKPOINT, lat=13.7437, lng=100.4888, accuracy_m=80)
    assert not result.accepted
    assert result.reject_reason == "low_accuracy"


def test_rejects_fix_outside_radius():
    # ~600m away — clearly outside a 40m radius.
    result = evaluate_position(**CHECKPOINT, lat=13.7468, lng=100.4930, accuracy_m=15)
    assert not result.accepted
    assert result.reject_reason == "too_far"


def test_dwell_not_satisfied_by_single_fix():
    assert first_dwell_satisfied_at([t(0)], required_seconds=45) is None


def test_dwell_satisfied_by_continuous_fixes():
    times = [t(0), t(20), t(40), t(50)]
    arrival = first_dwell_satisfied_at(times, required_seconds=45)
    assert arrival == t(50)


def test_dwell_run_resets_after_large_gap():
    # Gap of 200s (signal loss) restarts the run; the final 15s isn't enough.
    times = [t(0), t(20), t(220), t(235)]
    assert first_dwell_satisfied_at(times, required_seconds=45, gap_tolerance_seconds=60) is None


def test_zero_dwell_requirement_satisfied_immediately():
    assert first_dwell_satisfied_at([t(5)], required_seconds=0) == t(5)


def test_quorum_met_when_arrivals_close_together():
    arrivals = {"a": t(0), "b": t(120), "c": t(600)}
    result = find_quorum_completion(arrivals, min_members=2, quorum_window_seconds=300)
    assert result is not None
    completed_at, counted = result
    assert completed_at == t(120)
    assert set(counted) == {"a", "b"}


def test_quorum_not_met_when_team_splits_up():
    # Two members hours apart never form a quorum, even though each
    # individually dwelled long enough at the checkpoint.
    arrivals = {"a": t(0), "b": t(3 * 3600)}
    assert find_quorum_completion(arrivals, min_members=2, quorum_window_seconds=300) is None


def test_quorum_not_met_below_min_members():
    assert find_quorum_completion({"a": t(0)}, min_members=2, quorum_window_seconds=300) is None
