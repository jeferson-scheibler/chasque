from django.urls import path

from . import views

urlpatterns = [
    path("agenda/", views.AgendaView.as_view()),
    path("agenda/ler/", views.LerAgendaView.as_view()),
    path("roteiros/", views.RoteirosView.as_view()),
    path("roteiros/<int:pk>/", views.RoteiroView.as_view()),
    path("avisos/", views.AvisosView.as_view()),
    path("avisos/teste/", views.AvisoTesteView.as_view()),
]
