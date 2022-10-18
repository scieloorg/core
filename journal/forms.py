from wagtail.admin.forms import WagtailAdminModelForm


class OfficialJournalForm(WagtailAdminModelForm):

    def save_all(self, user):
        journal = super().save(commit=False)

        if self.instance.pk is not None:
            journal.updated_by = user
        else:
            journal.creator = user

        self.save()

        return journal
