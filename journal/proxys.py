from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtailautocomplete.edit_handlers import AutocompletePanel

from .models import Journal


class JournalProxyEditor(Journal):
    panels_titles = [
        # about_the_journal - 08 - Ficha Bibliográfica - F - Ano de criação do periódico / ISSN
        AutocompletePanel("official", read_only=True),
        # about_the_journal - 08 - Ficha Bibliográfica - A - Título do periódico
        FieldPanel("title", read_only=True),
        # about_the_journal - 08 - Ficha Bibliográfica - B - Título abreviado do periódico
        FieldPanel("short_title"),
        # InlinePanel("other_titles", label=_("Other titles")),
    ]

    panels_scope_and_about = [
        # InlinePanel("mission", label=_("Mission")),

        # about_the_journal - 01 - brief history
        InlinePanel("history", label=_("Brief History")),

        # about_the_journal - 05 - focus and scope
        InlinePanel("focus", label=_("Focus and Scope")),
        # AutocompletePanel("subject"),
        # InlinePanel("thematic_area", label=_("Thematic Areas")),
        # AutocompletePanel("subject_descriptor"),
        # AutocompletePanel("wos_area"),
        # AutocompletePanel("wos_db"),

        # about_the_journal - 07a - Fontes de Indexação padronizadas
        AutocompletePanel("indexed_at"),
        # about_the_journal - 07b - Fontes de Indexação adicionais / não padronizadas
        AutocompletePanel("additional_indexed_at"),

        # AutocompletePanel("vocabulary"),
        # InlinePanel("title_in_database", label=_("Title in Database")),
    ]

    panels_institutions = [
        # about_the_journal - 08 - Ficha Bibliográfica - C1 - Publicação de
        InlinePanel("owner_history", label=_("Owner")),
        # about_the_journal - 08 - Ficha Bibliográfica - C2 - Publicação de
        InlinePanel("publisher_history", label=_("Publisher")),
        
        # POLÍTICA EDITORIAL - 14 - Patrocinadores e Agências de Fomento 
        InlinePanel("sponsor_history", label=_("Sponsor")),
        # InlinePanel(
        #     "copyright_holder_history",
        #     label=_("Copyright Holder"),
        # ),
    ]

    panels_website = [
        # about_the_journal - 10a - Contato
        FieldPanel("contact_name"),
        # about_the_journal - 10b - Contato
        FieldPanel("contact_address"),
        # about_the_journal - 10c - Contato
        AutocompletePanel("contact_location"),
        # about_the_journal - 10d - Contato
        InlinePanel("journal_email", label=_("Contact e-mail")),

        # about_the_journal - 09d - Websites
        FieldPanel("logo", heading=_("Logo")),
        # about_the_journal - 09c - Websites
        FieldPanel("journal_url"),
        
        # InlinePanel("related_journal_urls", label=_("Journal Urls")),
        
        # about_the_journal - 09b - Websites
        FieldPanel("submission_online_url"),
        # FieldPanel("main_collection"),

        # about_the_journal - 09 - Websites e Mídias Sociais
        InlinePanel("journalsocialnetwork", label=_("Social Network")),

        # about_the_journal - 08 - Ficha Bibliográfica - D - Periodicidade
        FieldPanel("frequency"),

        # about_the_journal - 08 - Ficha Bibliográfica - E - Modalidade de publicação
        FieldPanel("publishing_model"),
        # FieldPanel("standard"),
    ]

    panels_open_science = [
        # FieldPanel("open_access"),

        # about_the_journal - 02 - journal declares it is open access
        InlinePanel("open_access_text", label=_("Open Access")),
        # FieldPanel("url_oa"),

        # about_the_journal - 03a - Conformidade com a Ciência Aberta - formulário de auto declaração
        InlinePanel("file_oa", label=_("Open Science accordance form")),

        # about_the_journal - 04 - Ética na Publicação
        InlinePanel(
            "ethics",
            label=_("Ethics"),
        ),

        # POLÍTICA EDITORIAL - 11b - Direitos Autorais / AUTORES CEDEM PARA PUBLICAR EM CC-BY
        # FieldPanel("journal_use_license"),

        # POLÍTICA EDITORIAL - 03 - Dados Abertos
        InlinePanel("open_data", label=_("Open data")),

        # POLÍTICA EDITORIAL - 01 - Preprints
        InlinePanel("preprint", label=_("Preprint")),

        # POLÍTICA EDITORIAL - 02 - Peer review
        InlinePanel("review", label=_("Peer review")),

        # about_the_journal - 03b - Conformidade com a Ciência Aberta - declaração de conformidade
        InlinePanel(
            "open_science_compliance",
            label=_("Open Science Compliance"),
        ),
    ]

    panels_policy = [

        # POLÍTICA EDITORIAL - 10 - Comitê de Ética
        InlinePanel(
            "ecommittee",
            label=_("Ethics Committee"),
        ),
        # POLÍTICA EDITORIAL - 11a - detentor dos direitos autorais
        InlinePanel(
            "copyright",
            label=_("Copyright"),
        ),

        # POLÍTICA EDITORIAL - 12 - Propriedade Intelectual e Termos de uso - Responsabilidade do site
        InlinePanel(
            "website_responsibility",
            label=_("Intellectual Property / Terms of use / Website responsibility"),
        ),
        
        # POLÍTICA EDITORIAL - 13 - Propriedade Intelectual e Termos de uso - Responsabilidade do autor
        InlinePanel(
            "author_responsibility",
            label=_("Intellectual Property / Terms of use / Author responsibility"),
        ),

        # POLÍTICA EDITORIAL - 05 - Política de Ética e Más condutas, Errata e Retratação
        InlinePanel(
            "policies",
            label=_("Retraction Policy | Ethics and Misconduct Policy"),
        ),

        # AutocompletePanel("digital_pa"),
        # about_the_journal - 06 - Preservação Digital - texto + link - poderia estar fixo no template html?
        InlinePanel(
            "digital_preservation",
            label=_("Digital Preservation"),
        ),

        # POLÍTICA EDITORIAL - 06 - Política sobre Conflito de Interesses
        InlinePanel(
            "conflict_policy",
            label=_("Conflict of interest policy"),
        ),

        # POLÍTICA EDITORIAL - 07 - Adoção de softwares de verificação de similaridade
        InlinePanel(
            "software_adoption",
            label=_("Similarity Verification Software Adoption"),
        ),

        # POLÍTICA EDITORIAL - 09 - Questões de Sexo e Gênero
        InlinePanel(
            "gender_issues",
            label=_("Gender Issues"),
        ),
        # POLÍTICA EDITORIAL - 04 - Cobrança de Taxas
        InlinePanel(
            "fee_charging",
            label=_("Fee Charging"),
        ),
        # InlinePanel(
        #     "editorial_policy",
        #     label=_("Editorial Policy"),
        # ),

        # POLÍTICA EDITORIAL - 08 - Adoção de softwares uso de recursos de Inteligência Artificial
        # Uso por autores
        # Responsabilidade e transparência
        # Uso por pareceristas e editores
        # Processos de avaliação e decisões editoriais
        # Atualizações - TEXTO FIXO NO TEMPLATE HTML?
        InlinePanel(
            "artificial_intelligence",
            label=_("Artificial Intelligence"),
        ),
    ]
    # panels_notes = [InlinePanel("annotation", label=_("Notes"))]

    panels_instructions_for_authors = [
        # INSTRUÇÕES AOS AUTORES - 01 - Tipos de documentos aceitos
        InlinePanel(
            "accepted_documment_types",
            label=_("Accepted Document Types"),
        ),
        # INSTRUÇÕES AOS AUTORES - 02 - Contribuição dos Autores
        InlinePanel(
            "authors_contributions",
            label=_("Authors Contributions"),
        ),
        
        # INSTRUÇÕES AOS AUTORES - 0? - 
        # InlinePanel(
        #     "preparing_manuscript",
        #     label=_("Preparing Manuscript"),
        # ),
        
        # INSTRUÇÕES AOS AUTORES - 04 - Ativos Digitais 
        InlinePanel(
            "digital_assets",
            label=_("Digital Assets"),
        ),

        # INSTRUÇÕES AOS AUTORES - 05 - Citações e Referências
        InlinePanel(
            "citations_and_references",
            label=_("Citations and References"),
        ),

        # INSTRUÇÕES AOS AUTORES - 0? - 
        # InlinePanel(
        #     "supp_docs_submission",
        #     label=_("Supplementary Documents Required for Submission"),
        # ),

        # INSTRUÇÕES AOS AUTORES - 06 - Declaração de Financiamento
        InlinePanel(
            "financing_statement",
            label=_("Financing Statement"),
        ),

        # INSTRUÇÕES AOS AUTORES - 0? - 
        # InlinePanel(
        #     "acknowledgements",
        #     label=_("Acknowledgements"),
        # ),
        # INSTRUÇÕES AOS AUTORES - 07 - Informações Adicionais
        InlinePanel(
            "additional_information",
            label=_("Additional Information"),
        ),
        # FieldPanel("author_name"),
        # FieldPanel("manuscript_length"),

        # INSTRUÇÕES AOS AUTORES - 03 - Formato de Envio dos Artigos
        FieldPanel("format_check_list"),
        
        # AutocompletePanel("text_language"),
        # AutocompletePanel("abstract_language"),
    ]

    # CORPO EDITORIAL
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
            ObjectList(
                panels_instructions_for_authors, heading=_("Instructions for Authors")
            ),
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


class JournalProxyAdminOnly(Journal):
    """
    Admin-only proxy model for Legacy Compatibility and Notes tabs.
    Only accessible to superusers.
    """

    panels_legacy_compatibility_fields = [
        FieldPanel("alphabet"),
        FieldPanel("classification"),
        FieldPanel("national_code"),
        FieldPanel("type_of_literature"),
        FieldPanel("treatment_level"),
        FieldPanel("level_of_publication"),
        FieldPanel("center_code"),
        FieldPanel("identification_number"),
        FieldPanel("ftp"),
        FieldPanel("user_subscription"),
        FieldPanel("subtitle"),
        FieldPanel("section"),
        FieldPanel("has_supplement"),
        FieldPanel("is_supplement"),
        FieldPanel("acronym_letters"),
    ]

    panels_notes = [InlinePanel("annotation", label=_("Notes"))]

    edit_handler = TabbedInterface(
        [
            ObjectList(
                panels_legacy_compatibility_fields, heading=_("Legacy Compatibility")
            ),
            ObjectList(panels_notes, heading=_("Notes")),
        ]
    )

    class Meta:
        proxy = True
        verbose_name = _("Journal (Admin Only)")
        verbose_name_plural = _("Journals (Admin Only)")
