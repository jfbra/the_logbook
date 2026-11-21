from django.contrib.auth import views as auth_views
from django.urls import path

from . import pwa, views

urlpatterns = [
    path("", views.session_list, name="session_list"),
    path("manifest.webmanifest", pwa.manifest, name="manifest"),
    path("sessions/new/", views.session_create, name="session_create"),
    path("sessions/<int:pk>/edit/", views.session_edit, name="session_edit"),
    path("sessions/<int:pk>/delete/", views.session_delete, name="session_delete"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
]
