from wagtail.admin.forms import WagtailAdminModelForm


class ThematicAreaForm(WagtailAdminModelForm):

    def save_all(self, user):
        thematic = super().save(commit=False)

        if self.instance.pk is not None:
            thematic.updated_by = user
        else:
            thematic.creator = user

        self.save()

        return thematic


class ThematicAreaFileForm(WagtailAdminModelForm):

    def save_all(self, user):
        thematic_areas_file = super().save(commit=False)

        if self.instance.pk is not None:
            thematic_areas_file.updated_by = user
        else:
            thematic_areas_file.creator = user

        self.save()

        return thematic_areas_file
