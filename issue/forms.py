from wagtail.admin.forms import WagtailAdminModelForm


class IssueForm(WagtailAdminModelForm):
    def save_all(self, user):
        issue = super().save(commit=False)

        if self.instance.pk is not None:
            issue.updated_by = user
        else:
            issue.creator = user

        self.save()

        return issue
