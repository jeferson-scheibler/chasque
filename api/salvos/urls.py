from django.urls import path

from . import views

urlpatterns = [
    path("salvos/", views.SalvosView.as_view()),
    path("salvos/<int:pk>/", views.SalvoView.as_view()),
    path("salvos/<int:pk>/intencao/", views.IntencaoView.as_view()),
    path("meus-lugares/", views.MeusLugaresView.as_view()),
]
