from django.urls import path

from . import views

urlpatterns = [
    path("registros/", views.RegistrosView.as_view()),
    path("registros/<int:pk>/", views.RegistroView.as_view()),
    path("sugestoes/", views.SugestoesView.as_view()),
    path("me/preferencias/", views.PreferenciasView.as_view()),
]
