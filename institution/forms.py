from wagtail.admin.forms import WagtailAdminModelForm


class InstitutionForm(WagtailAdminModelForm):

    def save_all(self, user):
        inst = super().save(commit=False)

        if self.instance.pk is not None:
            inst.updated_by = user
        else:
            inst.creator = user

        self.save()

        return inst
