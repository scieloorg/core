from django.db import models
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.utils.translation import get_language
from modelcluster.fields import ParentalKey
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Locale, Page
from wagtailcaptcha.models import WagtailCaptchaEmailForm

from collection.models import Collection
from core.utils.utils import language_iso
from journal.choices import STUDY_AREA
from journal.models import OwnerHistory, SciELOJournal


class HomePage(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        collections = Collection.objects.all().order_by("main_name")
        children = self.get_children()
        try:
            lang = get_language()
            locale = Locale.objects.get(language_code__iexact=lang)
            page_about = (
                self.get_children()
                .live()
                .public()
                .get(slug="about-scielo", locale=locale)
            )
            context["page_about"] = page_about
        except (Page.DoesNotExist, Locale.DoesNotExist, Page.MultipleObjectsReturned):
            context["page_about"] = Page.objects.filter(slug="about-scielo").first()

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
        lang = get_language()
        locale = Locale.objects.get(language_code__iexact=lang)
        parent_specific_page = (
            self.get_parent()
            .specific.get_children()
            .live()
            .public()
            .get(slug="about-scielo", locale=locale)
        )
        context["page_about"] = parent_specific_page
        category = request.GET.get("category")
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))

        filters = Q()
        filters &= Q(status__in=["C", "D", "S"])

        if category and any(category in item for item in STUDY_AREA):
            filters &= Q(journal__subject__code=category)
        if search_term:
            filters &= Q(journal__title__icontains=search_term)
        if starts_with_letter:
            filters &= Q(journal__title__istartswith=starts_with_letter)
        if active_or_discontinued:
            filters &= Q(status__in=active_or_discontinued)

        journals = (
            SciELOJournal.objects.filter(filters)
            .values(
                "journal__title",
                "issn_scielo",
                "collection__domain",
                "collection__main_name",
                "status",
            )
            .order_by("journal__title")
        )

        context["journals"] = journals
        return context


class ListPageJournalByPublisher(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        lang = get_language()
        locale = Locale.objects.get(language_code__iexact=lang)
        parent_specific_page = (
            self.get_parent()
            .specific.get_children()
            .live()
            .public()
            .get(slug="about-scielo", locale=locale)
        )
        context["page_about"] = parent_specific_page
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))

        filters = Q()
        filters &= Q(journal__scielojournal__status__in=["C", "D", "S"])
        if search_term:
            filters &= Q(journal__title__icontains=search_term) | Q(
                institution__institution__institution_identification__name__icontains=search_term
            )
        if starts_with_letter:
            filters &= Q(journal__title__istartswith=starts_with_letter)
        if active_or_discontinued:
            filters &= Q(journal__scielojournal__status__in=active_or_discontinued)

        publishers = (
            OwnerHistory.objects.filter(
                institution__isnull=False,
                institution__institution__institution_identification__name__isnull=False,
            )
            .filter(filters)
            .select_related(
                "institution__institution__institution_identification",
                "journal",
            )
            .prefetch_related(
                Prefetch(
                    "journal__scielojournal_set",
                    queryset=SciELOJournal.objects.select_related("collection")
                    .filter(status__in=["C", "D", "S"])
                    .order_by("journal__title"),
                )
            )
            .order_by("institution__institution__institution_identification__name")
            .distinct("institution__institution__institution_identification__name")
        )

        context["publishers"] = publishers
        context["parent_page"] = parent_specific_page
        return context


class AboutScieloOrgPage(Page):
    list_page = StreamField(
        [
            ("page", blocks.PageChooserBlock()),
            ("text", blocks.RichTextBlock()),
            ("url", blocks.URLBlock()),
            ("document", DocumentChooserBlock()),
        ],
        blank=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("list_page"),
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["page_about"] = self
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
                            "message": (
                                self.thank_you_text
                                if self.thank_you_text
                                else "Formulário enviado com sucesso!"
                            ),
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
