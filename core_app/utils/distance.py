import math


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points in kilometers.
    Uses the Haversine formula — which takes the Earth's curvature into account."""
    R = 6371

    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_nearest_vendors(user_lat, user_lon, vendors, max_distance_km=10):
    """Return the nearest vendors to the user in order of distance.
    max_distance_km: Return vendors within this radius."""

    vendors_with_distance = []

    for vendor in vendors:
        if not vendor.latitude or not vendor.longitude:
            continue

        distance = haversine_distance(
            user_lat, user_lon, vendor.latitude, vendor.longitude
        )
        if distance <= max_distance_km:
            vendors_with_distance.append(
                {"vendor": vendor, "distance": round(distance, 2)}
            )

    vendors_with_distance.sort(key=lambda x: x["distance"])
    return vendors_with_distance


def get_nearest_collection_center(user_lat, user_lon):
    """Return the nearest collection center to the given coordinates."""
    from core_app.models import CollectionCenter

    centers = CollectionCenter.objects.filter(latitude__isnull=False, longitude__isnull=False)
    if not centers.exists():
        return CollectionCenter.objects.first()

    nearest_center = None
    min_distance = float("inf")

    for center in centers:
        distance = haversine_distance(
            user_lat, user_lon, center.latitude, center.longitude
        )
        if distance < min_distance:
            min_distance = distance
            nearest_center = center

    return nearest_center or CollectionCenter.objects.first()
