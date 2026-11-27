from rest_framework import serializers

from lugares import horarios
from lugares.serializers import LugarSerializer
from salvos.intencoes import frases_por_lugar
from salvos.models import Salvo

from .models import Agenda, Roteiro
from .roteiros import km


class AgendaSerializer(serializers.ModelSerializer):
    """O endereço secreto nunca volta: só o domínio, para a pessoa reconhecer de onde vem."""

    class Meta:
        model = Agenda
        fields = ["servico", "lida_em", "erro", "dias_livres"]


class RoteiroSerializer(serializers.ModelSerializer):
    paradas = serializers.SerializerMethodField()
    visto = serializers.SerializerMethodField()

    class Meta:
        model = Roteiro
        fields = ["id", "dia", "cidade", "viagem", "visto", "paradas"]

    def get_visto(self, roteiro):
        return roteiro.visto_em is not None

    def get_paradas(self, roteiro):
        paradas = list(roteiro.paradas.all())
        ids = [p.lugar_id for p in paradas]
        # link salvo mais recente de cada lugar, para abrir a página dele no app
        salvos = {}
        for s in Salvo.objects.filter(usuario_id=roteiro.usuario_id, lugar_id__in=ids).order_by("criado_em"):
            salvos[s.lugar_id] = s.id
        frases = frases_por_lugar(roteiro.usuario_id, ids)
        saida = []
        for i, p in enumerate(paradas):
            saida.append({
                "lugar": LugarSerializer(p.lugar).data,
                "momento": p.momento,
                "salvo": p.salvo,
                "salvo_id": salvos.get(p.lugar_id),
                # por que a pessoa quis ir, quando o link tem um motivo lido ou confirmado
                "intencao": frases.get(p.lugar_id, ""),
                "horario": horarios.texto_do_dia(p.lugar.horario, roteiro.dia),
                "km_da_anterior": round(km(paradas[i - 1].lugar, p.lugar), 1) if i else None,
            })
        return saida
