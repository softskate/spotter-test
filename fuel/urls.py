from django.urls import path

from fuel import views

urlpatterns = [
    path("", views.map_page, name="home"),
    path("map/", views.map_page, name="map"),
    path("api/route/", views.route_api, name="route"),
]
