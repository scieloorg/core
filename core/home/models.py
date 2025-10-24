from django.conf import settings
from django.db import models
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.response import TemplateResponse
from django.utils.translation import activate, get_language, gettext
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from wagtail import blocks
from wagtail.admin.panels import FieldPanel, FieldRowPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.forms.models import AbstractFormField
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.contrib.routable_page.models import RoutablePageMixin, re_path
from wagtail.fields import RichTextField, StreamField
from wagtail.models import Locale, Page
from wagtailcaptcha.models import WagtailCaptchaEmailForm
from core.home.utils.get_social_networks import get_social_networks

from collection.models import Collection
from journal.choices import STUDY_AREA
from journal.models import OwnerHistory, SciELOJournal

SCIELO_STATUS_CHOICES = ["C", "D", "S"]

def _get_current_locale():
    lang = get_language()
    try:
        return Locale.objects.get(language_code__iexact=lang)
    except Locale.MultipleObjectsReturned:
        return Locale.objects.filter(language_code__iexact=lang).first()
    except Locale.DoesNotExist:
        return Locale.get_default()
    
def journal_filter_with_values(filters):
    return (
            SciELOJournal.objects.filter(filters)
            .select_related("journal" "collection")
            .values(
                "journal__title",
                "issn_scielo",
                "collection__domain",
                "collection__main_name",
                "status",
            )
            .order_by("journal__title")
        )

def default_journal_filter(search_term, starts_with_letter, active_or_discontinued):
    filters = Q(status__in=SCIELO_STATUS_CHOICES) 
    if search_term:
        filters &= Q(journal__title__icontains=search_term)
    if starts_with_letter:
        filters &= Q(journal__title__istartswith=starts_with_letter)
    if active_or_discontinued:
        filters &= Q(status__in=active_or_discontinued)
    return filters

def _default_context(context):
    context["social_networks"] = get_social_networks("scl")
    context["old_scielo_url"] = settings.SCIELO_OLD_URL
    context["page_about"] = get_page_about()

def get_page_about():
    try:
        locale = _get_current_locale()
        home_page = HomePage.objects.filter(locale=locale).first()
    
        if home_page:
            page_about = (
                home_page.get_children()
                .live()
                .public()
                .type(AboutScieloOrgPage)
                .filter(locale=locale)
                .first()
            )
            if page_about:
                return page_about
    except Exception:
        pass
    return Page.objects.filter(slug="sobre-o-scielo").first()


def as_item(qs, lang_code):
    return [{"obj": obj, "name": obj.get_name_for_language(lang_code)} for obj in qs]

def slug_to_category_code(slug):
    """
    Converte slug (ex: 'agricultural-sciences') para código original (ex: 'Agricultural Sciences')
    """
    words = [word.capitalize() for word in slug.split("-")]
    text = " ".join(words)
    for code, _ in STUDY_AREA:
        if code.lower().replace(",", "") == text.lower().replace(",", ""):
            return code
    return None

def get_translated_categories():
    """
    Retorna lista de categorias com slug e tradução
    [(slug, translated_label), ...]
    """
    categories = []
    for code, label in STUDY_AREA:
        slug = "-".join(code.replace(",", "").split()).lower()
        categories.append((slug, label))
    print(categories)
    return categories


class HomePage(Page):
    subpage_types = [
        "home.AboutScieloOrgPage",
        "home.ListPageJournal",
        "home.ListPageJournalByPublisher",
        "home.ListPageJournalByCategory",
    ]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        lang_code = get_language()
        lang_code = "pt" if lang_code == "pt-br" else lang_code
        collections = (
            Collection.objects.filter(
                domain__isnull=False,
                is_active=True,
                collection_name__language__code2=lang_code,
            )
            .order_by("collection_name__text")
            .prefetch_related("collection_name")
        )
        children_qs = self.get_children().live().specific()

        context["collections_journals"] = as_item(
            qs=collections.filter(Q(status="certified")), lang_code=lang_code
        )
        context["collections_in_development"] = as_item(
            qs=collections.filter(Q(status="development")), lang_code=lang_code
        )
        context["collections_servers_and_repositorios"] = as_item(
            qs=collections.filter(
                (Q(collection_type="repositories") | Q(collection_type="preprints"))
            ),
            lang_code=lang_code,
        )
        context["collections_books"] = as_item(
            qs=collections.filter(Q(collection_type="books")), lang_code=lang_code
        )
        context["collections_others"] = as_item(
            qs=collections.filter(Q(status="diffusion")), lang_code=lang_code
        )
        context["list_journal_pages"] = [
            p for p in children_qs if isinstance(p, ListPageJournal)
        ]
        context["list_journal_by_publisher_pages"] = [
            p for p in children_qs if isinstance(p, ListPageJournalByPublisher)
        ]
        context["list_journal_pages_by_category"] = [
            p for p in children_qs if isinstance(p, ListPageJournalByCategory)
        ]
        context["list_journal_by_publisher_pages"] = [
            p for p in children_qs if isinstance(p, ListPageJournalByPublisher)
        ]
        context["categories"] = get_translated_categories()
        _default_context(context)
        return context


class ListPageJournal(Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))
        filters = default_journal_filter(search_term, starts_with_letter, active_or_discontinued)
        journals = journal_filter_with_values(filters)

        context["journals"] = journals
        _default_context(context)
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
        _default_context(context)
        context["parent_page"] = get_page_about()
        return context


class ListPageJournalByCategory(RoutablePageMixin, Page):
    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))

        filters = default_journal_filter(search_term, starts_with_letter, active_or_discontinued)
        journals = journal_filter_with_values(filters)

        context["journals"] = journals
        _default_context(context)
        context["categories"] = get_translated_categories()
        return context

    @re_path(r'^(?P<category>[\w-]+)/$', name="list_journal_by_category")
    def journals_by_category(self, request, category=None):
        current_lang = request.LANGUAGE_CODE
        category_code = slug_to_category_code(category)
        if not category_code:
            return redirect(self.url)
        
        search_term = request.GET.get("search_term", "")
        starts_with_letter = request.GET.get("start_with_letter", "")
        active_or_discontinued = list(request.GET.get("tab", ""))
        
        filters = default_journal_filter(search_term, starts_with_letter, active_or_discontinued)
        filters &= Q(journal__subject__code=category_code)
        
        journals = journal_filter_with_values(filters)
        context = self.get_context(request)
        context["journals"] = journals
        activate(current_lang)
        context["current_category"] = gettext(category_code)
        return render(request, "home/list_page_journal_by_category.html", context)
    

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
            try:
                locale = _get_current_locale()
            except Locale.DoesNotExist:
                locale = Locale.get_default()
            search_results = AboutScieloOrgPage.objects.live().filter(locale=locale).filter(title__icontains=q)
        context["q"] = q
        context["search_results"] = search_results

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        _default_context(context)
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
