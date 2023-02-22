WAGTAIL_MENU_APPS_ORDER = {
    'collection': 400,
    'journal': 500,
    'issue': 510,
    'article': 520,
    # 'upload': 700,
    'migration': 710,
    'location': 800,
    'institution': 810,
}


def get_menu_order(app_name):
    try:
        return WAGTAIL_MENU_APPS_ORDER[app_name]
    except:
        return 900
