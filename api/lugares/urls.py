from django.urls import path

from . import views

urlpatterns = [
    path("lugares/", views.LugaresView.as_view()),
    path("lugares/<int:pk>/", views.LugarView.as_view()),
    path("cidades/", views.CidadesView.as_view()),
    path("tags/", views.TagsView.as_view()),
]
