import csv
import os

from institution import models
from location.models import Location, Country, State

from django.contrib.auth import get_user_model


User = get_user_model()


def run(*args):
    user_id = 1

    # Delete all institutions
    models.Institution.objects.all().delete()

    # User
    if args:
        user_id = args[0]

    creator = User.objects.get(id=user_id)

    with open(os.path.dirname(os.path.realpath(__file__)) + "/../fixtures/institutions.csv", 'r') as csvfile:
        data = csv.DictReader(csvfile, delimiter=";")

        try:
            for line, row in enumerate(data):
                inst = models.Institution()
                inst.name = row['Name']
                inst.institution_type = row['Institution Type']
                inst.acronym = row['Acronym']
                inst.level_1 = row['Level_1']
                inst.level_2 = row['Level_2']
                inst.level_3 = row['Level_3']
                inst.location = Location.get_or_create(user=creator,
                                                       location_country=Country.get_or_create(user=creator, name="Brasil", acronym='BR'),
                                                       location_state=State.get_or_create(user=creator, acronym=row['State Acronym']),
                                                       location_city=None)
                inst.creator = creator
                inst.save()

        except Exception as ex:
            print("Import error: %s, Line: %s, Data: %s" % (ex, str(line + 2), row))
        else:
            print("File imported successfully!")

