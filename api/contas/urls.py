from django.urls import path

from . import views

urlpatterns = [
    path("auth/cadastro/", views.CadastroView.as_view()),
    path("auth/entrar/", views.EntrarView.as_view()),
    path("auth/renovar/", views.RenovarView.as_view()),
    path("auth/sair/", views.SairView.as_view()),
    path("me/", views.MeView.as_view()),
    path("me/exportar/", views.ExportarView.as_view()),
]
