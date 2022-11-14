import os

from django.contrib.auth import get_user_model

from thematic_areas.models import GenericThematicArea


User = get_user_model()

# This script add bulk of countries
# This presuppose a fixtures/thematic_areas.csv file exists.
# Consider that exist a user with id=1

SEPARATOR = ';'


def run(*args):
    user_id = 1

    # Delete all cities
    GenericThematicArea.objects.all().delete()

    lang, origin = 'pt', 'CAPES'

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/thematic_areas.csv", 'r') as fp:
        for line in fp.readlines():
            text, level0, level1, level2 = line.strip().split(SEPARATOR)

            # User
            if args:
                user_id = args[0]

            creator = User.objects.get(id=user_id)

            GenericThematicArea(text=text, lang=lang, origin=origin, level0=level0, level1=level1,
                                level2=level2, creator=creator).save()
