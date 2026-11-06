import csv
from math import asin, cos, radians, sin, sqrt

from django.conf import settings

# Price file has no coordinates. city_coords.csv is city/state -> lat/lng.
PRICES_PATH = settings.BASE_DIR / "fuel-prices-for-be-assessment.csv"
COORDS_PATH = settings.BASE_DIR / "data" / "city_coords.csv"

_CACHE = None
CELL = 0.5


def miles_between(lat1, lng1, lat2, lng2):
    radius = 3958.8
    p1, p2 = radians(lat1), radians(lat2)
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlng / 2) ** 2
    return 2 * radius * asin(sqrt(a))


def load_stations():
    global _CACHE
    if _CACHE is None:
        _CACHE = _load()
    return _CACHE


def _load():
    coords = {}
    with COORDS_PATH.open(newline="") as fh:
        for row in csv.DictReader(fh):
            coords[(row["city"], row["state"])] = (float(row["lat"]), float(row["lng"]))

    best = {}
    with PRICES_PATH.open(newline="") as fh:
        for row in csv.DictReader(fh):
            city = row["City"].strip()
            state = row["State"].strip().upper()
            point = coords.get((city, state))
            if not point:
                continue
            price = float(row["Retail Price"])
            if price <= 0:
                continue
            key = (city, state)
            prev = best.get(key)
            if prev and prev["price"] <= price:
                continue
            best[key] = {
                "truckstop_id": row["OPIS Truckstop ID"].strip(),
                "name": row["Truckstop Name"].strip(),
                "city": city,
                "state": state,
                "price": price,
                "lat": point[0],
                "lng": point[1],
            }

    grid = {}
    for station in best.values():
        cell = _cell(station["lat"], station["lng"])
        grid.setdefault(cell, []).append(station)
    return list(best.values()), grid


def _cell(lat, lng):
    return (int(lat // CELL), int(lng // CELL))


def near_route(latlngs, total_miles, limit_miles):
    """Stations within limit_miles of the line. `mile` is distance along the route."""
    stations, grid = load_stations()
    if len(latlngs) < 2 or total_miles <= 0:
        return []

    cum = [0.0]
    for (lat1, lng1), (lat2, lng2) in zip(latlngs, latlngs[1:]):
        cum.append(cum[-1] + miles_between(lat1, lng1, lat2, lng2))
    shape = cum[-1] or 1.0
    scale = total_miles / shape

    ring = int(limit_miles / 20) + 1
    best = {}
    for (lat, lng), dist in zip(latlngs, cum):
        base = _cell(lat, lng)
        mile = dist * scale
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                for station in grid.get((base[0] + dx, base[1] + dy), ()):
                    off = miles_between(lat, lng, station["lat"], station["lng"])
                    if off > limit_miles:
                        continue
                    key = (station["city"], station["state"])
                    prev = best.get(key)
                    if prev is None or off < prev["off_miles"]:
                        item = dict(station)
                        item["mile"] = mile
                        item["off_miles"] = off
                        best[key] = item

    picked = []
    for station in best.values():
        if 0.5 < station["mile"] < total_miles - 0.5:
            picked.append(station)
    picked.sort(key=lambda s: s["mile"])
    return picked
