from django.urls import path

from . import views

urlpatterns = [
    path("pessoas/", views.PessoasView.as_view()),
    path("pessoas/convite/novo/", views.NovoConviteView.as_view()),
    # <id da pessoa>: as visitas que ela liberou para mim
    path("pessoas/<int:pk>/visitas/", views.VisitasDaPessoaView.as_view()),
    # <id da ligação de confiança>: aceitar pedido, ou desfazer (recusar, cancelar, deixar de seguir, remover)
    path("confiancas/<int:pk>/aceitar/", views.AceitarView.as_view()),
    path("confiancas/<int:pk>/", views.ConfiancaView.as_view()),
    path("convites/<str:codigo>/", views.ConviteView.as_view()),
]
