from issue.models import Issue
from .models import ScieloJournal

import csv
import os


def create_journals_kbart():
    records = []
    for journal in ScieloJournal.objects.all().iterator():
        last_date = 0
        first_date = 300000
        item = {
            'publication_title': journal.official.title,
            'print_identifier': journal.official.ISSN_print,
            'online_identifier': journal.official.ISSN_electronic
        }
        for issue in Issue.objects.filter(journal=journal).iterator():
            this_date = int(str(issue.year) + str(issue.month))
            if this_date > last_date:
                last_date = this_date
                last_issue = issue
            if this_date < first_date:
                first_date = this_date
                first_issue = issue
        item.update({
            'number_first_issue': first_issue.number,
            'volume_first_issue': first_issue.volume,
            'year_first_issue': first_issue.year,
            'month_first_issue': first_issue.month,
            'number_last_issue': last_issue.number,
            'volume_last_issue': last_issue.volume,
            'year_last_issue': last_issue.year,
            'month_last_issue': last_issue.month
        })
        records.append(item)

    with open(os.path.dirname(os.path.realpath(__file__)) + "/./fixtures/journals_kbart.csv", 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['publication_title', 'print_identifier', 'online_identifier',
                                                     'number_first_issue', 'volume_first_issue', 'year_first_issue',
                                                     'month_first_issue', 'number_last_issue', 'volume_last_issue',
                                                     'year_last_issue', 'month_last_issue'])
        writer.writeheader()
        writer.writerows(records)
