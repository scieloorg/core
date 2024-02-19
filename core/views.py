import redis

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import render
from django.contrib import messages

from config.settings.base import REDIS_HOST, REDIS_PORT


def clean_database_redis(request):
    redis_host = REDIS_HOST
    redis_port = REDIS_PORT
    redis_db = 0
    try:
        r = redis.StrictRedis(
            host=redis_host, port=redis_port, db=redis_db, decode_responses=True
        )
        r.flushdb()
        messages.success(request, "A base de dados Redis foi limpa com sucesso!")
    except redis.ConnectionError as e:
        messages.error(
            request, "Falha na conexão: Não foi possível limpar a base de dados Redis."
        )
    except Exception as e:
        messages.error(request, f"Erro ao limpar a base de dados Redis: {e}")
    return HttpResponseRedirect(reverse("wagtailadmin_home"))


def confirm_clean_database_redis(request):
    if request.method == "POST":
        if request.POST.get("action") == "delete":
            clean_database_redis(request)
    return render(request, "confirm_clean_database_redis.html")
