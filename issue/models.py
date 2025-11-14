from django.utils.functional import cached_property

from django.db import IntegrityError, models
from django.utils.translation import gettext_lazy as _
from modelcluster.fields import ParentalKey
from modelcluster.models import ClusterableModel
from wagtail.admin.panels import FieldPanel, InlinePanel, ObjectList, TabbedInterface
from wagtail.fields import RichTextField
from wagtail.models import Orderable
from wagtailautocomplete.edit_handlers import AutocompletePanel

from core.forms import CoreAdminModelForm
from core.models import (
    BaseExporter,
    BaseLegacyRecord,
    CommonControlField,
    Language,
    License,
    CharFieldLangMixin
)
from core.utils.date_utils import get_date_range
from journal.models import Journal, JournalTableOfContents
from location.models import City
from .utils.extract_digits import _get_digits
from tracker.models import UnexpectedEvent


class AMIssue(BaseLegacyRecord):
    """
    Modelo que representa a coleta de dados de Issue na API Article Meta.

    from:
        https://articlemeta.scielo.org/api/v1/issue/?collection={collection}&code={code}"
    """

    pid = models.CharField(
        _("PID"),
        max_length=17,
        blank=True,
        null=True,
    )
    new_record = models.ForeignKey(
        "Issue",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="legacy_issue",
    )

    class Meta:
        verbose_name = _("Legacy issue")
        verbose_name_plural = _("Legacy issues")
        indexes = [
            models.Index(
                fields=[
                    "pid",
                ]
            ),
        ]

    panels = [
        AutocompletePanel("collection"),
        FieldPanel("pid"),
        FieldPanel("status"),
        FieldPanel("processing_date"),
        FieldPanel("url"),
        FieldPanel("data", read_only=True),
    ]


class Issue(CommonControlField, ClusterableModel):
    """
    Class that represent an Issue
    """

    journal = models.ForeignKey(
        Journal,
        verbose_name=_("Journal"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    license = models.ManyToManyField(License, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, blank=True, null=True)
    number = models.CharField(_("Issue number"), max_length=20, null=True, blank=True)
    volume = models.CharField(_("Issue volume"), max_length=20, null=True, blank=True)
    season = models.CharField(
        _("Issue season"),
        max_length=20,
        null=True,
        blank=True,
        help_text="Ex: Jan-Abr.",
    )
    year = models.CharField(_("Issue year"), max_length=4, null=True, blank=True)
    month = models.CharField(_("Issue month"), max_length=20, null=True, blank=True)
    supplement = models.CharField(_("Supplement"), max_length=20, null=True, blank=True)
    markup_done = models.BooleanField(_("Markup done"), default=False)
    order = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text=_(
            "This number controls the order issues appear for a specific year on the website grid"
        ),
    )
    issue_pid_suffix = models.CharField(max_length=4, null=True, blank=True)
    issue_folder = models.CharField(
        _("Issue folder"),
        max_length=20,
        null=True,
        blank=True,
        help_text=_("Format: vXnYsZ (e.g., v10n2s1)"),
    )

    autocomplete_search_field = "journal__title"

    def autocomplete_label(self):
        return str(self)

    base_form_class = CoreAdminModelForm

    panels_issue = [
        AutocompletePanel("journal"),
        FieldPanel("volume"),
        FieldPanel("number"),
        FieldPanel("supplement"),
        InlinePanel("issue_title", label=_("Issue title")),
    ]

    panels_operation = [
        AutocompletePanel("license"),
        FieldPanel("order"),
        FieldPanel("markup_done"),
        FieldPanel("issue_pid_suffix", read_only=True),
        FieldPanel("issue_folder", read_only=True),
        FieldPanel("creator", read_only=True),
        FieldPanel("updated_by", read_only=True),
    ]

    panels_bibl = [
        AutocompletePanel("city"),
        FieldPanel("season"),
        FieldPanel("month"),
        FieldPanel("year"),
        InlinePanel("bibliographic_strip"),
    ]

    panels_table_of_contents = [
        # NOVO: substitui sections e code_sections
        InlinePanel("table_of_contents", label=_("Table of Contents Sections")),
    ]

    edit_handler = TabbedInterface(
        [
            ObjectList(panels_issue, heading=_("Issue")),
            ObjectList(panels_operation, heading=_("Operation")),
            ObjectList(panels_bibl, heading=_("Bibliographic Strip")),
            ObjectList(panels_table_of_contents, heading=_("Sections")),
        ]
    )

    class Meta:
        verbose_name = _("Issue")
        verbose_name_plural = _("Issues")
        indexes = [
            # Composite indexes for common query patterns
            models.Index(
                fields=["journal", "year", "volume", "number", "supplement"],
                name="issue_journal_identification"
            ),
            models.Index(
                fields=["journal", "markup_done"],
                name="issue_journal_markup_status"
            ),
            # Single field indexes for frequent lookups
            models.Index(
                fields=["journal", "issue_folder"],
                name="issue_journal_folder_idx"
            ),
        ]

    def __str__(self):
        return self.short_identification

    def generate_issue_folder(self):
        """
        Gera o identificador do issue no formato vXnYsZ.
        
        Returns:
            str: String no formato vXnYsZ (ex: v10n2s1, v5n3, n2s1)
        """
        values = (self.volume, self.number, self.supplement)
        labels = ("v", "n", "s")
        return "".join(
            [f"{label}{value}" for label, value in zip(labels, values) if value]
        )

    @property
    def short_identification(self):
        if self.journal:
            return f"{self.journal.title} {self.issue_folder} [{self.journal.collection_acrons}]"
        return f"{self.issue_folder}"

    def create_legacy_keys(self, user=None, force_update=None):
        if not force_update:
            if self.legacy_issue.count() == self.journal.scielojournal_set.count():
                return

        if not self.issue_pid_suffix:
            self.issue_pid_suffix = self.generate_issue_pid_suffix()
            self.save()

        for sj in self.journal.scielojournal_set.all():
            pid = f"{sj.issn_scielo}{self.year}{self.issue_pid_suffix}"
            am_issue = AMIssue.create_or_update(
                pid, sj.collection, None, user, status="done", new_record=self
            )

    def get_legacy_keys(self, collection_acron_list=None, is_active=None):
        params = {}
        if collection_acron_list:
            params["collection__acron3__in"] = collection_acron_list
        if is_active:
            params["collection__is_active"] = bool(is_active)
        data = {}
        for item in self.legacy_issue.filter(**params):
            data[item.collection.acron3] = item.legacy_keys
        if not data:
            UnexpectedEvent.create(
                exception=ValueError("No legacy keys found for issue"),
                detail={
                    "operation": "Issue.get_legacy_keys",
                    "issue": str(self),
                    "collection_acron_list": collection_acron_list,
                    "is_active": is_active,
                    "params": params,
                    "legacy_issue_count": self.legacy_issue.count(),
                },
            )
        return list(data.values())

    def select_collections(self, collection_acron_list=None, is_activate=None):
        if not self.journal:
            raise ValueError(f"{self} has no journal")
        return self.journal.select_collections(collection_acron_list, is_activate)

    def select_journals(self, collection_acron_list=None):
        if not self.journal:
            raise ValueError(f"{self} has no journal")
        return self.journal.select_items(collection_acron_list)

    @classmethod
    def select_issues(
        cls,
        collection_acron_list=None,
        journal_acron_list=None,
        journal_pid_list=None,
        publication_year=None,
        volume=None,
        number=None,
        supplement=None,
        from_date=None,
        until_date=None,
        days_to_go_back=None,
    ):
        """
        Método para filtrar issues com base em múltiplos critérios.

        Args:
            collection_acron_list: Lista de acrônimos de coleções (via SciELOJournal)
            journal_acron_list: Lista de acrônimos de journals
            publication_year: Ano de publicação
            volume: Volume do issue
            number: Número do issue
            supplement: Suplemento do issue
            from_date: Data inicial de atualização
            until_date: Data final de atualização
            days_to_go_back: Número de dias para voltar

        Returns:
            QuerySet de Issues filtradas
        """
        params = {}
        if collection_acron_list:
            params["journal__scielojournal__collection__acron3__in"] = (
                collection_acron_list
            )
        if journal_acron_list:
            params["journal__scielojournal__journal_acron__in"] = journal_acron_list
        if journal_pid_list:
            params["journal__scielojournal__pid__in"] = journal_pid_list
        if publication_year:
            params["year"] = publication_year
        if volume:
            params["volume"] = volume
        if number:
            params["number"] = number
        if supplement:
            params["supplement"] = supplement
        if from_date or until_date or days_to_go_back:
            from_date_str, until_date_str = get_date_range(
                from_date, until_date, days_to_go_back
            )
            params["updated__range"] = (from_date_str, until_date_str)
        queryset = cls.objects.filter(**params).select_related("journal").distinct()
        if not queryset.exists():
            UnexpectedEvent.create(
                exception=ValueError("No issues found for the given filters"),
                detail={
                    "function": "Issue.select_issues",
                    "params": params,
                },
            )
        return queryset
    
    @property
    def data(self):
        d = dict()
        if self.journal:
            d.update(self.journal.data)
        d.update(
            {
                "issue__number": self.number,
                "issue__volume": self.volume,
                "issue__season": self.season,
                "issue__year": self.year,
                "issue__month": self.month,
                "issue__supplement": self.supplement,
            }
        )
        return d

    @property
    def bibliographic(self):
        return [bs.data for bs in self.bibliographic_strip.all()]

    @classmethod
    def get(
        cls,
        journal,
        year,
        volume=None,
        number=None,
        supplement=None,
    ):
        """
        Get an existing Issue based on journal and issue identification.
        """
        if not journal and not year:
            raise ValueError("Journal and year are required")
        
        params = {'journal': journal}
        if year is not None:
            params['year'] = year
        if number is not None:
            params['number'] = number
        if volume is not None:
            params['volume'] = volume
        if supplement is not None:
            params['supplement'] = supplement
        
        try:
            return cls.objects.get(**params)
        except cls.MultipleObjectsReturned:
            return cls.objects.filter(**params).first()
        except cls.DoesNotExist:
            raise cls.DoesNotExist(f"Issue not found with parameters: {params}")

    @classmethod
    def create(
        cls,
        user,
        journal,
        number,
        volume,
        season,
        year,
        month,
        supplement,
        markup_done=False,
        issue_pid_suffix=None,
        order=None,
        **kwargs
    ):
        """
        Create a new Issue instance.
        """
        if not user:
            raise ValueError("User is required")
            
        issue = cls()
        issue.journal = journal
        issue.number = number
        issue.volume = volume
        issue.season = season
        issue.year = year
        issue.month = month
        issue.supplement = supplement
        issue.markup_done = markup_done
        issue.creator = user
        
        # Set additional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(issue, key):
                setattr(issue, key, value)
        
        # Generate computed fields if not provided
        issue.order = order or issue.generate_order()
        issue.issue_pid_suffix = issue_pid_suffix or issue.generate_issue_pid_suffix()
        issue.issue_folder = issue.generate_issue_folder()
        
        try:
            issue.save()
            return issue
        except IntegrityError:
            # If creation fails due to integrity error, try to get existing
            return cls.get(
                journal=journal,
                year=year,
                volume=volume,
                number=number,
                supplement=supplement
            )

    @classmethod
    def get_or_create(
        cls,
        user,
        journal,
        number,
        volume,
        season,
        year,
        month,
        supplement,
        markup_done=False,
        issue_pid_suffix=None,
        order=None,
        **kwargs
    ):
        """
        Get an existing Issue or create a new one.
        """
        try:
            return cls.get(
                journal=journal,
                year=year,
                volume=volume,
                number=number,
                supplement=supplement
            )
        except cls.DoesNotExist:
            return cls.create(
                user=user,
                journal=journal,
                number=number,
                volume=volume,
                season=season,
                year=year,
                month=month,
                supplement=supplement,
                markup_done=markup_done,
                issue_pid_suffix=issue_pid_suffix,
                order=order,
                **kwargs
            )

    def add_am_issue(self, user, am_issue):
        """
        Adiciona relacionamento com AMIssue (legacy) ao Issue.
        
        Args:
            user: Usuário responsável pela operação
            am_issue: Instância do AMIssue a ser associada
            
        Returns:
            bool: True se associação foi criada/atualizada com sucesso
        """
        if not am_issue:
            return False
            
        try:
            # Verifica se já existe relacionamento
            if am_issue in self.legacy_issue.all():
                return True
                
            # Adiciona relacionamento
            self.legacy_issue.add(am_issue)
            
            # Atualiza AMIssue com referência ao novo Issue
            am_issue.new_record = self
            am_issue.status = "completed"
            am_issue.updated_by = user
            am_issue.save()
            
            return True
            
        except Exception as e:
            import sys
            exc_type, exc_value, exc_traceback = sys.exc_info()
            UnexpectedEvent.create(
                exception=e,
                exc_traceback=exc_traceback,
                detail={
                    "function": "Issue.add_am_issue",
                    "issue": str(self),
                    "am_issue": str(am_issue),
                    "user": str(user),
                }
            )
            return False

    def add_sections(self, user, section_list, collection):
        """
        Adiciona seções ao Issue usando o novo modelo JournalTableOfContents.
        
        Args:
            user: Usuário responsável pela operação
            section_list: Lista de dicionários com dados das seções
            collection: Coleção associada ao journal
        """
        if not section_list:
            return
            
        for item in section_list:
            section_title = item.get("t")
            if not section_title:
                continue
            language = item.get("l")
            if not language:
                continue

            journal_toc = JournalTableOfContents.create_or_update(
                user,
                self.journal,
                collection,
                language,
                section_title,
                item.get("c"),
            )
            TableOfContents.create_or_update(
                user=user,
                issue=self,
                journal_toc=journal_toc,
            )

    def add_bibliographic_strips(self, user, bibliographic_strips_data):
        """
        Adiciona tiras bibliográficas ao Issue.
        
        Args:
            user: Usuário responsável pela operação
            bibliographic_strips_data: Lista de dicionários com dados das tiras
                                     Formato: [{"text": "text", "language": language_obj}, ...]
        """
        if not bibliographic_strips_data:
            return
            
        for item in bibliographic_strips_data:
            text = item.get("text")
            language = item.get("language")
            
            if not text or not language:
                continue
                
            BibliographicStrip.get_or_create(
                user=user,
                issue=self,
                language=language,
                text=text,
            )

    def add_issue_titles(self, user, issue_titles_data):
        """
        Adiciona títulos ao Issue.
        
        Args:
            user: Usuário responsável pela operação
            issue_titles_data: Lista de dicionários com dados dos títulos
                              Formato: [{"title": "title", "language": language_obj}, ...]
        """
        if not issue_titles_data:
            return
            
        for item in issue_titles_data:
            title = item.get("title")
            language = item.get("language")
            
            if not title or not language:
                continue
                
            IssueTitle.get_or_create(
                user=user,
                issue=self,
                language=language,
                title=title,
            )

    @property
    def total_articles(self):
        return self.article_set.count()

    def articlemeta_format(self, collection):
        # Evita importacao circular
        from .formats.articlemeta_format import get_articlemeta_format_issue
        return get_articlemeta_format_issue(self, collection)

    def save(self, *args, **kwargs):
        # Gerar campos computados se estiverem ausentes
        if not self.order:
            self.order = self.generate_order()
        if not self.issue_pid_suffix:
            self.issue_pid_suffix = self.generate_issue_pid_suffix()
        if not self.issue_folder:
            self.issue_folder = self.generate_issue_folder()
            
        super().save(*args, **kwargs)
        
        if self.journal:  # Só cria se tiver journal associado
            self.create_legacy_keys(user=self.creator, force_update=True)

    def generate_issue_pid_suffix(self):
        return str(self.generate_order()).zfill(4)

    def generate_order_supplement(self, suppl_start=1000):
        suppl_val = _get_digits(self.supplement)
        return suppl_start + suppl_val

    def generate_order_number(self, spe_start=2000):
        parts = self.number.split("spe")[-1]
        spe_val = _get_digits(parts)
        return spe_start + spe_val

    def generate_order(self, suppl_start=1000, spe_start=2000):
        if self.supplement is not None:
            return self.generate_order_supplement(suppl_start)

        if not self.number:
            return 1

        if "spe" in self.number:
            return self.generate_order_number(spe_start)
        if self.number == "ahead":
            return 9999

        number = _get_digits(self.number)
        return number or 1


class IssueTitle(CommonControlField):
    issue = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="issue_title",
    )
    title = models.CharField(_("Issue Title"), max_length=255, blank=True, null=True)
    language = models.ForeignKey(
        Language, on_delete=models.CASCADE, blank=True, null=True
    )

    panels = [FieldPanel("title"), AutocompletePanel("language")]

    def __str__(self):
        return f"{self.title} ({self.language.code2 if self.language else 'no-lang'})"

    class Meta:
        verbose_name = _("Title")
        verbose_name_plural = _("Titles")
        unique_together = [("issue", "language")]
        indexes = [
            models.Index(
                fields=[
                    "issue", "language"
                ]
            )
        ]

    @property
    def data(self):
        return {
            "title": self.title,
            "language": self.language.code2 if self.language else None,
        }

    @classmethod
    def get(cls, issue, language):
        return cls.objects.get(issue=issue, language=language)
    
    @classmethod
    def create(cls, user, issue, language, title):
        try:
            obj = cls()
            obj.issue = issue
            obj.language = language
            obj.title = title
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(issue, language)

    @classmethod
    def get_or_create(cls, user, issue, language, title):
        try:
            return cls.get(issue, language)
        except cls.DoesNotExist:
            return cls.create(user, issue, language, title)   
        

class BibliographicStrip(CharFieldLangMixin, CommonControlField):
    issue = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="bibliographic_strip",
    )
    class Meta:
        verbose_name = _("Bibliographic Strip")
        verbose_name_plural = _("Bibliographic Strips")
        unique_together = [("issue", "language")]
        indexes = [
            models.Index(
                fields=[
                    "issue", "language"
                ]
            )
        ]

    @property
    def data(self):
        return {
            "text": self.text,
            "language": self.language.code2 if self.language else None,
        }

    @classmethod
    def get(cls, issue, language):
        return cls.objects.get(issue=issue, language=language)
    
    @classmethod
    def create(cls, user, issue, language, text):
        try:
            obj = cls()
            obj.issue = issue
            obj.language = language
            obj.text = text
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(issue, language)

    @classmethod
    def get_or_create(cls, user, issue, language, text):
        try:
            return cls.get(issue, language)
        except cls.DoesNotExist:
            return cls.create(user, issue, language, text)        


class IssueExporter(BaseExporter):
    """
    Controla exportações de fascículos para o ArticleMeta
    """

    parent = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="exporter",
        verbose_name=_("Issue"),
    )


class TableOfContents(Orderable, CommonControlField):
    """
    Relacionamento ordenado entre Issue e JournalTableOfContents.
    Este modelo substitui os relacionamentos antigos sections e code_sections.
    """
    issue = ParentalKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="table_of_contents",
        verbose_name=_("Issue"),
    )
    journal_toc = models.ForeignKey(
        JournalTableOfContents,
        on_delete=models.CASCADE,
        verbose_name=_("Table of Contents Section"),
    )
    
    panels = [
        AutocompletePanel("journal_toc"),
    ]
    
    class Meta:
        verbose_name = _("Table of Contents")
        verbose_name_plural = _("Table of Contents")
        unique_together = [("issue", "journal_toc")]
    
    def __str__(self):
        return f"{self.issue} - {self.journal_toc}"

    @classmethod
    def get(cls, issue, journal_toc):
        return cls.objects.get(issue=issue, journal_toc=journal_toc)
    
    @classmethod
    def create(cls, user, issue, journal_toc):
        try:
            obj = cls()
            obj.issue = issue
            obj.journal_toc = journal_toc
            obj.creator = user
            obj.save()
            return obj
        except IntegrityError:
            return cls.get(issue, journal_toc)
    
    @classmethod
    def create_or_update(cls, user, issue, journal_toc):
        try:
            return cls.get(issue=issue, journal_toc=journal_toc)
        except cls.DoesNotExist:
            return cls.create(user=user, issue=issue, journal_toc=journal_toc)
