import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from fuel.route import LocationError, RouteError, build_route


@csrf_exempt
def route_api(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode() or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Request body is not valid JSON."}, status=400)
        start = body.get("start") or ""
        finish = body.get("finish") or ""
    elif request.method == "GET":
        start = request.GET.get("start") or ""
        finish = request.GET.get("finish") or ""
    else:
        return JsonResponse({"error": "Use GET or POST."}, status=405)

    start, finish = start.strip(), finish.strip()
    if not start or not finish:
        return JsonResponse({"error": "Both start and finish are required."}, status=400)
    if len(start) > 120 or len(finish) > 120:
        return JsonResponse({"error": "Location text is too long."}, status=400)

    try:
        payload = build_route(start, finish)
    except LocationError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except RouteError as exc:
        return JsonResponse({"error": str(exc)}, status=502)
    return JsonResponse(payload)


def map_page(request):
    response = render(request, "map.html", {
        "start": request.GET.get("start", ""),
        "finish": request.GET.get("finish", ""),
    })
    # OSM tile servers refuse requests that omit Referer. Django's default
    # same-origin policy strips it on this cross-origin request.
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
