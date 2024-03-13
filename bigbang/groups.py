import logging
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


def get_or_create_group(group_name):
    return Group.objects.get_or_create(name=group_name)


def set_permission_access_wagtail_admin(group_name):
    wagtail_admin_codename = "access_admin"
    group, created = get_or_create_group(group_name=group_name)
    permission = Permission.objects.get(codename=wagtail_admin_codename)
    group.permissions.add(permission)
    group.save()


def set_permissions_group(group_name, permissions):
    group, created = get_or_create_group(group_name=group_name)

    for perm in permissions:
        content_type = ContentType.objects.get(
            app_label=perm["app"], model=perm["model"]
        )
        permission = Permission.objects.get(
            content_type=content_type, codename=perm["codename"]
        )
        group.permissions.add(permission)
        logging.info({"Group": group, "Permission": permission})
    group.save()


def load_group(group_name, permissions):
    set_permissions_group(group_name=group_name, permissions=permissions)
    set_permission_access_wagtail_admin(group_name=group_name)