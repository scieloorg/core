from django.contrib.auth import get_user_model

from institution import models

User = get_user_model()


def run(username):
    user = User.objects.get(username=username)
    # models.InstitutionIdentification.objects.all().delete()
    # models.Institution.objects.all().delete()

    models.Institution.load(user)
