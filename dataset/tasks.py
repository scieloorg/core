from django.contrib.auth import get_user_model
from config import celery_app
from dataset.sources.dataverse import load_from_data_scielo

User = get_user_model()


def _get_user(request, username=None, user_id=None):
    try:
        return User.objects.get(pk=request.user.id)
    except AttributeError:
        if user_id:
            return User.objects.get(pk=user_id)
        if username:
            return User.objects.get(username=username)


@celery_app.task(bind=True)
def load_dataset(self, user_id=None):
    # TODO
    # Pgar usuario da sessao
    user = User.objects.first()
    load_from_data_scielo(user)
