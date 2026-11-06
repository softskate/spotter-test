# Fuel route

API for a drive inside the US. It returns the route, where to buy fuel, and what that fuel costs.

The truck holds 50 gallons (500 miles at 10 mpg) and leaves full. Fuel already in the tank is not added to the total.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export DJANGO_SECRET_KEY=change-me
export DJANGO_DEBUG=1
export DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

python manage.py migrate
python manage.py runserver
```

## Endpoints

GET `/api/route/?start=Chicago,%20IL&finish=Denver,%20CO`

POST `/api/route/`

```json
{"start": "Chicago, IL", "finish": "Denver, CO"}
```

Same trip on a map: `/map/?start=Chicago,%20IL&finish=Denver,%20CO`

## How the stops are chosen

The price CSV has no coordinates, so each stop is placed on its city (`data/city_coords.csv`).

Start and finish are geocoded once and cached. The driving route is a single request to the public OSRM server. Stops more than ~25 miles off the line are ignored (wider only if 500 miles wouldn't be enough to connect the gaps).

While the finish is still out of range, the next stop is the cheapest one we can reach that doesn't dead-end. If a cheaper stop is within 500 miles, we buy only enough to get there. Otherwise we fill the tank, or buy just enough to finish when the end is closer.
