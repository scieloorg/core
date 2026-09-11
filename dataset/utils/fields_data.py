commom_fields = [
    "name",
    "identifier",
    "type",
    "published_at",
]

fields_dataset = [
    "global_id",
    "description",
    "publisher",
    "citation_html",
    "citation",
    "dataverse",
    "authors",
    "keywords",
    "thematic_area",
    "contacts",
    "publications",
    "file_type",
    "file_content_type",
    "dataset",
    "identifier_of_dataverse",
    "dataset_persistent_id",
] + commom_fields

fields_dataverse = ["identifier", "description"] + commom_fields

fields_file = [
    "file_type",
    "file_content_type",
    "file_persistent_id",
    "dataset_persistent_id",
] + commom_fields
