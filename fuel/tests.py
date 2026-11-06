from django.test import SimpleTestCase

from fuel.planner import plan_stops
from fuel.stations import load_stations


class PlannerTests(SimpleTestCase):
    def test_short_trip_needs_no_stop(self):
        stops = plan_stops([{"mile": 100, "price": 3.5, "name": "A"}], 320)
        self.assertEqual(stops, [])

    def test_picks_the_cheaper_stop(self):
        stations = [
            {"mile": 400, "price": 5.0, "name": "pricey"},
            {"mile": 450, "price": 2.0, "name": "cheap"},
        ]
        stops = plan_stops(stations, 800)
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0]["name"], "cheap")
        # 350 miles left to the finish, 50 still in the tank -> 30 gallons
        self.assertAlmostEqual(stops[0]["gallons"], 30.0)
        self.assertAlmostEqual(stops[0]["cost"], 60.0)

    def test_ignores_a_stop_that_cannot_reach_anything_else(self):
        # mile 100 can only see out to 600, and the next stop is 750
        stations = [
            {"mile": 100, "price": 1.0, "name": "trap"},
            {"mile": 750, "price": 2.0, "name": "too far"},
        ]
        self.assertIsNone(plan_stops(stations, 1100))

    def test_buys_only_enough_to_reach_a_cheaper_stop(self):
        stations = [
            {"mile": 300, "price": 4.0, "name": "first"},
            {"mile": 700, "price": 1.0, "name": "second"},
        ]
        stops = plan_stops(stations, 900)
        self.assertEqual([s["name"] for s in stops], ["first", "second"])
        # arrive at mile 300 with 200 miles left, need 400 to reach the cheap stop
        self.assertAlmostEqual(stops[0]["gallons"], 20.0)
        self.assertAlmostEqual(stops[1]["gallons"], 20.0)

    def test_impossible_without_stations(self):
        self.assertIsNone(plan_stops([], 1200))


class StationLoadTests(SimpleTestCase):
    def test_prices_match_to_coords(self):
        stations, grid = load_stations()
        self.assertGreater(len(stations), 3000)
        self.assertTrue(grid)
        chicago = [s for s in stations if s["city"] == "Chicago" and s["state"] == "IL"]
        self.assertEqual(len(chicago), 1)
        self.assertAlmostEqual(chicago[0]["lat"], 41.84, places=1)
