import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from config.settings.base import COLLECTION_TEAM, JOURNAL_TEAM
from .permissions import permission_collection_team

def get_or_create_group(group_name):
    return Group.objects.get_or_create(name=group_name)


def set_permission_access_wagtail_admin(group_name):
    wagtail_admin_codename = "access_admin"
    group, created = get_or_create_group(group_name=group_name)
    permission = Permission.objects.get(codename=wagtail_admin_codename)
    group.permissions.add(permission)
    group.save()


def set_permissions_collection_team():
    group, created = get_or_create_group(group_name=COLLECTION_TEAM)

    for perm in permission_collection_team:
        content_type = ContentType.objects.get(
            app_label=perm["app"], model=perm["model"]
        )
        permission = Permission.objects.get(
            content_type=content_type, codename=perm["codename"]
        )
        group.permissions.add(permission)
        logging.info({"Group": group, "Permission": permission})
    group.save()


def load_group_collection_team():
    set_permissions_collection_team()
    set_permission_access_wagtail_admin(group_name=COLLECTION_TEAM)


def load_group_journal_team():
    get_or_create_group(group_name=JOURNAL_TEAM)