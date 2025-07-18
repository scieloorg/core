import logging
import sys

from core.mongodb import write_to_db
from core.utils import date_utils
from journal.models import SciELOJournal, SciELOJournalExport
from tracker.models import UnexpectedEvent


