from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtailautocomplete.edit_handlers import AutocompletePanel

from .models import Journal


class JournalProxyEditor(Journal):
    """
    Proxy model for Journal Editor with reorganized form structure.
    Structure follows the reference document "20251010_RBEF_Total_Página_Informativa_português_ok"
    with 4 main tabs: About Journal, Editorial Policy, Editorial Board, and Instructions for Authors.
    """
    
    # TAB 1: ABOUT JOURNAL (Sobre o Periódico)
    # Combines basic identification, history, open access, open science, focus/scope,
    # digital preservation, indexing sources, bibliographic data, websites, contact, and institutions
    
    panels_about_journal = [
        # Basic Identification
        AutocompletePanel("official", read_only=True),
        FieldPanel("title", read_only=True),
        FieldPanel("short_title"),
        InlinePanel("other_titles", label=_("Other titles")),
        
        # Brief History (Breve Histórico)
        InlinePanel("history", label=_("Brief History")),
        
        # Open Access (Acesso Aberto)
        FieldPanel("open_access"),
        InlinePanel("open_access_text", label=_("Open Access")),
        
        # Open Science Compliance (Conformidade com a Ciência Aberta)
        FieldPanel("url_oa"),
        InlinePanel(
            "file_oa", label=_("Open Science accordance form")
        ),
        InlinePanel(
            "open_science_compliance",
            label=_("Open Science Compliance"),
        ),
        InlinePanel("open_data", label=_("Open data")),
        InlinePanel("preprint", label=_("Preprint")),
        FieldPanel("journal_use_license"),
        
        # Ethics in Publication (Ética na Publicação)
        InlinePanel(
            "ethics",
            label=_("Ethics"),
        ),
        InlinePanel(
            "ecommittee",
            label=_("Ethics Committee"),
        ),
        
        # Focus and Scope (Foco e Escopo)
        InlinePanel("mission", label=_("Mission")),
        InlinePanel("focus", label=_("Focus and Scope")),
        AutocompletePanel("subject"),
        InlinePanel("thematic_area", label=_("Thematic Areas")),
        AutocompletePanel("subject_descriptor"),
        AutocompletePanel("vocabulary"),
        
        # Digital Preservation (Preservação Digital)
        AutocompletePanel("digital_pa"),
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
        ),
        
        # Indexing Sources (Fontes de Indexação)
        AutocompletePanel("indexed_at"),
        AutocompletePanel("additional_indexed_at"),
        InlinePanel("title_in_database", label=_("Title in Database")),
        AutocompletePanel("wos_area"),
        AutocompletePanel("wos_db"),
        
        # Bibliographic Data (Ficha Bibliográfica)
        FieldPanel("frequency"),
        FieldPanel("publishing_model"),
        FieldPanel("standard"),
        FieldPanel("main_collection"),
        
        # Websites and Social Media (Websites e Mídias Sociais)
        InlinePanel(
            "related_journal_urls", label=_("Journal Urls")
        ),
        InlinePanel("journalsocialnetwork", label=_("Social Network")),
        FieldPanel("submission_online_url"),
        FieldPanel("logo", heading=_("Logo")),
        
        # Contact (Contato)
        FieldPanel("contact_name"),
        InlinePanel("journal_email", label=_("Contact e-mail")),
        FieldPanel("contact_address"),
        AutocompletePanel("contact_location"),
        
        # Institutions (Instituições)
        InlinePanel("owner_history", label=_("Owner")),
        InlinePanel("publisher_history", label=_("Publisher")),
        InlinePanel("sponsor_history", label=_("Sponsor")),
        InlinePanel(
            "copyright_holder_history",
            label=_("Copyright Holder"),
        ),
    ]

    # TAB 2: EDITORIAL POLICY (Política Editorial)
    # Groups all editorial policy-related panels including peer review, data,
    # fees, ethics, conflicts, software, AI, gender, copyright, and intellectual property
    
    panels_editorial_policy = [
        # Peer Review Process (Processo de Avaliação por Pares)
        InlinePanel("review", label=_("Peer review")),
        
        # Fee Charging (Cobrança de Taxas)
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
        ),
        
        # Ethics and Misconduct (Ética e Más Condutas)
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
        ),
        
        # Conflict of Interest (Conflito de Interesses)
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
        ),
        
        # Verification Software (Software de Verificação)
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
        ),
        
        # Artificial Intelligence (Inteligência Artificial)
        InlinePanel(
            "artificial_intelligence",
            label=_("Artificial Intelligence"),
        ),
        
        # Gender Issues (Questões de Gênero)
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
        ),
        
        # Copyright (Direitos Autorais)
        InlinePanel(
            "copyright",
            label=_("Copyright"),
        ),
        
        # Intellectual Property (Propriedade Intelectual)
        InlinePanel(
            "website_responsibility",
            label=_("Intellectual Property / Terms of use / Website responsibility"),
        ),
        InlinePanel(
            "author_responsibility",
            label=_("Intellectual Property / Terms of use / Author responsibility"),
        ),
        
        # General Editorial Policy (Política Editorial Geral)
        InlinePanel(
            "editorial_policy",
            label=_("Editorial Policy"),
        ),
    ]

    # TAB 3: EDITORIAL BOARD (Corpo Editorial)
    
    panels_editorial_board = [
        InlinePanel("editorial_board_member_journal", label=_("Editorial Board")),
    ]

    # TAB 4: INSTRUCTIONS FOR AUTHORS (Instruções para Autores)
    # Groups all author-facing instructions including document types, contributions,
    # format, assets, citations, supplementary docs, funding, acknowledgments, and additional info
    
    panels_instructions_for_authors = [
        # Document Types (Tipos de Documentos)
        InlinePanel(
            "accepted_documment_types",
            label=_("Accepted Document Types"),
        ),
        
        # Author Contributions (Contribuição dos Autores)
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
        ),
        FieldPanel("author_name"),
        
        # Submission Format (Formato de Envio)
        InlinePanel(
            "preparing_manuscript",
            label=_("Preparing Manuscript"),
        ),
        FieldPanel("manuscript_length"),
        FieldPanel("format_check_list"),
        AutocompletePanel("text_language"),
        AutocompletePanel("abstract_language"),
        
        # Digital Assets (Ativos Digitais)
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
        ),
        
        # Citations and References (Citações e Referências)
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
        ),
        
        # Supplementary Documents (Documentos Suplementares)
        InlinePanel(
            "supp_docs_submission",
            label=_("Supplementary Documents Required for Submission"),
        ),
        
        # Funding Statement (Declaração de Financiamento)
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
        ),
        
        # Acknowledgements (Agradecimentos)
        InlinePanel(
            "acknowledgements",
            label=_("Acknowledgements"),
        ),
        
        # Additional Information (Informações Adicionais)
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
        ),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_about_journal, heading=_("About Journal")),
            ObjectList(panels_editorial_policy, heading=_("Editorial Policy")),
            ObjectList(panels_editorial_board, heading=_("Editorial Board")),
            ObjectList(panels_instructions_for_authors, heading=_("Instructions for Authors")),
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
