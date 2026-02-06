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
        AutocompletePanel("official"),
        FieldPanel("title"),
        FieldPanel("short_title"),
        InlinePanel("other_titles", label=_("Other titles"), classname="collapsed"),
        
        # Brief History (Breve Histórico)
        InlinePanel("history", label=_("Brief History"), classname="collapsed"),
        
        # Open Access (Acesso Aberto)
        FieldPanel("open_access"),
        InlinePanel("open_access_text", label=_("Open Access"), classname="collapsed"),
        
        # Open Science Compliance (Conformidade com a Ciência Aberta)
        FieldPanel("url_oa"),
        InlinePanel(
            "file_oa", label=_("Open Science accordance form"), classname="collapsed"
        ),
        InlinePanel(
            "open_science_compliance",
            label=_("Open Science Compliance"),
            classname="collapsed",
        ),
        InlinePanel("open_data", label=_("Open data"), classname="collapsed"),
        InlinePanel("preprint", label=_("Preprint"), classname="collapsed"),
        FieldPanel("journal_use_license"),
        
        # Ethics in Publication (Ética na Publicação)
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
        
        # Focus and Scope (Foco e Escopo)
        InlinePanel("mission", label=_("Mission"), classname="collapsed"),
        InlinePanel("focus", label=_("Focus and Scope"), classname="collapsed"),
        AutocompletePanel("subject"),
        InlinePanel("thematic_area", label=_("Thematic Areas"), classname="collapsed"),
        AutocompletePanel("subject_descriptor"),
        AutocompletePanel("vocabulary"),
        
        # Digital Preservation (Preservação Digital)
        AutocompletePanel("digital_pa"),
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
            classname="collapsed",
        ),
        
        # Indexing Sources (Fontes de Indexação)
        AutocompletePanel("indexed_at"),
        AutocompletePanel("additional_indexed_at"),
        InlinePanel("title_in_database", label=_("Title in Database"), classname="collapsed"),
        AutocompletePanel("wos_area"),
        AutocompletePanel("wos_db"),
        
        # Bibliographic Data (Ficha Bibliográfica)
        FieldPanel("frequency"),
        FieldPanel("publishing_model"),
        FieldPanel("standard"),
        FieldPanel("main_collection"),
        
        # Websites and Social Media (Websites e Mídias Sociais)
        InlinePanel(
            "related_journal_urls", label=_("Journal Urls"), classname="collapsed"
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
        InlinePanel("owner_history", label=_("Owner"), classname="collapsed"),
        InlinePanel("publisher_history", label=_("Publisher"), classname="collapsed"),
        InlinePanel("sponsor_history", label=_("Sponsor"), classname="collapsed"),
        InlinePanel(
            "copyright_holder_history",
            label=_("Copyright Holder"),
            classname="collapsed",
        ),
        
        # Administrative Notes (Notas Administrativas)
        InlinePanel("annotation", label=_("Notes"), classname="collapsed"),
    ]

    # TAB 2: EDITORIAL POLICY (Política Editorial)
    # Groups all editorial policy-related panels including peer review, data,
    # fees, ethics, conflicts, software, AI, gender, copyright, and intellectual property
    
    panels_editorial_policy = [
        # Peer Review Process (Processo de Avaliação por Pares)
        InlinePanel("review", label=_("Peer review"), classname="collapsed"),
        
        # Fee Charging (Cobrança de Taxas)
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
            classname="collapsed",
        ),
        
        # Ethics and Misconduct (Ética e Más Condutas)
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
            classname="collapsed",
        ),
        
        # Conflict of Interest (Conflito de Interesses)
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
            classname="collapsed",
        ),
        
        # Verification Software (Software de Verificação)
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
            classname="collapsed",
        ),
        
        # Artificial Intelligence (Inteligência Artificial)
        InlinePanel(
            "artificial_intelligence",
            label=_("Artificial Intelligence"),
            classname="collapsed",
        ),
        
        # Gender Issues (Questões de Gênero)
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
            classname="collapsed",
        ),
        
        # Copyright (Direitos Autorais)
        InlinePanel(
            "copyright",
            label=_("Copyright"),
            classname="collapsed",
        ),
        
        # Intellectual Property (Propriedade Intelectual)
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
        
        # General Editorial Policy (Política Editorial Geral)
        InlinePanel(
            "editorial_policy",
            label=_("Editorial Policy"),
            classname="collapsed",
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
            classname="collapsed",
        ),
        
        # Author Contributions (Contribuição dos Autores)
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
            classname="collapsed",
        ),
        FieldPanel("author_name"),
        
        # Submission Format (Formato de Envio)
        InlinePanel(
            "preparing_manuscript",
            label=_("Preparing Manuscript"),
            classname="collapsed",
        ),
        FieldPanel("manuscript_length"),
        FieldPanel("format_check_list"),
        AutocompletePanel("text_language"),
        AutocompletePanel("abstract_language"),
        
        # Digital Assets (Ativos Digitais)
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
            classname="collapsed",
        ),
        
        # Citations and References (Citações e Referências)
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
            classname="collapsed",
        ),
        
        # Supplementary Documents (Documentos Suplementares)
        InlinePanel(
            "supp_docs_submission",
            label=_("Supplementary Documents Required for Submission"),
            classname="collapsed",
        ),
        
        # Funding Statement (Declaração de Financiamento)
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
            classname="collapsed",
        ),
        
        # Acknowledgements (Agradecimentos)
        InlinePanel(
            "acknowledgements",
            label=_("Acknowledgements"),
            classname="collapsed",
        ),
        
        # Additional Information (Informações Adicionais)
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
            classname="collapsed",
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
