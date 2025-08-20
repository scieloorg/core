# myproject/celery_signals.py (ou myproject/utils/celery_signals.py)

from celery.signals import worker_process_init, task_prerun, task_postrun
from django.db import close_old_connections
import logging

logger = logging.getLogger(__name__)


def _close_old_connections():
    try:
        close_old_connections()
        logger.info("Conexões de banco de dados antigas fechadas após a tarefa Celery.")
    except Exception as e:
        logger.error(f"Erro ao fechar conexões de banco de dados após a tarefa Celery: {e}")


@worker_process_init.connect
def close_connections(**kwargs):
    """Fecha conexões quando o worker é iniciado"""
    _close_old_connections()

@task_prerun.connect
def close_connections_task_prerun(**kwargs):
    """Fecha conexões antes de cada task"""
    _close_old_connections()

@task_postrun.connect
def close_connections_task_postrun(**kwargs):
    _close_old_connections()
