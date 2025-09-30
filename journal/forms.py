from core.forms import CoreAdminModelForm


class SciELOJournalModelForm(CoreAdminModelForm):
    def save_all(self, user):
        instance_model = super().save_all(user)

        if self.instance.issn_scielo is None:
            self.instance.issn_scielo = instance_model.journal.official.issn_electronic or instance_model.journal.official.issn_print

        self.save()

        return instance_model
