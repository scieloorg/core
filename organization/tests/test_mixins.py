from location.tests.test_mixins import LocationTestMixin
from organization.models import Organization


class OrganizationTestMixin(LocationTestMixin):
    """Mixin com helpers para criar objetos do app organization em testes."""

    def make_organization(
        self,
        user,
        name="Universidade de São Paulo",
        acronym="USP",
        location=None,
    ):
        if location is None:
            # Passa o 'user' que já veio como parâmetro obrigatório no make_organization
            location = self.make_location(user)

        return Organization.create(
            user=user, name=name, acronym=acronym, location=location
        )
