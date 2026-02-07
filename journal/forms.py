from core.forms import CoreAdminModelForm


class JournalModelForm(CoreAdminModelForm):
    """
    Custom form for Journal model that automatically migrates institution data
    to raw_text fields before presenting the form.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # If we're editing an existing instance (not creating a new one)
        if self.instance and self.instance.pk:
            self._auto_migrate_history_to_raw()
    
    def _auto_migrate_history_to_raw(self):
        """
        Automatically migrates history data from institution to raw_text fields
        when presenting the form, if raw_text is empty but institution is not None.
        """
        # Check and migrate publisher_history
        for history_item in self.instance.publisher_history.all():
            if not history_item.raw_text and history_item.institution:
                self.instance._migrate_history_to_raw(history_item)
        
        # Check and migrate owner_history
        for history_item in self.instance.owner_history.all():
            if not history_item.raw_text and history_item.institution:
                self.instance._migrate_history_to_raw(history_item)
        
        # Check and migrate sponsor_history
        for history_item in self.instance.sponsor_history.all():
            if not history_item.raw_text and history_item.institution:
                self.instance._migrate_history_to_raw(history_item)
        
        # Check and migrate copyright_holder_history
        for history_item in self.instance.copyright_holder_history.all():
            if not history_item.raw_text and history_item.institution:
                self.instance._migrate_history_to_raw(history_item)


class SciELOJournalModelForm(CoreAdminModelForm):
    def save_all(self, user):
        instance_model = super().save_all(user)

        if self.instance.issn_scielo is None:
            self.instance.issn_scielo = instance_model.journal.official.issn_electronic or instance_model.journal.official.issn_print

        self.save()

        return instance_model
