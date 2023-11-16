from article import models
from institution.models import Institution
from issue.models import TocSection
from journal.models import (
    AMJournal,
    CopyrightHolderHistory,
    Journal,
    OfficialJournal,
    OwnerHistory,
    PublisherHistory,
    SciELOJournal,
    SponsorHistory,
    WebOfKnowledgeSubjectCategory,
)
from location.models import City, Country, CountryName, Location, State
from tracker.models import UnexpectedEvent
from vocabulary.models import Vocabulary


def run():
    models.Article.objects.all().delete()
    models.ArticleType.objects.all().delete()
    models.DOI.objects.all().delete()
    models.ArticleFunding.objects.all().delete()
    TocSection.objects.all().delete()
    models.License.objects.all().delete()
    models.Keyword.objects.all().delete()
    models.Researcher.objects.all().delete()
    models.DocumentTitle.objects.all().delete()
    models.Issue.objects.all().delete()
    models.Sponsor.objects.all().delete()
    Institution.objects.all().delete()
    Journal.objects.all().delete()
    SciELOJournal.objects.all().delete()
    OfficialJournal.objects.all().delete()
    SponsorHistory.objects.all().delete()
    OwnerHistory.objects.all().delete()
    PublisherHistory.objects.all().delete()
    CopyrightHolderHistory.objects.all().delete()
    Vocabulary.objects.all().delete()
    Country.objects.all().delete()
    UnexpectedEvent.objects.all().delete()
    CountryName.objects.all().delete()
    City.objects.all().delete()
    State.objects.all().delete()
    Location.objects.all().delete()
    AMJournal.objects.all().delete()
    WebOfKnowledgeSubjectCategory.objects.all().delete()
