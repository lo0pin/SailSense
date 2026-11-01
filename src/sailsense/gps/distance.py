import math


EARTH_RADIUS_M = 6371000
M_TO_NM = 1 / 1852
M_TO_KM = 1 / 1000


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """
    Entfernung zwischen zwei GPS-Punkten in Metern.
    """
    if None in (lat1, lon1, lat2, lon2):
        return 0.0

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_M * c


def meters_to_nm(meters: float) -> float:
    return meters * M_TO_NM


def meters_to_km(meters: float) -> float:
    return meters * M_TO_KM
