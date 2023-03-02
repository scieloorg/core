import os
import csv

from thematic_areas.models import GenericThematicArea


# This script add bulk of thematic areas
# This presuppose a fixtures/thematic_areas.csv file exists.
# Consider that exist a user with id=1

SEPARATOR = ";"


def load_thematic_area(user):
    lang, origin = "pt", "CAPES"

    with open(
        os.path.dirname(os.path.realpath(__file__)) + "/./fixtures/thematic_areas.csv",
        "r",
    ) as csvfile:
        data = csv.reader(csvfile, delimiter=SEPARATOR)
        for row in data:
            for level in range(len(row)):
                if row[level]:
                    if level > 0:
                        level_up = GenericThematicArea.objects.get(
                            text=row[level - 1].rstrip("\n"),
                            lang=lang,
                            origin=origin,
                            level=level - 1,
                        )
                    else:
                        level_up = None

                    GenericThematicArea.get_or_create(
                        text=row[level].rstrip("\n"),
                        lang=lang,
                        origin=origin,
                        level=level,
                        level_up=level_up,
                        user=user,
                    )
