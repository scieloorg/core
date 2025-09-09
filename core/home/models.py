from django.db import models
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Locale, Page, Site
from wagtailcaptcha.models import WagtailCaptchaEmailForm

from collection.models import Collection
from core.home.utils.get_social_networks import get_social_networks
from journal.choices import STUDY_AREA
from journal.models import OwnerHistory, SciELOJournal


def get_page_about():
    try:
        lang = get_language()
        try:
            locale = Locale.objects.get(language_code__iexact=lang)
        except Locale.MultipleObjectsReturned:
            locale = Locale.objects.filter(language_code__iexact=lang).first()
        except Locale.DoesNotExist:
            # Fallback para locale padrão
            locale = Locale.get_default()
        home_page = HomePage.objects.filter(locale=locale).first()
        page_about = (
            home_page.get_children()
            .live()
            .public()
            .type(AboutScieloOrgPage)
            .filter(locale=locale)
            .first()
        )
    except (Page.DoesNotExist, Locale.DoesNotExist, Page.MultipleObjectsReturned):
        page_about = Page.objects.filter(slug="sobre-o-scielo").first()
    return page_about


class HomePage(Page):
    subpage_types = [
        "home.AboutScieloOrgPage",
        "home.ListPageJournal",
        "home.ListPageJournalByPublisher",
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        collections = Collection.objects.filter(
            domain__isnull=False, is_active=True
        ).order_by("main_name")
        children_qs = self.get_children().live().specific()

        context["collections_journals"] = collections.filter(Q(status="certified"))
        context["collections_in_development"] = collections.filter(
            Q(status="development")
        )
        context["collections_servers_and_repositorios"] = collections.filter(
            (Q(collection_type="repositories") | Q(collection_type="preprints"))
        )
        context["collections_books"] = collections.filter(Q(collection_type="books"))
        context["collections_others"] = collections.filter(Q(status="diffusion"))
        context["categories"] = [item[0] for item in STUDY_AREA]
        context["page_about"] = get_page_about()
        context["list_journal_pages"] = [
            p for p in children_qs if isinstance(p, ListPageJournal)
        ]
        context["list_journal_by_publisher_pages"] = [
            p for p in children_qs if isinstance(p, ListPageJournalByPublisher)
        ]
        context["social_networks"] = get_social_networks("scl")
        return context


class ListPageJournal(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
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
        context["social_networks"] = get_social_networks("scl")
        context["page_about"] = get_page_about()
        return context


class ListPageJournalByPublisher(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
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
        context["social_networks"] = get_social_networks("scl")
        context["page_about"] = get_page_about()
        context["parent_page"] = context["page_about"]
        return context


class FAQItemBlock(blocks.StructBlock):
    question = blocks.CharBlock(required=True)
    body = blocks.RichTextBlock(required=True)
    updated = blocks.DateBlock(required=False)


class AboutScieloOrgPage(Page):
    subpage_types = ["home.AboutScieloOrgPage"]

    body = RichTextField(_("Body"), blank=True)
    external_link = models.URLField(
        _("Link externo"), blank=True, null=True, max_length=2000
    )

    attached_document = models.ForeignKey(
        "wagtaildocs.Document",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text=_("Documento principal desta página"),
    )
    updated = models.DateField(blank=True, null=True)

    list_page = StreamField(
        [
            ("faq_item", FAQItemBlock()),
        ],
        blank=True,
        use_json_field=True,
    )

    content_panels = Page.content_panels + [
        FieldPanel("attached_document"),
        FieldPanel("external_link"),
        FieldPanel("body"),
        FieldPanel("list_page"),
        FieldPanel("updated"),
    ]

    @staticmethod
    def search_pages(request, context):
        q = request.GET.get("q", "").strip()
        search_results = []
        if q:
            site = Site.find_for_request(request)
            pages = Page.objects.live().public()
            if site:
                pages = pages.descendant_of(site.root_page, inclusive=True)

            pages = pages.type(AboutScieloOrgPage)
            search_results = list(pages.search(q))

            context["q"] = q
            context["search_results"] = search_results

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        context["social_networks"] = get_social_networks("scl")
        context["page_about"] = self
        self.search_pages(request, context)
        return context

    class Meta:
        verbose_name = "Página Sobre SciELO"


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
