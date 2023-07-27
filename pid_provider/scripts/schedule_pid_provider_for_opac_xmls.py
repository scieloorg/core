from django.utils.translation import gettext_lazy as _

from core.utils import scheduler


def run(username, begin_date, end_date, limit, pages):
    # deixa a task agendada
    scheduler.schedule_task(
        task="provide_pid_for_opac_xmls",
        name=_("Registra XML do site www.scielo.br no pid provider"),
        kwargs={
            "username": username,
            "begin_date": None,
            "end_date": None,
            "limit": int(limit),
            "pages": int(pages),
        },
        description=_(
            "Executa diariamente às 23h UTC a carga de XML atualizados de 30 anteriores até hoje"
        ),
        priority=1,
        enabled=True,
        run_once=False,
        day_of_week=None,
        hour=22,
        minute=0,
    )
