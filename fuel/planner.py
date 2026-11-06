# Tank starts full. That fuel is not billed.
# While the finish is out of range, stop at the cheapest station
# we can still reach that doesn't leave us stuck.

MAX_RANGE = 500.0  # miles
MPG = 10.0


def can_continue(station, stations, total):
    reach = station["mile"] + MAX_RANGE
    if reach >= total - 0.1:
        return True
    for other in stations:
        if station["mile"] + 0.1 < other["mile"] <= reach + 0.1:
            return True
    return False


def plan_stops(stations, total):
    pos = 0.0
    fuel = MAX_RANGE
    stops = []
    steps = 0

    while pos + fuel < total - 0.1:
        steps += 1
        if steps > len(stations) + 2:
            return None

        reachable = []
        for station in stations:
            if pos + 0.1 < station["mile"] <= pos + fuel + 0.1 and can_continue(station, stations, total):
                reachable.append(station)
        if not reachable:
            return None

        # same price: take the one further down the road
        chosen = min(reachable, key=lambda s: (s["price"], -s["mile"]))
        fuel -= chosen["mile"] - pos
        pos = chosen["mile"]

        target = _buy_target(pos, chosen["price"], stations, total)
        need = target - pos
        if fuel >= need - 0.1:
            continue

        buy_miles = min(need - fuel, MAX_RANGE - fuel)
        if buy_miles <= 0.2:
            return None

        gallons = buy_miles / MPG
        stop = dict(chosen)
        stop["gallons"] = gallons
        stop["cost"] = gallons * chosen["price"]
        stops.append(stop)
        fuel += buy_miles

    return stops


def _buy_target(pos, price, stations, total):
    # only enough fuel to reach the next cheaper stop, if there is one
    cheaper_mile = None
    window = pos + MAX_RANGE
    for station in stations:
        if not (pos + 0.1 < station["mile"] <= window + 0.1):
            continue
        if station["price"] >= price - 0.0001:
            continue
        if not can_continue(station, stations, total):
            continue
        if cheaper_mile is None or station["mile"] < cheaper_mile:
            cheaper_mile = station["mile"]
    if cheaper_mile is not None:
        return cheaper_mile
    if total <= window + 0.1:
        return total
    return window
