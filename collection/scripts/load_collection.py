from django.contrib.auth import get_user_model

from collection import controller


User = get_user_model()


def run(*args):
    user_id = args[0] if args else 1

    user = User.objects.get(id=user_id)

    controller.load(user)
