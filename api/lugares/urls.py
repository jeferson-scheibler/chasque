from django.urls import path

from . import views

urlpatterns = [
    path("lugares/", views.LugaresView.as_view()),
    path("cidades/", views.CidadesView.as_view()),
]
