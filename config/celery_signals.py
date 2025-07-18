# myproject/celery_signals.py (ou myproject/utils/celery_signals.py)

from celery.signals import task_postrun
from django.db import close_old_connections
import logging

logger = logging.getLogger(__name__)

@task_postrun.connect
def close_db_connections(**kwargs):
    """
    Função que será executada após cada tarefa Celery.
    Fecha as conexões de banco de dados antigas ou ociosas.
    """
    try:
        close_old_connections()
        logger.debug("Conexões de banco de dados antigas fechadas após a tarefa Celery.")
    except Exception as e:
        logger.error(f"Erro ao fechar conexões de banco de dados após a tarefa Celery: {e}")