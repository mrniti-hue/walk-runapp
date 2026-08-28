"""
Pure decision logic for checkpoint validation — no DB access, so the anti-cheat
rules (the highest-risk part of this system) can be unit tested directly
against edge cases instead of through an HTTP round trip.

The API/repository layer is responsible for loading claim history and writing
the result; everything here just answers "does this data satisfy the rule".
"""

from dataclasses import dataclass
from datetime import datetime

from app.services.geo import haversine_distance_m


@dataclass(frozen=True)
class PositionCheck:
    accepted: bool
    distance_m: float
    reject_reason: str | None  # "low_accuracy" | "too_far"


def evaluate_position(
    *,
    checkpoint_lat: float,
    checkpoint_lng: float,
    radius_m: float,
    max_accuracy_m: float,
    lat: float,
    lng: float,
    accuracy_m: float,
) -> PositionCheck:
    """Single-fix check: is this GPS reading trustworthy enough, and is it
    actually inside the checkpoint radius. Does not know about dwell or quorum.
    """
    if accuracy_m > max_accuracy_m:
        return PositionCheck(accepted=False, distance_m=-1.0, reject_reason="low_accuracy")

    distance_m = haversine_distance_m(checkpoint_lat, checkpoint_lng, lat, lng)
    if distance_m > radius_m:
        return PositionCheck(accepted=False, distance_m=distance_m, reject_reason="too_far")

    return PositionCheck(accepted=True, distance_m=distance_m, reject_reason=None)


def first_dwell_satisfied_at(
    accepted_times: list[datetime],
    *,
    required_seconds: int,
    gap_tolerance_seconds: float = 60,
) -> datetime | None:
    """First moment a member's accepted claims form a continuous stay of
    required_seconds at one checkpoint — i.e. they actually stopped, rather
    than passing through on one lucky fix. `accepted_times` must already be
    filtered to one member and one checkpoint.

    A gap between claims wider than gap_tolerance_seconds (client ping missed,
    brief signal loss) restarts the run rather than failing it outright.
    """
    if not accepted_times:
        return None

    times = sorted(accepted_times)
    if required_seconds <= 0:
        return times[0]

    run_start = times[0]
    for prev, curr in zip(times, times[1:]):
        if (curr - prev).total_seconds() > gap_tolerance_seconds:
            run_start = curr
        if (curr - run_start).total_seconds() >= required_seconds:
            return curr
    return None


def find_quorum_completion(
    member_arrival_times: dict[object, datetime],
    *,
    min_members: int,
    quorum_window_seconds: int,
) -> tuple[datetime, list[object]] | None:
    """Given each member's dwell-satisfied arrival instant (from
    first_dwell_satisfied_at), find the earliest instant at which at least
    min_members were present together — i.e. their arrivals all fall within
    one quorum_window_seconds window.

    This is what stops a team splitting up to farm checkpoints in parallel:
    members arriving hours apart never form a quorum, even if every one of
    them individually satisfied the radius/accuracy/dwell checks.

    Returns (completion_time, member_ids_counted) or None if quorum was never
    reached.
    """
    if len(member_arrival_times) < min_members:
        return None

    ordered = sorted(member_arrival_times.items(), key=lambda kv: kv[1])
    for i in range(len(ordered) - min_members + 1):
        window = ordered[i : i + min_members]
        window_start, window_end = window[0][1], window[-1][1]
        if (window_end - window_start).total_seconds() <= quorum_window_seconds:
            return window_end, [member_id for member_id, _ in window]

    return None
