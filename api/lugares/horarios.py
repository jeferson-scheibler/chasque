"""Horário de funcionamento, no formato `opening_hours` do OpenStreetMap.

Entende o que cobre quase tudo que bares, lanchonetes e cafés escrevem:

    24/7
    Mo-Fr 08:00-18:00; Sa 09:00-13:00
    Mo,We,Fr 11:00-14:00,18:00-23:00; Tu off
    Su-Th 18:00-02:00          (passa da meia-noite: vale para o dia em que abre)
    Mo-Fr 11:30-14:30, Sa 12:00-00:00   (vírgula antes de um dia: regra que se soma)

Qualquer coisa fora disso (meses, semanas, nascer do sol, "08:00+", feriados sozinhos) devolve `None`,
ou seja, "não sei": é melhor dizer que não se sabe do que errar se o lugar está aberto. Feriados (PH) e
férias (SH) são ignorados. Se o texto lista dias e deixa um de fora, esse dia conta como fechado, que é a
regra do OSM.
"""

import re
from functools import lru_cache

DIAS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
NOMES = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]

_INTERVALO = r"\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}"
_REGRA = re.compile(
    rf"^(?:(?P<dias>[A-Za-z][A-Za-z,\- ]*?)\s+)?"
    rf"(?P<horas>off|closed|open|24/7|{_INTERVALO}(?:\s*,\s*{_INTERVALO})*)$",
    re.IGNORECASE,
)
_DESCONHECIDO = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|week|sunrise|sunset|dawn|dusk|easter|\[|\+|\|\||\d{4})",
    re.IGNORECASE,
)


def _minutos(texto):
    h, m = texto.split(":")
    return int(h) * 60 + int(m)


def _intervalos(horas):
    saida = []
    for par in horas.split(","):
        ini, fim = (_minutos(p.strip()) for p in par.split("-"))
        if ini >= 24 * 60 or fim > 24 * 60 + 12 * 60 or ini == fim:
            raise ValueError
        saida.append((ini, fim if fim > ini else fim + 24 * 60))  # 18:00-02:00 vira (1080, 1560)
    return sorted(saida)


def _dias(seletor):
    """'Mo-Fr,Su' -> {0, 1, 2, 3, 4, 6}. PH e SH são ignorados. Levanta ValueError se não entender."""
    dias = set()
    for parte in (p.strip() for p in seletor.split(",") if p.strip()):
        if parte.upper() in ("PH", "SH"):
            continue
        ponta = [p.strip().capitalize() for p in parte.split("-")]
        if len(ponta) > 2 or any(p not in DIAS for p in ponta):
            raise ValueError
        ini = DIAS.index(ponta[0])
        fim = DIAS.index(ponta[-1])
        while True:  # Fr-Mo dá a volta na semana
            dias.add(ini)
            if ini == fim:
                break
            ini = (ini + 1) % 7
    return dias


@lru_cache(maxsize=4096)
def interpretar(horario):
    """{0..6: [(inicio, fim) em minutos]} ou None se não entender. Dia sem regra fica fechado."""
    texto = re.sub(r'"[^"]*"', "", horario or "").strip().rstrip(";").strip()
    if not texto or _DESCONHECIDO.search(texto):
        return None
    semana = {d: [] for d in range(7)}
    viu_dia = False
    regras = []
    for regra in (r.strip() for r in texto.split(";") if r.strip()):
        # "Mo-Fr 11:00-14:00, Sa 12:00-23:00": a vírgula antes de um dia junta uma regra a mais, sem apagar
        # (só depois de um horário ou de "off": em "Sa, Su 10:00-22:00" a vírgula separa dias do mesmo seletor)
        partes = re.split(r"(?:(?<=\d:\d\d)|(?<=off))\s*,\s*(?=(?:Mo|Tu|We|Th|Fr|Sa|Su|PH|SH)\b)", regra)
        regras += [(parte.strip(), i > 0) for i, parte in enumerate(partes)]
    for regra, somar in regras:
        m = _REGRA.match(regra)
        if not m:
            return None
        horas = m.group("horas").lower()
        try:
            dias = _dias(m.group("dias")) if m.group("dias") else set(range(7))
            if horas in ("off", "closed"):
                intervalos = []
            elif horas in ("24/7", "open"):
                intervalos = [(0, 24 * 60)]
            else:
                intervalos = _intervalos(horas)
        except ValueError:
            return None
        if m.group("dias") and not dias:
            continue  # só feriados: não muda a semana
        viu_dia = True
        for d in dias:
            # depois de ";" a regra mais nova substitui; depois de "," ela se soma
            semana[d] = sorted(semana[d] + intervalos) if somar and intervalos else intervalos
    return semana if viu_dia else None


MADRUGADA_LONGA = 6 * 60  # virada da noite anterior que vai além das 06:00 conta como dia aberto


def _virada(ontem):
    """Fim do intervalo de ontem que passa da meia-noite e vai além das 06:00 (em minutos do dia), ou None."""
    fins = [fim - 24 * 60 for _, fim in ontem if fim > 24 * 60 + MADRUGADA_LONGA]
    return max(fins) if fins else None


def estado(horario, data, hora=None):
    """'aberto', 'fechado' ou None (não sei). `data` é date; `hora` é minutos desde 00:00 ou None."""
    semana = interpretar(horario)
    if semana is None:
        return None
    dia = data.weekday()
    ontem = semana[(dia - 1) % 7]
    if hora is None:
        # "Su 18:00-02:00" não abre a segunda: o resto da madrugada não conta como dia aberto. Só conta se a
        # virada for até de manhã (MADRUGADA_LONGA), o que é raro.
        return "aberto" if semana[dia] or _virada(ontem) else "fechado"
    if any(ini <= hora < fim for ini, fim in semana[dia]):
        return "aberto"
    if any(fim > 24 * 60 and hora + 24 * 60 < fim for _, fim in ontem):
        return "aberto"
    return "fechado"


def _hhmm(minutos):
    minutos %= 24 * 60
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def texto_do_dia(horario, data):
    """'11:00 às 14:00 e 18:00 às 23:00', 'o dia todo', ou '' se fechado ou desconhecido."""
    semana = interpretar(horario)
    if not semana:
        return ""
    partes = semana[data.weekday()]
    if not partes:
        virada = _virada(semana[(data.weekday() - 1) % 7])
        return f"até {_hhmm(virada)}" if virada else ""
    if partes == [(0, 24 * 60)]:
        return "o dia todo"
    return " e ".join(f"{_hhmm(ini)} às {_hhmm(fim)}" for ini, fim in partes)
