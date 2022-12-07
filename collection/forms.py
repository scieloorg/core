from wagtail.admin.forms import WagtailAdminModelForm


class CollectionForm(WagtailAdminModelForm):
    def save_all(self, user):
        collection = super().save(commit=False)

        if self.instance.pk is not None:
            collection.updated_by = user
        else:
            collection.creator = user

        self.save()

        return collection
