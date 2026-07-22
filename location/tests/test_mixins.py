from location.models import City, Country, Location, State


class LocationTestMixin:
    """Mixin com helpers para criar objetos do app location em testes."""

    def make_location(
        self,
        user,
        country_name="Brazil",
        country_acronym="BR",
        country_acron3="BRA",
        state_name="São Paulo",
        state_acronym="SP",
        city_name="São Paulo",
    ):

        country = Country.create_or_update(
            user=user,
            name=country_name,
            acronym=country_acronym,
            acron3=country_acron3,
        )
        state = State.create(user=user, name=state_name, acronym=state_acronym)
        city = City.create(user=user, name=city_name)
        return Location._create(
            user=user, country=country, state=state, city=city
        )
