"""Leitura da agenda pelo endereço secreto em formato iCal (Google, Outlook, iCloud).

O servidor baixa o arquivo, então o endereço é tratado como entrada de risco (SSRF): só HTTPS na porta
443, o nome precisa resolver para IPs públicos, a conexão vai direto ao IP conferido (sem uma segunda
consulta ao DNS no meio), redirecionamentos são conferidos de novo, e o tamanho e o tempo são limitados.

Do arquivo só saem intervalos ocupados. Eventos marcados como "livre" (TRANSP:TRANSPARENT) e cancelados
não contam.
"""

import http.client
import ipaddress
import socket
import ssl
from datetime import date, datetime, time, timedelta
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import icalendar
import recurring_ical_events
from django.conf import settings

TAMANHO_MAXIMO = 5 * 1024 * 1024
TEMPO_LIMITE = 10
REDIRECIONAMENTOS = 3


class AgendaInvalida(Exception):
    """Mensagem já pronta para mostrar à pessoa."""


def normalizar(url):
    url = (url or "").strip()
    if url.lower().startswith("webcal://"):
        url = "https://" + url[len("webcal://"):]
    partes = urlsplit(url)
    if partes.scheme != "https" or not partes.hostname:
        raise AgendaInvalida("Use o endereço que começa com https:// ou webcal://.")
    if partes.port not in (None, 443) or partes.username or partes.password:
        raise AgendaInvalida("Esse endereço não parece ser de uma agenda.")
    return url


def _ips_publicos(host):
    try:
        enderecos = {info[4][0] for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except (socket.gaierror, UnicodeError):
        raise AgendaInvalida("Não encontrei o servidor dessa agenda.")
    ips = [ipaddress.ip_address(e.split("%")[0]) for e in enderecos]
    if not ips or not all(ip.is_global for ip in ips):
        raise AgendaInvalida("Esse endereço não parece ser de uma agenda.")
    return [str(ip) for ip in sorted(ips, key=lambda ip: (ip.version, str(ip)))]  # IPv4 primeiro


class _Conexao(http.client.HTTPSConnection):
    """HTTPS para um IP já conferido, com o certificado validado pelo nome original."""

    def __init__(self, host, ips, **kwargs):
        super().__init__(host, 443, timeout=TEMPO_LIMITE, context=ssl.create_default_context(), **kwargs)
        self._ips = ips

    def connect(self):
        erro = None
        for ip in self._ips:
            try:
                bruto = socket.create_connection((ip, 443), self.timeout)
                break
            except OSError as e:
                erro = e
        else:
            raise erro
        self.sock = self._context.wrap_socket(bruto, server_hostname=self.host)


def baixar(url):
    """Bytes do arquivo .ics. Levanta AgendaInvalida com uma mensagem amigável."""
    url = normalizar(url)
    for _ in range(REDIRECIONAMENTOS + 1):
        partes = urlsplit(url)
        conexao = _Conexao(partes.hostname, _ips_publicos(partes.hostname))
        caminho = partes.path or "/"
        if partes.query:
            caminho += "?" + partes.query
        try:
            conexao.request("GET", caminho, headers={"User-Agent": "Chasque/1.0", "Accept": "text/calendar"})
            resposta = conexao.getresponse()
            if resposta.status in (301, 302, 303, 307, 308):
                destino = resposta.getheader("Location", "")
                url = normalizar(urljoin(url, destino))
                continue
            if resposta.status in (401, 403, 404):
                raise AgendaInvalida("A agenda não abriu. Confira se copiou o endereço secreto inteiro.")
            if resposta.status != 200:
                raise AgendaInvalida("O servidor da agenda não respondeu agora. Tente de novo mais tarde.")
            dados = resposta.read(TAMANHO_MAXIMO + 1)
        except (OSError, http.client.HTTPException):
            raise AgendaInvalida("Não consegui falar com o servidor da agenda.")
        finally:
            conexao.close()
        if len(dados) > TAMANHO_MAXIMO:
            raise AgendaInvalida("Essa agenda é grande demais para ler.")
        if b"BEGIN:VCALENDAR" not in dados[:2048]:
            raise AgendaInvalida("Esse endereço não devolveu uma agenda no formato iCal.")
        return dados
    raise AgendaInvalida("A agenda redirecionou vezes demais.")


def _quando(valor, fuso):
    if isinstance(valor, datetime):
        return valor if valor.tzinfo else valor.replace(tzinfo=fuso)
    return datetime.combine(valor, time.min, tzinfo=fuso)  # evento de dia inteiro


def ocupados(dados, inicio, fim):
    """[(início, fim)] em datetimes com fuso, dos eventos ocupados entre `inicio` e `fim` (datas)."""
    fuso = ZoneInfo(settings.TIME_ZONE)
    try:
        agenda = icalendar.Calendar.from_ical(dados)
        eventos = recurring_ical_events.of(agenda).between(inicio, fim)
    except Exception:  # arquivo quebrado ou regra de repetição que a biblioteca não entende
        raise AgendaInvalida("Não consegui ler os eventos dessa agenda.")
    saida = []
    for evento in eventos:
        if str(evento.get("TRANSP", "")).upper() == "TRANSPARENT":
            continue
        if str(evento.get("STATUS", "")).upper() == "CANCELLED":
            continue
        comeco = evento.get("DTSTART")
        if comeco is None:
            continue
        comeco = comeco.dt
        termino = evento.get("DTEND")
        if termino is not None:
            termino = termino.dt
        elif evento.get("DURATION") is not None:
            termino = comeco + evento.get("DURATION").dt
        else:
            termino = comeco + timedelta(days=1) if not isinstance(comeco, datetime) else comeco
        a, b = _quando(comeco, fuso), _quando(termino, fuso)
        if isinstance(comeco, date) and not isinstance(comeco, datetime) and b <= a:
            b = a + timedelta(days=1)
        saida.append((a, b))
    return sorted(saida)
