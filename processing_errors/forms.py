from wagtail.admin.forms import WagtailAdminModelForm


class ProcessingErrorsForm(WagtailAdminModelForm):
    def save_all(self, user):
        erro = super().save(commit=False)

        if self.instance.pk is not None:
            erro.updated_by = user
        else:
            erro.creator = user

        self.save()

        return erro
