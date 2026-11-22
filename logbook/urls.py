from django.contrib.auth import views as auth_views
from django.urls import path

from . import pwa, views

urlpatterns = [
    path("", views.session_list, name="session_list"),
    path("manifest.webmanifest", pwa.manifest, name="manifest"),
    path("sessions/new/", views.session_create, name="session_create"),
    path("sessions/<int:pk>/", views.session_detail, name="session_detail"),
    path("sessions/<int:pk>/ascents/new/", views.ascent_create, name="ascent_create"),
    path("sessions/<int:pk>/ascents/form/", views.ascent_form, name="ascent_form"),
    path("sessions/<int:pk>/routes/search/", views.route_search, name="route_search"),
    path("sessions/<int:pk>/edit/", views.session_edit, name="session_edit"),
    path("sessions/<int:pk>/delete/", views.session_delete, name="session_delete"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
