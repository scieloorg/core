from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtailautocomplete.edit_handlers import AutocompletePanel

from .models import Journal


class JournalProxyEditor(Journal):
    panels_titles = [
        AutocompletePanel("official", read_only=True),
        FieldPanel("title", read_only=True),
        FieldPanel("short_title"),
        InlinePanel("other_titles", label=_("Other titles")),
    ]

    panels_scope_and_about = [
        InlinePanel("mission", label=_("Mission")),
        InlinePanel("history", label=_("Brief History")),
        InlinePanel("focus", label=_("Focus and Scope")),
        AutocompletePanel("subject"),
        InlinePanel("thematic_area", label=_("Thematic Areas")),
        AutocompletePanel("subject_descriptor"),
        AutocompletePanel("wos_area"),
        AutocompletePanel("wos_db"),
        AutocompletePanel("indexed_at"),
        AutocompletePanel("additional_indexed_at"),
        AutocompletePanel("vocabulary"),
        InlinePanel("title_in_database", label=_("Title in Database")),
    ]

    panels_institutions = [
        InlinePanel("owner_history", label=_("Owner")),
        InlinePanel("publisher_history", label=_("Publisher")),
        InlinePanel("sponsor_history", label=_("Sponsor")),
        InlinePanel(
            "copyright_holder_history",
            label=_("Copyright Holder"),
        ),
    ]

    panels_website = [
        FieldPanel("contact_name"),
        FieldPanel("contact_address"),
        AutocompletePanel("contact_location"),
        InlinePanel("journal_email", label=_("Contact e-mail")),
        FieldPanel("logo", heading=_("Logo")),
        # FieldPanel("journal_url"),
        InlinePanel(
            "related_journal_urls", label=_("Journal Urls")
        ),
        FieldPanel("submission_online_url"),
        FieldPanel("main_collection"),
        InlinePanel("journalsocialnetwork", label=_("Social Network")),
        FieldPanel("frequency"),
        FieldPanel("publishing_model"),
        FieldPanel("standard"),
    ]

    panels_open_science = [
        FieldPanel("open_access"),
        FieldPanel("url_oa"),
        InlinePanel(
            "file_oa", label=_("Open Science accordance form")
        ),
        FieldPanel("journal_use_license"),
        InlinePanel("open_access_text", label=_("Open Access")),
        InlinePanel("open_data", label=_("Open data")),
        InlinePanel("preprint", label=_("Preprint")),
        InlinePanel("review", label=_("Peer review")),
        InlinePanel(
            "open_science_compliance",
            label=_("Open Science Compliance"),
        ),
    ]

    panels_policy = [
        InlinePanel(
            "ethics",
            label=_("Ethics"),
        ),
        InlinePanel(
            "ecommittee",
            label=_("Ethics Committee"),
        ),
        InlinePanel(
            "copyright",
            label=_("Copyright"),
        ),
        InlinePanel(
            "website_responsibility",
            label=_("Intellectual Property / Terms of use / Website responsibility"),
        ),
        InlinePanel(
            "author_responsibility",
            label=_("Intellectual Property / Terms of use / Author responsibility"),
        ),
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
        ),
        AutocompletePanel("digital_pa"),
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
        ),
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
        ),
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
        ),
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
        ),
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
        ),
        InlinePanel(
            "editorial_policy",
            label=_("Editorial Policy"),
        ),
        InlinePanel(
            "artificial_intelligence",
            label=_("Artificial Intelligence"),
        ),
    ]
    panels_notes = [InlinePanel("annotation", label=_("Notes"))]

    panels_instructions_for_authors = [
        InlinePanel(
            "accepted_documment_types",
            label=_("Accepted Document Types"),
        ),
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
        ),
        InlinePanel(
            "preparing_manuscript",
            label=_("Preparing Manuscript"),
        ),
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
        ),
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
        ),
        InlinePanel(
            "supp_docs_submission",
            label=_("Supplementary Documents Required for Submission"),
        ),
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
        ),
        InlinePanel(
            "acknowledgements",
            label=_("Acknowledgements"),
        ),
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
        ),
        FieldPanel("author_name"),
        FieldPanel("manuscript_length"),
        FieldPanel("format_check_list"),
        AutocompletePanel("text_language"),
        AutocompletePanel("abstract_language"),
    ]

    panels_editorial_board = [
        InlinePanel("editorial_board_member_journal", label=_("Editorial Board")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_titles, heading=_("Title")),
            ObjectList(panels_institutions, heading=_("Institutions")),
            ObjectList(panels_website, heading=_("Website")),
            ObjectList(panels_scope_and_about, heading=_("Focus and Scope")),
            ObjectList(panels_open_science, heading=_("Open Science")),
            ObjectList(panels_policy, heading=_("Editorial Policy")),
            ObjectList(panels_instructions_for_authors, heading=_("Instructions for Authors")),
            ObjectList(panels_editorial_board, heading=_("Editorial Board")),
        ]
    )
    class Meta:
        proxy = True
        verbose_name = _("Journal Editor")
        verbose_name_plural = _("Journal Editors")


class JournalProxyPanelPolicy(Journal):
    panels_policy = [
        InlinePanel(
            "ethics",
            label=_("Ethics"),
            classname="collapsed",
        ),
        InlinePanel(
            "ecommittee",
            label=_("Ethics Committee"),
            classname="collapsed",
        ),
        InlinePanel(
            "copyright",
            label=_("Copyright"),
            classname="collapsed",
        ),
        InlinePanel(
            "website_responsibility",
            label=_("Intellectual Property / Terms of use / Website responsibility"),
            classname="collapsed",
        ),
        InlinePanel(
            "author_responsibility",
            label=_("Intellectual Property / Terms of use / Author responsibility"),
            classname="collapsed",
        ),
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
            classname="collapsed",
        ),
        AutocompletePanel("digital_pa"),
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
            classname="collapsed",
        ),
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
            classname="collapsed",
        ),
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
            classname="collapsed",
        ),
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
            classname="collapsed",
        ),
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
            classname="collapsed",
        ),
        InlinePanel(
            "editorial_policy",
            label=_("Editorial Policy"),
            classname="collapsed",
        ),
        InlinePanel(
            "artificial_intelligence",
            label=_("Artificial Intelligence"),
            classname="collapsed",
        ),
    ]
    panels_editorial_board = [
        InlinePanel("editorial_board_member_journal", label=_("Editorial Board")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_policy, heading=_("Journal Policy")),
        ]
    )
    class Meta:
        proxy = True
        verbose_name = _("Journal Policy")
        verbose_name_plural = _("Journal Policy")



class JournalProxyPanelInstructionsForAuthors(Journal):
    panels_instructions_for_authors = [
        InlinePanel(
            "accepted_documment_types",
            label=_("Accepted Document Types"),
            classname="collapsed",
        ),
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
            classname="collapsed",
        ),
        InlinePanel(
            "preparing_manuscript",
            label=_("Preparing Manuscript"),
            classname="collapsed",
        ),
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
            classname="collapsed",
        ),
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
            classname="collapsed",
        ),
        InlinePanel(
            "supp_docs_submission",
            label=_("Supplementary Documents Required for Submission"),
            classname="collapsed",
        ),
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
            classname="collapsed",
        ),
        InlinePanel(
            "acknowledgements",
            label=_("Acknowledgements"),
            classname="collapsed",
        ),
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
            classname="collapsed",
        ),
        FieldPanel("author_name"),
        FieldPanel("manuscript_length"),
        FieldPanel("format_check_list"),
        AutocompletePanel("text_language"),
        AutocompletePanel("abstract_language"),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(
                panels_instructions_for_authors, heading=_("Instructions for Authors")
            )
        ]
    )
    class Meta:
        proxy = True
        verbose_name = _("Journal Instructions for Authors")
        verbose_name_plural = _("Journal Instructions for Authors")
