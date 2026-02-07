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
        # List of related history managers to process
        history_manager_names = [
            "publisher_history",
            "owner_history",
            "sponsor_history",
            "copyright_holder_history",
        ]

        for manager_name in history_manager_names:
            related_manager = getattr(self.instance, manager_name, None)
            if related_manager is None:
                continue

            # Use select_related to avoid N+1 queries
            queryset = related_manager.all().select_related(
                "institution",
                "institution__institution",
                "institution__institution__institution_identification",
                "institution__institution__location",
                "institution__institution__location__country",
                "institution__institution__location__state",
                "institution__institution__location__city",
            )

            for history_item in queryset:
                if not history_item.raw_text and history_item.institution:
                    self.instance._migrate_history_to_raw(history_item)


class SciELOJournalModelForm(CoreAdminModelForm):
    def save_all(self, user):
        instance_model = super().save_all(user)

        if self.instance.issn_scielo is None:
            self.instance.issn_scielo = instance_model.journal.official.issn_electronic or instance_model.journal.official.issn_print

        self.save()

        return instance_model
