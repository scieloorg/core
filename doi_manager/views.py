from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin import messages

from journal.models import Journal

from .forms import CrossRefConfigurationForm


@login_required
def create_crossref_configuration(request, journal_pk):
    """
    View to create a new CrossRefConfiguration and link it to a Journal.

    Accessible to journal editors who need to create a CrossRefConfiguration
    when none is available for selection via the AutocompletePanel.
    """
    journal = get_object_or_404(Journal, pk=journal_pk)
    journal_edit_url = reverse("wagtailsnippets_journal_journal:edit", args=[journal_pk])

    if request.method == "POST":
        form = CrossRefConfigurationForm(request.POST)
        if form.is_valid():
            config = form.save(commit=False)
            config.creator = request.user
            config.save()
            journal.crossref_configuration = config
            journal.save(update_fields=["crossref_configuration"])
            messages.success(
                request,
                _("CrossRef configuration created and linked to the journal successfully."),
            )
            return HttpResponseRedirect(journal_edit_url)
    else:
        form = CrossRefConfigurationForm()

    context = {
        "form": form,
        "journal": journal,
        "journal_edit_url": journal_edit_url,
    }
    return render(request, "doi_manager/create_crossref_configuration.html", context)
