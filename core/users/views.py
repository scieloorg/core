from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Prefetch
from django.http import JsonResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

from journal.models import Journal, SciELOJournal

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self):
        assert (
            self.request.user.is_authenticated
        )  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


def filter_journals(request):
    # Filtra apenas valores numéricos não vazios
    raw_ids = request.GET.getlist("collections[]")
    collection_ids = [int(cid) for cid in raw_ids if cid.isdigit()]
    if collection_ids:
        journals = (
            Journal.objects.filter(
                scielojournal__collection__id__in=collection_ids,
                scielojournal__collection__is_active=True,
            )
            .select_related("official")
            .prefetch_related(
                Prefetch(
                    "scielojournal_set",
                    queryset=SciELOJournal.objects.select_related("collection").filter(
                        collection__id__in=collection_ids, collection__is_active=True
                    ),
                    to_attr="active_collections",
                )
            )
        )
    else:
        journals = Journal.objects.select_related("official").prefetch_related(
            Prefetch(
                "scielojournal_set",
                queryset=SciELOJournal.objects.select_related("collection").filter(
                    collection__is_active=True
                ),
                to_attr="active_collections",
            )
        )
    journal_list = [{"id": journal.id, "name": str(journal)} for journal in journals]
    return JsonResponse(journal_list, safe=False)
