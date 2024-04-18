WAGTAIL_MENU_APPS_ORDER = [
    "x",
    "collection",
    "journal",
    "editorialboard",
    "issue",
    "article",

    "book",

    "location",
    "institution",
    "researcher",

    "thematic_areas",
    "vocabulary",
    "core",

    "altmetric",
    "report",

    "amjournal",

    "article_subm",

    "pid_provider",
    "django_celery_beat",
    "tracker",
    "files_storage",
    "Configurações",
    "Páginas",
    "Relatórios",
    "Ajuda",
    "Images",
    "Documentos",
]


def get_menu_order(app_name):
    try:
        return WAGTAIL_MENU_APPS_ORDER.index(app_name)
    except:
        return 9000
