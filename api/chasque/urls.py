from django.contrib import admin
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path


def healthz(_request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "erro", "banco": "indisponivel"}, status=503)
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/healthz", healthz),
    path("api/", include("contas.urls")),
    path("api/", include("lugares.urls")),
    path("api/", include("salvos.urls")),
    path("admin/", admin.site.urls),
]
