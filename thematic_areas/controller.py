import os

from models import GenericThematicArea


# This script add bulk of thematic areas
# This presuppose a fixtures/thematic_areas.csv file exists.
# Consider that exist a user with id=1

SEPARATOR = ';'


def load_thematic_area(user):
    lang, origin = 'pt', 'CAPES'

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/thematic_areas.csv", 'r') as data:
        for row in data.readlines():
            for level in range(len(row)):
                try:
                    level_up = GenericThematicArea.objects.get(
                        text=row.split(SEPARATOR)[level - 1].rstrip('\n'),
                        lang=lang,
                        origin=origin,
                        level=level - 1
                    )
                except Exception:
                    level_up = None

                GenericThematicArea.get_or_create(
                    text=row.split(SEPARATOR)[level].rstrip('\n'),
                    lang=lang,
                    origin=origin,
                    level=level,
                    level_up=level_up,
                    user=user
                )
