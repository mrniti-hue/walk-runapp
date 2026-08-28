from app.services.geo import haversine_distance_m


def test_same_point_is_zero():
    assert haversine_distance_m(13.7, 100.5, 13.7, 100.5) == 0.0


def test_known_distance_bangkok_landmarks():
    # Wat Arun to Wat Pho, roughly 550-650m across the river.
    d = haversine_distance_m(13.7437, 100.4888, 13.7468, 100.4930)
    assert 400 < d < 700
