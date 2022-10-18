import os
from location import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of states
# This presuppose a fixtures/states.csv file exists.
# Consider that existe a user with id=1

SEPARATOR = ';'

def run(*args):
    user_id = 1

    # Delete all cities
    models.State.objects.all().delete()

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/states.csv", 'r') as fp:
        for line in fp.readlines():
            name, acron, region = line.strip().split(SEPARATOR)

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)

            models.State(name=name, acronym=acron, region=region, creator=creator).save()
