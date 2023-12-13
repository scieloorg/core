import logging

# from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.forms import WagtailAdminModelForm


class EditorialBoardForm(WagtailAdminModelForm):
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        self.save()

        return inst


class EditorialBoardRoleForm(WagtailAdminModelForm):
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        self.save()

        return inst


class EditorialBoardMemberForm(WagtailAdminModelForm):
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user
        # FIXME it is not called
        self.instance.update_editorial_board(user)

        self.save()
        return inst


class EditorialBoardMemberActivityForm(WagtailAdminModelForm):
    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        self.save()

        return inst
