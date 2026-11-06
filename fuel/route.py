import json
import ssl
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

from django.conf import settings

from fuel.planner import MPG, MAX_RANGE, plan_stops
from fuel.stations import near_route

NOMINATIM = "https://nominatim.openstreetmap.org/search"
OSRM = "https://router.project-osrm.org/route/v1/driving"
UA = "fuel-route/1.0"

# geocode hits the network once per location, then we reuse it
_geo_cache = None
_route_cache = {}


class LocationError(Exception):
    pass


class RouteError(Exception):
    pass


def build_route(start, finish):
    key = (" ".join(start.lower().split()), " ".join(finish.lower().split()))
    cached = _route_cache.get(key)
    if cached:
        return cached

    start_hit = geocode(start)
    finish_hit = geocode(finish)
    route = driving_route(start_hit, finish_hit)

    latlngs = [(lat, lng) for lng, lat in route["coords"]]
    total = route["miles"]
    stops = None
    for limit in (25, 50, 80):
        nearby = near_route(latlngs, total, limit)
        stops = plan_stops(nearby, total)
        if stops is not None:
            break
    if stops is None:
        raise LocationError(
            "Not enough truck stops along this route to stay inside a 500 mile range."
        )

    payload = _payload(start, finish, start_hit, finish_hit, route, stops)
    _route_cache[key] = payload
    return payload


def geocode(query):
    cache = _geocodes()
    key = " ".join(query.lower().split())
    if key in cache:
        return cache[key]

    url = NOMINATIM + "?" + urlencode({
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "us",
    })
    data = _get_json(url, LocationError)
    if not data:
        raise LocationError(f"Couldn't find '{query}' in the US.")

    hit = {
        "name": data[0].get("display_name") or query,
        "lat": float(data[0]["lat"]),
        "lng": float(data[0]["lon"]),
    }
    cache[key] = hit
    path = settings.BASE_DIR / "data" / "geocode_cache.json"
    path.write_text(json.dumps(cache))
    return hit


def driving_route(start_hit, finish_hit):
    # one routing call for the whole trip
    path = f"{start_hit['lng']},{start_hit['lat']};{finish_hit['lng']},{finish_hit['lat']}"
    url = f"{OSRM}/{path}?overview=simplified&geometries=geojson&steps=false"
    data = _get_json(url, RouteError)
    if data.get("code") != "Ok" or not data.get("routes"):
        raise RouteError("Couldn't build a driving route for those locations.")

    route = data["routes"][0]
    return {
        "miles": route["distance"] / 1609.344,
        "coords": route["geometry"]["coordinates"],
    }


def _payload(start, finish, start_hit, finish_hit, route, stops):
    fuel_stops = []
    total_cost = 0.0
    total_gallons = 0.0
    for stop in stops:
        price = round(stop["price"], 3)
        gallons = round(stop["gallons"], 2)
        cost = round(gallons * price, 2)
        total_cost += cost
        total_gallons += gallons
        fuel_stops.append({
            "truckstop_id": stop["truckstop_id"],
            "name": stop["name"],
            "city": stop["city"],
            "state": stop["state"],
            "price_per_gallon": price,
            "mile": round(stop["mile"], 1),
            "gallons": gallons,
            "cost": cost,
            "lat": round(stop["lat"], 5),
            "lng": round(stop["lng"], 5),
        })

    return {
        "start": {
            "query": start,
            "name": start_hit["name"],
            "lat": round(start_hit["lat"], 5),
            "lng": round(start_hit["lng"], 5),
        },
        "finish": {
            "query": finish,
            "name": finish_hit["name"],
            "lat": round(finish_hit["lat"], 5),
            "lng": round(finish_hit["lng"], 5),
        },
        "distance_miles": round(route["miles"], 1),
        "mpg": int(MPG),
        "max_range_miles": int(MAX_RANGE),
        "total_gallons": round(total_gallons, 2),
        "total_cost_usd": round(total_cost, 2),
        "stop_count": len(fuel_stops),
        "fuel_stops": fuel_stops,
        "note": "Truck starts with a full tank. Fuel already in the tank is not included in total_cost_usd.",
        "map_url": "/map/?" + urlencode({"start": start, "finish": finish}),
        "route": {
            "type": "LineString",
            "coordinates": _thin(route["coords"]),
        },
    }


def _thin(coords, limit=900):
    if not coords:
        return []
    if len(coords) <= limit:
        picked = coords
    else:
        step = (len(coords) - 1) / (limit - 1)
        picked = [coords[int(round(i * step))] for i in range(limit)]
        picked[-1] = coords[-1]
    return [[round(lng, 5), round(lat, 5)] for lng, lat in picked]


def _geocodes():
    global _geo_cache
    if _geo_cache is None:
        path = settings.BASE_DIR / "data" / "geocode_cache.json"
        if path.exists():
            _geo_cache = json.loads(path.read_text())
        else:
            _geo_cache = {}
    return _geo_cache


def _get_json(url, error_cls):
    req = Request(url, headers={"User-Agent": UA})
    try:
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urlopen(req, timeout=25, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise error_cls("Map service didn't respond. Try again.") from exc
