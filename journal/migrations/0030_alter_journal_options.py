# Generated by Django 5.0.8 on 2025-03-19 19:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0029_alter_scielojournal_journal_acron"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="journal",
            options={
                "ordering": ("title",),
                "permissions": [
                    ("can_edit_official", "Can edit official journal"),
                    ("can_edit_title", "Can edit title"),
                    ("can_edit_short_title", "Can edit short title"),
                    (
                        "can_edit_submission_online_url",
                        "Can edit submission online url",
                    ),
                    ("can_edit_contact_name", "Can edit contact name"),
                    ("can_edit_contact_address", "Can edit contact address"),
                    ("can_edit_contact_location", "Can edit contact location"),
                    ("can_edit_open_access", "Can edit open access"),
                    ("can_edit_url_oa", "Can edit url Open Science accordance form"),
                    ("can_edit_main_collection", "Can edit main collection"),
                    ("can_edit_frequency", "Can edit frequency"),
                    ("can_edit_publishing_model", "Can edit publishing model"),
                    ("can_edit_subject_descriptor", "Can edit subject descriptor"),
                    ("can_edit_subject", "Can edit subject"),
                    ("can_edit_wos_db", "Can edit Web of Knowledge Databases"),
                    (
                        "can_edit_wos_area",
                        "Can edit Web of Knowledge Subject Categories",
                    ),
                    ("can_edit_abstract_language", "Can edit abstract language"),
                    ("can_edit_standard", "Can edit standard"),
                    ("can_edit_alphabet", "Can edit alphabet"),
                    ("can_edit_type_of_literature", "Can edit type of literature"),
                    ("can_edit_treatment_level", "Can edit treatment level"),
                    ("can_edit_level_of_publication", "Can edit level of publication"),
                    ("can_edit_national_code", "Can edit national code"),
                    ("can_edit_classification", "Can edit classification"),
                    ("can_edit_vocabulary", "Can edit vocabulary"),
                    ("can_edit_indexed_at", "Can edit indexed at"),
                    (
                        "can_edit_additional_indexed_at",
                        "Can edit additional indexed at",
                    ),
                    ("can_edit_journal_url", "Can edit journal url"),
                    ("can_edit_use_license", "Can edit use license"),
                    ("can_edit_journal_use_license", "Can edit journal use license"),
                    ("can_edit_center_code", "Can edit center code"),
                    (
                        "can_edit_identification_number",
                        "Can edit identification number",
                    ),
                    ("can_edit_ftp", "Can edit ftp"),
                    ("can_edit_user_subscription", "Can edit user subscription"),
                    ("can_edit_subtitle", "Can edit subtitle"),
                    ("can_edit_section", "Can edit section"),
                    ("can_edit_has_supplement", "Can edit has supplement"),
                    ("can_edit_is_supplement", "Can edit is supplement"),
                    ("can_edit_acronym_letters", "Can edit acronym letters"),
                    ("can_edit_author_name", "Can edit author name"),
                    ("can_edit_manuscript_length", "Can edit manuscript length"),
                    ("can_edit_format_check_list", "Can edit format check list"),
                    ("can_edit_digital_pa", "Can edit digital pa"),
                    ("can_edit_doi_prefix", "Can edit doi prefix"),
                    ("can_edit_mission", "Can edit mission"),
                    ("can_edit_owner_history", "Can edit owner history"),
                    ("can_edit_publisher_history", "Can edit publisher history"),
                    ("can_edit_sponsor_history", "Can edit sponsor history"),
                    (
                        "can_edit_copyright_holder_history",
                        "Can edit copyright holder history",
                    ),
                    ("can_edit_journalsocialnetwork", "Can edit journalsocialnetwork"),
                    ("can_edit_file_oa", "Can edit file oa"),
                    ("can_edit_journal_email", "Can edit journal email"),
                    ("can_edit_history", "Can edit history"),
                    ("can_edit_focus", "Can edit focus"),
                    ("can_edit_thematic_area", "Can edit thematic area"),
                    ("can_edit_annotation", "Can edit annotation"),
                    ("can_edit_ecommittee", "Can edit ecommittee"),
                    ("can_edit_other_titles", "Can edit other titles"),
                    ("can_edit_related_journal_urls", "Can edit related journal urls"),
                    ("can_edit_open_data", "Can edit open data"),
                    ("can_edit_preprint", "Can edit preprint"),
                    ("can_edit_review", "Can edit review"),
                    (
                        "can_edit_open_science_compliance",
                        "Can edit open science compliance",
                    ),
                    ("can_edit_ethics", "Can edit ethics"),
                    ("can_edit_copyrigth", "Can edit copyrigth"),
                    (
                        "can_edit_website_responsibility",
                        "Can edit website responsibility",
                    ),
                    (
                        "can_edit_author_responsibility",
                        "Can edit author responsibility",
                    ),
                    ("can_edit_policies", "Can edit policies"),
                    ("can_edit_digital_preservation", "Can edit digital preservation"),
                    ("can_edit_conflict_policy", "Can edit conflict policy"),
                    ("can_edit_software_adoption", "Can edit software adoption"),
                    ("can_edit_gender_issues", "Can edit Gender Issues"),
                    ("can_edit_fee_charging", "Can edit Fee Charging"),
                    ("can_edit_editorial_policy", "Can edit Editorial Policy"),
                    (
                        "can_edit_accepted_documment_types",
                        "Can edit Accepted Document Types",
                    ),
                    (
                        "can_edit_authors_contributions",
                        "Can edit Authors Contributions",
                    ),
                    ("can_edit_preparing_manuscript", "Can edit Preparing Manuscript"),
                    ("can_edit_digital_assets", "Can edit Digital Assets"),
                    (
                        "can_edit_citations_and_references",
                        "Can edit Citations and References",
                    ),
                    (
                        "can_edit_supp_docs_submission",
                        "Can edit Supplementary Documents Required for Submission",
                    ),
                    ("can_edit_financing_statement", "Can edit Financing Statement"),
                    ("can_edit_acknowledgements", "Can edit Acknowledgements"),
                    (
                        "can_edit_additional_information",
                        "Can edit Additional Information",
                    ),
                    ("can_edit_text_language", "Can edit Text Language"),
                ],
                "verbose_name": "Journal",
                "verbose_name_plural": "Journals",
            },
        ),
    ]
