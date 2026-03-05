from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST


@login_required
@require_POST
def deposit_article_to_crossref(request, article_id):
    """
    Triggers an asynchronous Crossref DOI deposit for the given article.

    The task is dispatched via Celery and a JSON response is returned
    immediately indicating that the deposit has been queued.
    """
    from article.models import Article
    from doi_manager.tasks import task_deposit_doi_to_crossref

    get_object_or_404(Article, pk=article_id)

    task = task_deposit_doi_to_crossref.delay(
        article_id=article_id,
        user_id=request.user.id,
        username=request.user.username,
    )

    return JsonResponse(
        {
            "message": str(_("Crossref deposit queued successfully")),
            "task_id": task.id,
            "article_id": article_id,
        }
    )
