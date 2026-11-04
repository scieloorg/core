from django.test import TestCase

from article.tasks import (
    get_researcher_identifier_unnormalized,
    normalize_stored_email,
)
from researcher.models import ResearcherIdentifier


class NormalizeEmailResearcherIdentifierTest(TestCase):
    def setUp(self):
        self.emails = [
            '<a href="mailto:jgarrido@ucv.cl">jgarrido@ucv.cl</a>',
            '<a href="mailto:gagopa39@hotmail.com">gagopa39@hotmail.com</a>',
            " herbet@ufs.br",
            "pilosaperez@gmail.com.",
            "cortes- camarillo@hotmail.com",
            "ulrikekeyser@upn162-zamora.edu.mx",
            "cortescamarillo@hotmail.com",
            "candelariasgro@yahoo.com",
            'mailto:user@hotmail.com">gagopa39@hotmail.com</a>',
        ]

        self.orcids = [
            "0000-0002-9147-0547",
            "0000-0003-3622-3428",
            "0000-0002-4842-3331",
            "0000-0003-1314-4073",
        ]
        ResearcherIdentifier.objects.bulk_create(
            [
                ResearcherIdentifier(identifier=email, source_name="EMAIL")
                for email in self.emails
            ]
        )
        ResearcherIdentifier.objects.bulk_create(
            [
                ResearcherIdentifier(identifier=orcid, source_name="ORCID")
                for orcid in self.orcids
            ]
        )

    def test_normalize_stored_email(self):
        unnormalized_identifiers = get_researcher_identifier_unnormalized()
        self.assertEqual(6, unnormalized_identifiers.count())

        normalize_stored_email()

        normalized_emails = [
            "jgarrido@ucv.cl",
            "gagopa39@hotmail.com",
            "herbet@ufs.br",
            "pilosaperez@gmail.com",
            "cortes-camarillo@hotmail.com",
            "user@hotmail.com",
        ]

        for email in normalized_emails:
            with self.subTest(email=email):
                self.assertTrue(
                    ResearcherIdentifier.objects.filter(identifier=email).exists(),
                    f"E-mail '{email}' unnormalized",
                )