import os
from location import models
from django.contrib.auth import get_user_model

User = get_user_model()

# This script add bulk of cities
# This presuppose a fixtures/cities.csv file exists.
# Consider that existe a user with id=1


def run(*args):
    user_id = 1

    # Delete all cities
    models.City.objects.all().delete()

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/cities.csv", 'r') as fp:
        for line in fp.readlines():
            name = line.strip()

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)


            models.City(name=name, creator=creator).save()
