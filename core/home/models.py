from django.db import models
from django.db.models import Q
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.utils.translation import get_language
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtailcaptcha.models import WagtailCaptchaEmailForm

from collection.models import Collection
from core.utils.utils import language_iso
from institution.models import Institution
from journal.choices import STUDY_AREA
from journal.models import Journal


class HomePage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        lang = language_iso(get_language())
        collections = Collection.objects.all()
        children = self.get_children()

        context["collections_journals"] = collections.filter(
            Q(is_active=True) & Q(status="certified")
        )
        context["collections_in_development"] = collections.filter(
            Q(is_active=True) & Q(status="development")
        )
        context["collections_servers_and_repositorios"] = collections.filter(
            Q(is_active=True)
            & (Q(collection_type="repositories") | Q(collection_type="preprints"))
        )
        context["collections_books"] = collections.filter(
            Q(is_active=True) & Q(collection_type="books")
        )
        context["collections_others"] = collections.filter(
            Q(is_active=True) & Q(status="diffusion")
        )
        context["categories"] = [item[0] for item in STUDY_AREA]
        context["children"] = children
        return context


class ListPageJournal(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        parent_specific_page = self.get_parent().specific
        journals = (
            Journal.objects.filter(scielojournal__status__in=["C", "D", "S"])
            .values(
                "title",
                "scielojournal__issn_scielo",
                "scielojournal__collection__domain",
                "scielojournal__status",
            )
            .distinct("title")
            .order_by("title")
        )

        category = request.GET.get("category")
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = request.GET.get("tab", "")

        publisher = category == "publisher"
        institution = []

        if any(category in item for item in STUDY_AREA):
            journals = journals.filter(subject__code=category)
        elif search_term:
            journals = journals.filter(title__icontains=search_term)
        elif starts_with_letter:
            journals = journals.filter(title__istartswith=starts_with_letter)
        elif active_or_discontinued:
            journals = journals.filter(scielojournal__status=active_or_discontinued)
        elif publisher:
            institution = Institution.objects.all().order_by(
                "institution_identification__name"
            )

        context["search_term"] = search_term
        context["parent_page"] = parent_specific_page
        context["category"] = category
        context["publisher"] = publisher
        context["institution"] = institution
        context["journals"] = journals
        return context


class FormField(AbstractFormField):
    page = ParentalKey("FormPage", on_delete=models.CASCADE, related_name="form_fields")


class FormPage(WagtailCaptchaEmailForm):
    intro = RichTextField(blank=True, help_text="Texto de introdução ao formulário.")
    thank_you_text = RichTextField(
        blank=True,
        help_text="Adicione a mensagem que será exibido após o envio do formulário.",
    )

    def serve(self, request, *args, **kwargs):
        if request.method == "POST":
            form = self.get_form(
                request.POST, request.FILES, page=self, user=request.user
            )

            if request.is_ajax():
                if form.is_valid():
                    self.process_form_submission(form)
                    return JsonResponse(
                        {
                            "alert": "success",
                            "message": self.thank_you_text
                            if self.thank_you_text
                            else "Formulário enviado com sucesso!",
                        }
                    )
                else:
                    return JsonResponse(
                        {
                            "alert": "error",
                            "message": "Erro ao tentar enviar a <strong>formulário!</strong> Verifique os campos obrigatórios. Errors: %s"
                            % form.errors,
                        }
                    )
            else:
                if form.is_valid():
                    form_submission = self.process_form_submission(form)
                    return self.render_landing_page(
                        request, form_submission, *args, **kwargs
                    )
        else:
            form = self.get_form(page=self, user=request.user)

        context = self.get_context(request)
        context["form"] = form
        return TemplateResponse(request, self.get_template(request), context)

    class Meta:
        verbose_name = "Página com formulário."
        verbose_name_plural = "Páginas com formulários."

    content_panels = WagtailCaptchaEmailForm.content_panels + [
        FormSubmissionsPanel(),
        FieldPanel("intro", classname="full"),
        InlinePanel("form_fields", label="Form fields"),
        FieldPanel("thank_you_text", classname="full"),
        MultiFieldPanel(
            [
                FieldRowPanel(
                    [
                        FieldPanel("from_address", classname="col6"),
                        FieldPanel("to_address", classname="col6"),
                    ]
                ),
                FieldPanel("subject"),
            ],
            "Email",
        ),
    ]
