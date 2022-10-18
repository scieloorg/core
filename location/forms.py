from wagtail.admin.forms import WagtailAdminModelForm


class CityForm(WagtailAdminModelForm):

    def save_all(self, user):
        city = super().save(commit=False)

        if self.instance.pk is not None:
            city.updated_by = user
        else:
            city.creator = user

        self.save()

        return city


class StateForm(WagtailAdminModelForm):

    def save_all(self, user):
        state = super().save(commit=False)

        if self.instance.pk is not None:
            state.updated_by = user
        else:
            state.creator = user

        self.save()

        return state


class CountryForm(WagtailAdminModelForm):

    def save_all(self, user):
        country = super().save(commit=False)

        if self.instance.pk is not None:
            country.updated_by = user
        else:
            country.creator = user

        self.save()

        return country


class LocationForm(WagtailAdminModelForm):

    def save_all(self, user):
        location = super().save(commit=False)

        if self.instance.pk is not None:
            location.updated_by = user
        else:
            location.creator = user

        self.save()

        return location
