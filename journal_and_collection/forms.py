from wagtail.admin.forms import WagtailAdminModelForm


class JournalAndCollectionForm(WagtailAdminModelForm):
    def save_all(self, user):
        journal = super().save(commit=False)

        if self.instance.pk is not None:
            journal.updated_by = user
        else:
            journal.creator = user

        self.save()

        return journal


class EventForm(WagtailAdminModelForm):
    def save_all(self, user):
        event = super().save(commit=False)

        if self.instance.pk is not None:
            event.updated_by = user
        else:
            event.creator = user

        self.save()

        return event
