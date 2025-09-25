from haystack import indexes

from journal.models import SciELOJournal

from .models import Article
from .mods_mappings import (MODS_TYPE_OF_RESOURCE_MAPPING, DISPLAY_LABEL, AUDIENCE_MAPPING, ISO_639_1_TO_2B,
                            LATIN_SCRIPT_LANGUAGES, STRUCTURAL_SECTIONS, POLICIES, MAPPING_OAI_STATUS)

from legendarium.formatter import descriptive_format


class ArticleIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)
    # doi
    doi = indexes.MultiValueField(null=True)

    # ids
    ids = indexes.MultiValueField(null=True)

    # URLs
    ur = indexes.MultiValueField(null=True)

    titles = indexes.MultiValueField(index_fieldname="ti", null=True)
    la = indexes.MultiValueField(null=True)
    au = indexes.MultiValueField(null=True)
    kw = indexes.MultiValueField(null=True)
    # toc_sections = indexes.MultiValueField(null=True)
    ab = indexes.MultiValueField(null=True)
    orcid = indexes.MultiValueField(null=True)
    au_orcid = indexes.MultiValueField(null=True)
    collab = indexes.MultiValueField(null=True)

    collection = indexes.MultiValueField(index_fieldname="in", null=True)
    journal_title = indexes.CharField(null=True)
    type = indexes.CharField(model_attr="article_type", null=True)
    pid = indexes.CharField(model_attr="pid_v2", null=True)
    pid_v3 = indexes.CharField(model_attr="pid_v3", null=True)
    publication_year = indexes.CharField(model_attr="pub_date_year", null=True)
    domain = indexes.CharField(null=True)
    issue = indexes.CharField(null=True)
    volume = indexes.CharField(null=True)
    elocation = indexes.CharField(model_attr="elocation_id", null=True)
    start_page = indexes.CharField(model_attr="first_page", null=True)
    end_page = indexes.CharField(model_attr="last_page", null=True)
    pg = indexes.CharField(null=True)
    wok_citation_index = indexes.CharField(null=True)
    subject_areas = indexes.MultiValueField(null=True)
    ta_cluster = indexes.CharField(null=True)
    year_cluster = indexes.CharField(null=True)

    def prepare(self, obj):
        """ "
        Here add the title to with dynamic fields.

        Example ti_* (title and the translations)

        About the prepare function see: https://django-haystack.readthedocs.io/_/downloads/en/master/pdf/
        """
        data = super().prepare(obj)

        # prepare the titles ti_*
        for title in obj.titles.all():
            if title.language:
                data[f"ti_{title.language.code2}"] = title.plain_text
            else:
                data["ti_"] = title.plain_text

        # prepare abstracts
        for ab in obj.abstracts.all():
            if ab.language:
                data[f"ab_{ab.language.code2}"] = ab.plain_text
            else:
                data["ab_"] = ab.plain_text

        if obj.journal:
            collections = obj.collections
            # prepara the fulltext_pdf_*
            # FIXME
            # Article languages nao tem a mesma correpondencia de languages PDF
            for collection in collections:
                for lang in obj.languages.all():
                    data["fulltext_pdf_%s" % (lang.code2)] = (
                        "http://%s/scielo.php?script=sci_pdf&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
                    )

            # prepara the fulltext_html_*
            # FIXME
            # Article languages nao tem a mesma correpondencia de languages HTML
            for collection in collections:
                for lang in obj.languages.all():
                    data["fulltext_html_%s" % (lang.code2)] = (
                        "http://%s/scielo.php?script=sci_arttext&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
                    )

        return data

    def prepare_ids(self, obj):
        """
        This field have all ids for the article.

        Example:
        """
        ids = []

        if obj.pid_v2:
            ids.append(obj.pid_v2)

        if obj.pid_v3:
            ids.append(obj.pid_v3)

        if obj.id:
            ids.append(obj.id)

        return ids

    def prepare_ur(self, obj):
        """
        This field is a URLs for all collection of this article.
        """
        collections = obj.collections
        urls = []

        if obj.journal:
            for collection in collections:
                urls.append(
                    "http://%s/scielo.php?script=sci_arttext&pid=%s"
                    % (collection.domain, obj.pid_v2)
                )

        return urls

    def prepare_journal_title(self, obj):
        if obj.journal:
            return obj.journal.title

    def prepare_subject_areas(self, obj):
        return (
            [subj_areas.value for subj_areas in obj.journal.subject.all()]
            if obj.journal
            else None
        )

    def prepare_ta_cluster(self, obj):
        """
        This function get the SciELOJournal.journal_acron to get the acronym to the journal.
        """
        if obj.journal:
            sci_journals = SciELOJournal.objects.filter(
                journal=obj.journal, collection__is_active=True
            )
            return [sci_journal.journal_acron for sci_journal in sci_journals]

    def prepare_year_cluster(self, obj):
        return str(obj.pub_date_year)

    def prepare_collection(self, obj):
        collections = obj.collections
        return (
            [collection.acron3 for collection in collections] if obj.journal else None
        )

    def prepare_doi(self, obj):
        if obj.doi:
            return [doi.value for doi in obj.doi.all()]

    def prepare_la(self, obj):
        if obj.languages:
            return [language.code2 for language in obj.languages.all()]

    def prepare_titles(self, obj):
        if obj.titles:
            return [title.plain_text for title in obj.titles.all()]

    def prepare_orcid(self, obj):
        if obj.researchers:
            return [research.orcid for research in obj.researchers.all()]

    def prepare_au_orcid(self, obj):
        if obj.researchers:
            return [f"{research.orcid}" for research in obj.researchers.all()]

    def prepare_collab(self, obj):
        if obj.collab:
            return [collab.institution_author for collab in obj.collab.all()]

    def prepare_au(self, obj):
        if obj.researchers:
            return [research.get_full_name for research in obj.researchers.all()]

    def prepare_kw(self, obj):
        if obj.keywords:
            return [keyword.text for keyword in obj.keywords.all()]

    # def prepare_toc_sections(self, obj):
    #     if obj.toc_sections:
    #         return [toc_section.plain_text for toc_section in obj.toc_sections.all()]

    def prepare_issue(self, obj):
        try:
            return obj.issue.number
        except AttributeError:
            pass

    def prepare_volume(self, obj):
        try:
            return obj.issue.volume
        except AttributeError:
            pass

    def prepare_ab(self, obj):
        if obj.abstracts:
            return [abstract.plain_text for abstract in obj.abstracts.all()]

    def prepare_domain(self, obj):
        collections = obj.collections
        try:
            return collections.all()[0].domain
        except AttributeError:
            pass

    def prepare_pg(self, obj):
        return "%s-%s" % (obj.first_page, obj.last_page)

    def prepare_wok_citation_index(self, obj):
        return [wos.code for wos in obj.journal.wos_db.all()] if obj.journal else None

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()


class ArticleOAIIndex(indexes.SearchIndex, indexes.Indexable):
    """
    The format of the data:

        "item.id":1,
        "item.handle":"54v7n5FBfdfC3KYFbbGWZYP",
        "item.id":"54v7n5FBfdfC3KYFbbGWZYP",
        "item.lastmodified":"2022-12-20T15:18:22Z",
        "item.submitter":"submitter",
        "item.deleted":false,
        "item.public":true,
        "item.collections":["TEST"],
        "item.communities":["com_INST01"],
        "metadata.dc.title":["Descripción de estados fenológicos de pecán."],
        "metadata.dc.creator":["PROGRAMA NACIONAL PRODUCCIÓN FRUTÍCOLA"],
        "metadata.dc.subject":["NUEZ",
          "FRUTALES",
          "PECAN",
          "FENOLOGIA"],
        "metadata.dc.description":[""],
        "metadata.dc.date":["2022-12-16T20:50:16Z",
          "2022-12-16T20:50:16Z",
          "2016",
          "2022-12-16T20:50:16Z"],
        "metadata.dc.type":["info:eu-repo/semantics/publishedVersion",
          "info:eu-repo/semantics/report"],
        "metadata.dc.identifier":["http://www.ainfo.inia.uy/consulta/busca?b=pc&id=56088&biblioteca=vazio&busca=56088&qFacets=56088"],
        "metadata.dc.language":["es",
          "spa"],
        "metadata.dc.rights":["info:eu-repo/semantics/openAccess",
          "Acceso abierto"],
        "metadata.dc.source":["reponame:Ainfo",
          "instname:Instituto Nacional de Investigación Agropecuaria",
          "instacron:Instituto Nacional de Investigación Agropecuaria"],
        "item.compile":"<metadata xmlns=\"http://www.lyncode.com/xoai\"\n"

    """

    text = indexes.CharField(document=True, use_template=True)
    id = indexes.CharField(index_fieldname="item.handle", null=True)
    item_id = indexes.CharField(index_fieldname="item.id", null=True)
    updated = indexes.CharField(index_fieldname="item.lastmodified", null=True)
    submitter = indexes.CharField(
        model_attr="creator", index_fieldname="item.submitter", null=True
    )
    deleted = indexes.CharField(index_fieldname="item.deleted", null=True)
    public = indexes.CharField(index_fieldname="item.public", null=True)
    collections = indexes.MultiValueField(index_fieldname="item.collections", null=True)
    communities = indexes.MultiValueField(index_fieldname="item.communities", null=True)
    titles = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.title")
    creator = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.creator")
    collab = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.collab")
    kw = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.subject")
    description = indexes.MultiValueField(index_fieldname="metadata.dc.description")
    dates = indexes.MultiValueField(index_fieldname="metadata.dc.date")
    type = indexes.CharField(
        model_attr="article_type", index_fieldname="metadata.dc.type", null=True
    )
    identifier = indexes.MultiValueField(
        null=True, index_fieldname="metadata.dc.identifier"
    )
    la = indexes.MultiValueField(null=True, index_fieldname="metadata.dc.language")
    license = indexes.MultiValueField(index_fieldname="metadata.dc.rights")
    sources = indexes.MultiValueField(index_fieldname="metadata.dc.source")
    compile = indexes.CharField(
        null=True, index_fieldname="item.compile", use_template=True
    )

    def prepare_id(self, obj):
        """This field is the identifier of the record
        The OAI persistent identifier prefix for SciELO is ``oai:scielo:``
        We are giving preference to pid_v2 then pid-v3 and finally DOI
        """
        return "oai:scielo:%s" % obj.pid_v2 or obj.doi or obj.pid_v3

    def prepare_item_id(self, obj):
        """This field is the identifier of the record
        The OAI persistent identifier prefix for SciELO is ``oai:scielo:``
        We are giving preference to pid_v2 then pid-v3 and finally DOI
        """
        return "oai:scielo:%s" % obj.pid_v2 or obj.doi or obj.pid_v3

    def prepare_updated(self, obj):
        """
        This is the lastmodified to the OAI-PMH protocol.
        The format of the date must be something like: 2024-03-06 15:48:25.
        The strftime: 2022-12-20T15:18:22Z
        The param ``from`` and ``until`` considers this field as filtering.
        """
        return obj.updated.strftime("%Y-%m-%dT%H:%M:%SZ")

    def prepare_deleted(self, obj):
        """This is a soft delete on the index, so in the application which handle
        the data must flag as deleted to the index, by now we are set as ``False``
        """
        return False

    def prepare_public(self, obj):
        """Until now we dont have a field on data set as public,
        by now we are set as ``False``
        """
        return True

    def prepare_collections(self, obj):
        """The ISSN is on SciELO Journal models.SciELOJournal.objects.filter(journal=j)[0].issn_scielo"""
        # set com os issns
        if obj.journal:
            return set([
                j.issn_scielo for j in SciELOJournal.objects.filter(journal=obj.journal)
            ])

    def prepare_communities(self, obj):
        """The collection field is multi-value, so may contain N collection.
        IMPORTANT: the attribute of the ``obj`` is a property with a query which
        can return no record that is very weak.
        """
        if obj.collections:
            if obj.collections:
                return ["com_%s" % col for col in obj.collections]

    def prepare_titles(self, obj):
        """The list of titles."""
        if obj.titles:
            return set([title.plain_text for title in obj.titles.all()])

    def prepare_creator(self, obj):
        """The list of authors is the researchers on the models that related with
        class PersonName, so we used ``select_related`` to ensure that
        person_name is not null.
        """
        if obj.researchers:
            researchers = obj.researchers.select_related("person_name").filter(
                person_name__isnull=False
            )
            return set([str(researcher.person_name) for researcher in researchers])

    def prepare_collab(self, obj):
        """This is the instituional author."""
        if obj.collab:
            return set([collab.collab for collab in obj.collab.all()])

    def prepare_kw(self, obj):
        """The keywords of the article."""
        if obj.keywords:
            return set([keyword.text for keyword in obj.keywords.all()])

    def prepare_description(self, obj):
        """The abstracts of the articles
        This is a property that filter by article ``DocumentAbstract.objects.filter(article=self)``
        """
        if obj.abstracts:
            return set([abs.plain_text for abs in obj.abstracts.all()])

    def prepare_dates(self, obj):
        """This the publication date, that is format by YYYY-MM-DD
        In the model this field is seperated into pub_date_day, pub_date_month and pub_date_year
        """
        return [
            "-".join(
                [
                    obj.pub_date_year or "",
                    obj.pub_date_month or "",
                    obj.pub_date_day or "",
                ]
            ),
        ]

    def prepare_la(self, obj):
        """The language of the article."""
        if obj.languages:
            return set([language.code2 for language in obj.languages.all()])

    def prepare_identifier(self, obj):
        """Add the all identifier to the article:
        PID v2
        PID v3
        DOI
        URL old format:
            Example: https://www.scielo.br/scielo.php?script=sci_arttext&pid=S0102-311X2019000104001&lang=pt
        """
        idents = set()

        if obj.journal:
            collections = obj.collections
            for collection in collections:
                for lang in obj.languages.all():
                    idents.add(
                        "http://%s/scielo.php?script=sci_arttext&pid=%s&tlng=%s"
                        % (
                            collection.domain,
                            obj.pid_v2,
                            lang.code2,
                        )
                    )

        if obj.doi:
            idents.update([doi.value for doi in obj.doi.all()])

        if obj.pid_v2:
            idents.add(obj.pid_v2)

        if obj.pid_v3:
            idents.add(obj.pid_v3)

        return idents

    def prepare_license(self, obj):
        if obj.license and obj.license.license_type:
            return [obj.license.license_type]

    def prepare_sources(self, obj):
        # property no article.
        # Acta Cirúrgica Brasileira, Volume: 37, Issue: 7, Article number: e370704, Published: 10 OCT 2022
        try:
            return obj.source
        except Exception as ex:
            return ""

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.all()


class ArticleOAIMODSIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Índice OAI-PMH para metadados MODS (Metadata Object Description Schema)

    Este índice implementa os elementos principais do padrão MODS conforme especificação:
    https://www.loc.gov/standards/mods/

    Adiciona suporte para metadados MODS sem interferir nos índices existentes.
    """

    # CAMPOS BASE OBRIGATÓRIOS
    text = indexes.CharField(document=True, use_template=True)

    # ELEMENTOS OAI-PMH BÁSICOS
    # Identificador OAI-PMH
    id = indexes.CharField(index_fieldname="item.handle", null=True)
    item_id = indexes.CharField(index_fieldname="item.id", null=True)
    updated = indexes.CharField(index_fieldname="item.lastmodified", null=True)
    submitter = indexes.CharField(
        model_attr="creator", index_fieldname="item.submitter", null=True
    )
    deleted = indexes.CharField(index_fieldname="item.deleted", null=True)
    public = indexes.CharField(index_fieldname="item.public", null=True)
    collections = indexes.MultiValueField(index_fieldname="item.collections", null=True)
    communities = indexes.MultiValueField(index_fieldname="item.communities", null=True)

    # ELEMENTOS MODS - PRIORIDADE ALTA
    # titleInfo (0-n) - Informações sobre títulos do recurso
    mods_title_info = indexes.MultiValueField(
        null=True, index_fieldname="mods.titleInfo"
    )

    # name (0-n) - Informações sobre nomes de pessoas e entidades
    mods_name = indexes.MultiValueField(null=True, index_fieldname="mods.name")

    # typeOfResource (0-n) - Categoria geral do recurso
    mods_type_of_resource = indexes.CharField(
        null=True, index_fieldname="mods.typeOfResource"
    )

    # originInfo (0-n) - Informações sobre origem, criação, publicação
    mods_origin_info = indexes.MultiValueField(
        null=True, index_fieldname="mods.originInfo"
    )

    # language (0-n) - Informações sobre o idioma do conteúdo
    mods_language = indexes.MultiValueField(null=True, index_fieldname="mods.language")

    # identifier (0-n) - Identificador único do recurso
    mods_identifier = indexes.MultiValueField(
        null=True, index_fieldname="mods.identifier"
    )

    # subject (0-n) - Assuntos, tópicos ou conceitos
    mods_subject = indexes.MultiValueField(null=True, index_fieldname="mods.subject")

    # abstract (0-n) - Resumo do conteúdo intelectual
    mods_abstract = indexes.MultiValueField(null=True, index_fieldname="mods.abstract")

    # accessCondition (0-n) - Condições de acesso e uso
    mods_access_condition = indexes.MultiValueField(
        null=True, index_fieldname="mods.accessCondition"
    )

    # relatedItem (0-n) - Recursos relacionados
    mods_related_item = indexes.MultiValueField(
        null=True, index_fieldname="mods.relatedItem"
    )

    # part (0-n) - Informações sobre partes do recurso
    mods_part = indexes.MultiValueField(null=True, index_fieldname="mods.part")

    # # location (0-n) - Localização física ou eletrônica
    # mods_location = indexes.MultiValueField(null=True, index_fieldname="mods.location")
    #
    # # ELEMENTOS MODS - PRIORIDADE MÉDIA-ALTA
    # # physicalDescription (0-n) - Características físicas do recurso
    # mods_physical_description = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.physicalDescription"
    # )
    #
    # # recordInfo (0-n) - Informações sobre o registro de metadados
    # mods_record_info = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.recordInfo"
    # )
    #
    # # extension (0-n) - Metadados não cobertos pelos elementos padrão
    # mods_extension = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.extension"
    # )
    #
    # # note (0-n) - Informação geral em forma de nota
    # mods_note = indexes.MultiValueField(null=True, index_fieldname="mods.note")
    #
    # # genre (0-n) - Categoria que caracteriza estilo/forma
    # mods_genre = indexes.MultiValueField(null=True, index_fieldname="mods.genre")
    #
    # # ELEMENTOS MODS - PRIORIDADE MÉDIA
    # # classification (0-n) - Número ou código de classificação
    # mods_classification = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.classification"
    # )
    #
    # # tableOfContents (0-n) - Sumário ou índice do conteúdo
    # mods_table_of_contents = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.tableOfContents"
    # )
    #
    # # targetAudience (0-n) - Público-alvo do recurso
    # mods_target_audience = indexes.MultiValueField(
    #     null=True, index_fieldname="mods.targetAudience"
    # )
    #
    # # Campo compile para template XML completo
    # compile = indexes.CharField(
    #     null=True, index_fieldname="item.compile", use_template=True
    # )

    # CONFIGURAÇÃO DO ÍNDICE
    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        """
        Define o queryset base para indexação com otimizações.
        Indexa todos os artigos independente do status.
        """
        return (
            self.get_model()
            .objects.select_related("journal", "issue", "license", "creator")
            .prefetch_related(
                "titles", "researchers__person_name", "collab",
                "languages", "keywords", "doi", "abstracts",
                "license_statements", "fundings__funding_source",
                "toc_sections", "journal__scielojournal_set__collection",
                # Otimizações MODS específicas
                "researchers__affiliation__institution__institution_identification",
                "researchers__researcheraka_set__researcher_identifier",
            )
            # Sem filtro de status - indexa todos os artigos
        )

    # MÉTODOS AUXILIARES PRIVADOS
    def _prepare_oai_identifier(self, obj):
        """Método auxiliar para gerar identificador OAI padrão."""
        identifier = obj.pid_v2 or obj.pid_v3
        if obj.doi.exists():
            identifier = identifier or str(obj.doi.first())
        return f"oai:scielo:{identifier}" if identifier else None

    def _safe_get_collections(self, obj):
        """Obtém collections com tratamento seguro de erros."""
        try:
            if hasattr(obj, 'collections') and obj.collections:
                return list(obj.collections)
            return []
        except Exception:
            return []

    def _safe_get_available_urls(self, obj, fmt):
        """Método auxiliar seguro para obter URLs disponíveis."""
        try:
            return obj.get_available(fmt=fmt) if hasattr(obj, "get_available") else []
        except Exception:
            return []

    def _prepare_affiliation_data(self, researcher):
        """Prepara dados de afiliação estruturados"""
        if not researcher.affiliation or not researcher.affiliation.institution:
            return None

        institution = researcher.affiliation.institution
        affiliation_parts = []

        # Nome da instituição
        if institution.institution_identification:
            affiliation_parts.append(institution.institution_identification)

        # Localização estruturada
        if institution.location:
            location_parts = []
            if institution.location.city:
                location_parts.append(institution.location.city)
            if institution.location.state:
                location_parts.append(institution.location.state)
            if institution.location.country:
                location_parts.append(institution.location.country)

            if location_parts:
                affiliation_parts.append(", ".join(location_parts))

        return " - ".join(affiliation_parts) if affiliation_parts else str(researcher.affiliation)

    # MÉTODOS DE PREPARAÇÃO OAI-PMH BÁSICOS
    def prepare_id(self, obj):
        """Identificador OAI-PMH do registro"""
        return self._prepare_oai_identifier(obj)

    def prepare_item_id(self, obj):
        """Identificador do item"""
        return self._prepare_oai_identifier(obj)

    def prepare_updated(self, obj):
        """Data de última modificação no formato OAI-PMH"""
        return obj.updated.strftime("%Y-%m-%dT%H:%M:%SZ")

    def prepare_deleted(self, obj):
        """Flag de exclusão suave"""
        return obj.data_status == "DELETED" if hasattr(obj, "data_status") else False

    def prepare_public(self, obj):
        """Flag de disponibilidade pública"""
        return obj.data_status == "PUBLIC" if hasattr(obj, "data_status") else True

    def prepare_collections(self, obj):
        """Coleções baseadas nos ISSNs do periódico"""
        if obj.journal:
            sci_journals = SciELOJournal.objects.filter(journal=obj.journal)
            return set([j.issn_scielo for j in sci_journals if j.issn_scielo])
        return set()

    def prepare_communities(self, obj):
        """Comunidades baseadas nas coleções"""
        collections = self._safe_get_collections(obj)
        return [f"com_{col.acronym}" for col in collections if hasattr(col, "acronym")]

    # MODS: titleInfo
    def prepare_mods_title_info(self, obj):
        """
        Prepara elemento titleInfo do MODS
        Inclui título principal, subtítulo e variações de título
        """
        titles = []
        if obj.titles.exists():
            for title in obj.titles.all():
                title_data = {
                    "title": title.plain_text,
                    "lang": title.language.code2 if title.language else None,
                }
                # Remove valores None
                title_data = {k: v for k, v in title_data.items() if v is not None}
                titles.append(title_data)
        return titles

    # MODS: name
    def prepare_mods_name(self, obj):
        """
        Prepara elemento name do MODS com estrutura completa

        Implementa todos os subelementos e atributos MODS para nomes:
        - namePart estruturado (given/family/termsOfAddress)
        - múltiplos nameIdentifier (ORCID, LATTES, EMAIL, etc.)
        - afiliação hierárquica estruturada
        - role com autoridade
        - entidades corporativas estruturadas
        """
        names = []

        # PESQUISADORES INDIVIDUAIS
        if obj.researchers.exists():
            researchers = obj.researchers.select_related(
                "person_name",
                "affiliation__institution__institution_identification",
                "affiliation__institution__location__city",
                "affiliation__institution__location__state",
                "affiliation__institution__location__country"
            ).prefetch_related(
                "researcheraka_set__researcher_identifier"
            ).filter(person_name__isnull=False)

            for researcher in researchers:
                name_data = {
                    "type": "personal",
                    "role": {
                        "roleTerm": {
                            "type": "text",
                            "authority": "marcrelator",
                            "text": "author"
                        }
                    }
                }

                # NAMEPART ESTRUTURADO
                name_parts = self._prepare_name_parts(researcher.person_name)
                if name_parts:
                    name_data["namePart"] = name_parts

                # MÚLTIPLOS IDENTIFICADORES
                identifiers = self._prepare_name_identifiers(researcher)
                if identifiers:
                    name_data["nameIdentifier"] = identifiers

                # AFILIAÇÃO ESTRUTURADA
                affiliation = self._prepare_name_affiliation(researcher)
                if affiliation:
                    name_data["affiliation"] = affiliation

                names.append(name_data)

        # AUTORES CORPORATIVOS/INSTITUCIONAIS
        if obj.collab.exists():
            collabs = obj.collab.select_related(
                "affiliation__institution__institution_identification",
                "affiliation__institution__location__city",
                "affiliation__institution__location__state",
                "affiliation__institution__location__country"
            )

            for collab in collabs:
                if collab.collab:  # Verificar se tem texto de colaboração
                    corporate_name = {
                        "type": "corporate",
                        "namePart": collab.collab,
                        "role": {
                            "roleTerm": {
                                "type": "text",
                                "authority": "marcrelator",
                                "text": "author"
                            }
                        }
                    }

                    # Afiliação para entidade corporativa
                    if collab.affiliation:
                        corporate_affiliation = self._prepare_corporate_affiliation(collab.affiliation)
                        if corporate_affiliation:
                            corporate_name["affiliation"] = corporate_affiliation

                    names.append(corporate_name)

        return names

    def _prepare_name_parts(self, person_name):
        """
        Prepara namePart estruturado conforme padrão MODS

        Returns:
            list: Lista de dicionários com type e text para cada parte do nome
        """
        name_parts = []

        # Nome(s) próprio(s) - given names
        if person_name.given_names:
            name_parts.append({
                "type": "given",
                "text": person_name.given_names
            })

        # Sobrenome - family name
        if person_name.last_name:
            name_parts.append({
                "type": "family",
                "text": person_name.last_name
            })

        # Sufixos (Jr., Sr., III, etc.) - terms of address
        if person_name.suffix:
            name_parts.append({
                "type": "termsOfAddress",
                "text": person_name.suffix
            })

        # Se não temos partes estruturadas, usar fullname ou declared_name
        if not name_parts:
            name_text = person_name.fullname or person_name.declared_name
            if name_text:
                name_parts.append({
                    "text": name_text
                })

        return name_parts

    def _prepare_name_identifiers(self, researcher):
        """
        Prepara múltiplos nameIdentifier para um pesquisador

        Returns:
            list: Lista de identificadores com type e text
        """
        identifiers = []

        # Buscar todos os identificadores via ResearcherAKA
        researcher_akas = researcher.researcheraka_set.select_related(
            'researcher_identifier'
        ).all()

        for aka in researcher_akas:
            if aka.researcher_identifier and aka.researcher_identifier.identifier:
                source_name = aka.researcher_identifier.source_name
                identifier_value = aka.researcher_identifier.identifier

                # Mapear source_name para tipos MODS apropriados
                identifier_type = self._map_identifier_type(source_name)

                identifier_data = {
                    "type": identifier_type,
                    "text": identifier_value
                }

                # Para ORCID, adicionar autoridade
                if source_name.upper() == 'ORCID':
                    identifier_data["authority"] = "orcid"

                identifiers.append(identifier_data)

        return identifiers

    def _map_identifier_type(self, source_name):
        """
        Mapeia source_name para tipos MODS padrão

        Args:
            source_name: Nome da fonte do identificador

        Returns:
            str: Tipo MODS apropriado
        """
        mapping = {
            'ORCID': 'orcid',
            'LATTES': 'lattes',
            'EMAIL': 'email',
            'SCOPUS': 'scopus',
            'RESEARCHERID': 'researcherid',
            'GOOGLE_SCHOLAR': 'scholar',
        }

        return mapping.get(source_name.upper(), source_name.lower())

    def _prepare_name_affiliation(self, researcher):
        """
        Prepara afiliação estruturada para pesquisador individual

        Returns:
            str: Texto de afiliação estruturado hierarquicamente
        """
        if not researcher.affiliation:
            return None

        affiliation_parts = []

        try:
            institution = researcher.affiliation.institution
            if not institution:
                return None

            # Nome da instituição (prioridade: identification > levels)
            if institution.institution_identification:
                institution_name = institution.institution_identification.name
                if institution_name:
                    affiliation_parts.append(institution_name)

            # Níveis hierárquicos da organização
            levels = [
                institution.level_1,
                institution.level_2,
                institution.level_3
            ]

            for level in levels:
                if level and level.strip():
                    affiliation_parts.append(level.strip())

            # Localização geográfica estruturada
            location_parts = self._prepare_location_text(institution.location)
            if location_parts:
                affiliation_parts.extend(location_parts)

        except Exception:
            # Fallback para string simples se houver erro
            return str(researcher.affiliation) if researcher.affiliation else None

        return " - ".join(affiliation_parts) if affiliation_parts else None

    def _prepare_corporate_affiliation(self, affiliation):
        """
        Prepara afiliação para entidade corporativa

        Returns:
            str: Texto de afiliação para entidade corporativa
        """
        if not affiliation or not affiliation.institution:
            return None

        return self._prepare_institution_text(affiliation.institution)

    def _prepare_institution_text(self, institution):
        """
        Prepara texto estruturado de uma instituição

        Returns:
            str: Representação textual estruturada da instituição
        """
        parts = []

        try:
            # Nome/identificação principal
            if institution.institution_identification:
                if institution.institution_identification.name:
                    parts.append(institution.institution_identification.name)
                elif institution.institution_identification.acronym:
                    parts.append(institution.institution_identification.acronym)

            # Níveis organizacionais
            levels = [institution.level_1, institution.level_2, institution.level_3]
            for level in levels:
                if level and level.strip():
                    parts.append(level.strip())

            # Localização
            location_parts = self._prepare_location_text(institution.location)
            if location_parts:
                parts.extend(location_parts)

        except Exception:
            # Fallback
            return str(institution) if institution else None

        return " - ".join(parts) if parts else None

    def _prepare_location_text(self, location):
        """
        Prepara texto de localização estruturada

        Returns:
            list: Lista de partes da localização
        """
        if not location:
            return []

        location_parts = []

        try:
            # Cidade
            if location.city and location.city.name:
                location_parts.append(location.city.name)

            # Estado (preferir sigla se disponível)
            if location.state:
                state_text = location.state.acronym or location.state.name
                if state_text:
                    location_parts.append(state_text)

            # País
            if location.country and location.country.name:
                location_parts.append(location.country.name)

        except Exception:
            # Fallback para property formatted_location se disponível
            if hasattr(location, 'formatted_location'):
                return [location.formatted_location]
            elif hasattr(location, '__str__'):
                return [str(location)]

        return location_parts


    # MODS: typeOfResource
    def prepare_mods_type_of_resource(self, obj):
        """
        Prepara elemento typeOfResource do MODS
        """

        # Valor principal
        resource_type = MODS_TYPE_OF_RESOURCE_MAPPING.get(obj.article_type, "text/digital") if obj.article_type else "text/digital"

        # Estrutura base
        type_data = {
            "text": resource_type
        }

        # 1. ID
        pid_for_id = obj.pid_v3 or obj.pid_v2
        if pid_for_id:
            type_data["ID"] = pid_for_id

        # 2. lang
        try:
            primary_language = obj.languages.first() if obj.languages.exists() else None
            if primary_language and hasattr(primary_language, 'code2') and primary_language.code2:
                type_data["lang"] = primary_language.code2
        except Exception:
            pass

        # 3. displayLabel
        if obj.article_type:
            display_label = obj.article_type.replace("-", " ").title()
            type_data["displayLabel"] = display_label

        return type_data

    # MODS: originInfo
    def prepare_mods_origin_info(self, obj):
        """
        Prepara elemento originInfo do MODS com origem de dados correta
        """
        origin_info = []
        origin_data = {}

        try:
            # 1. dateIssued seguro
            if (hasattr(obj, 'pub_date_year') and obj.pub_date_year and
                str(obj.pub_date_year).strip()):

                date_parts = [str(obj.pub_date_year)]

                if (hasattr(obj, 'pub_date_month') and obj.pub_date_month and
                    str(obj.pub_date_month).strip()):
                    date_parts.append(str(obj.pub_date_month).zfill(2))

                    if (hasattr(obj, 'pub_date_day') and obj.pub_date_day and
                        str(obj.pub_date_day).strip()):
                        date_parts.append(str(obj.pub_date_day).zfill(2))

                origin_data["dateIssued"] = {
                    "text": "-".join(date_parts),
                    "encoding": "w3cdtf",
                    "keyDate": "yes"
                }

        except (AttributeError, TypeError, ValueError):
            pass

        # 2. publisher via publisher_history (relacionamento correto)
        publishers = []
        try:
            if (obj.journal and
                hasattr(obj.journal, 'publisher_history') and
                obj.journal.publisher_history.exists()):

                for pub_history in obj.journal.publisher_history.select_related(
                    'institution__institution__institution_identification',
                    'organization'
                ):
                    try:
                        pub_name = None

                        # Tentar nova estrutura Organization primeiro
                        if (pub_history.organization and
                            pub_history.organization.name):
                            pub_name = pub_history.organization.name.strip()

                            if (pub_history.organization.acronym and
                                pub_history.organization.acronym.strip()):
                                pub_name += f" ({pub_history.organization.acronym.strip()})"

                        # Fallback para estrutura Institution legada
                        elif (pub_history.institution and
                              pub_history.institution.institution and
                              pub_history.institution.institution.institution_identification and
                              pub_history.institution.institution.institution_identification.name):

                            inst_id = pub_history.institution.institution.institution_identification
                            pub_name = inst_id.name.strip()

                            if inst_id.acronym and inst_id.acronym.strip():
                                pub_name += f" ({inst_id.acronym.strip()})"

                        if pub_name:
                            publishers.append(pub_name)

                    except (AttributeError, TypeError):
                        continue

            if publishers:
                origin_data["publisher"] = publishers

        except (AttributeError, TypeError):
            pass

        # 3. place via múltiplas fontes com prioridades
        places = []
        try:
            # Fonte 1: contact_location do Journal (prioridade alta)
            if (obj.journal and
                hasattr(obj.journal, 'contact_location') and
                obj.journal.contact_location):

                location = obj.journal.contact_location
                place_terms = self._extract_place_terms_from_location(location)

                if place_terms:
                    places.append({"placeTerm": place_terms})

            # Fonte 2: Location via Publisher Organizations (se não há contact_location)
            if not places and obj.journal and hasattr(obj.journal, 'publisher_history'):
                for pub_history in obj.journal.publisher_history.select_related(
                    'organization__location__city',
                    'organization__location__state',
                    'organization__location__country'
                ):
                    try:
                        if (pub_history.organization and
                            pub_history.organization.location):

                            place_terms = self._extract_place_terms_from_location(
                                pub_history.organization.location
                            )

                            if place_terms:
                                places.append({"placeTerm": place_terms})
                                break  # Usar apenas o primeiro válido

                    except (AttributeError, TypeError):
                        continue

            # Fonte 3: Collections (fallback final)
            if not places:
                try:
                    scielo_journals = obj.journal.scielojournal_set.select_related(
                        'collection'
                    ).filter(collection__is_active=True)

                    for scielo_journal in scielo_journals:
                        collection = scielo_journal.collection
                        if (collection and
                            hasattr(collection, 'main_name') and
                            collection.main_name):
                            # Usar nome da coleção como place genérico
                            place_terms = [{
                                "type": "text",
                                "text": collection.main_name.strip()
                            }]
                            places.append({"placeTerm": place_terms})
                            break

                except (AttributeError, TypeError):
                    pass

            if places:
                origin_data["place"] = places

        except (AttributeError, TypeError):
            pass

        # 4. frequency do Journal
        try:
            if (obj.journal and
                hasattr(obj.journal, 'frequency') and
                obj.journal.frequency and
                obj.journal.frequency.strip()):
                origin_data["frequency"] = obj.journal.frequency.strip()
        except (AttributeError, TypeError):
            pass

        # 5. Atributos MODS padrão
        origin_data["eventType"] = "publication"

        # Idioma principal
        try:
            if (hasattr(obj, 'languages') and obj.languages.exists()):
                primary_lang = obj.languages.first()
                if (primary_lang and
                    hasattr(primary_lang, 'code2') and
                    primary_lang.code2 and
                    primary_lang.code2.strip()):
                    origin_data["lang"] = primary_lang.code2.strip()
        except (AttributeError, TypeError):
            pass

        if origin_data:
            origin_info.append(origin_data)

        return origin_info

    def _extract_place_terms_from_location(self, location):
        """
        Método auxiliar para extrair placeTerm de um objeto Location
        """
        place_terms = []

        try:
            # Cidade
            if (location.city and
                hasattr(location.city, 'name') and
                location.city.name and
                location.city.name.strip()):
                place_terms.append({
                    "type": "text",
                    "text": location.city.name.strip()
                })

            # Estado
            if location.state:
                if (hasattr(location.state, 'name') and
                    location.state.name and
                    location.state.name.strip()):
                    place_terms.append({
                        "type": "text",
                        "text": location.state.name.strip()
                    })

                if (hasattr(location.state, 'acronym') and
                    location.state.acronym and
                    location.state.acronym.strip()):
                    place_terms.append({
                        "type": "code",
                        "authority": "iso3166-2",
                        "text": location.state.acronym.strip()
                    })

            # País
            if location.country:
                if (hasattr(location.country, 'name') and
                    location.country.name and
                    location.country.name.strip()):
                    place_terms.append({
                        "type": "text",
                        "text": location.country.name.strip()
                    })

                if (hasattr(location.country, 'acronym') and
                    location.country.acronym and
                    location.country.acronym.strip()):
                    place_terms.append({
                        "type": "code",
                        "authority": "iso3166-1-alpha-2",
                        "text": location.country.acronym.strip()
                    })

                if (hasattr(location.country, 'acron3') and
                    location.country.acron3 and
                    location.country.acron3.strip()):
                    place_terms.append({
                        "type": "code",
                        "authority": "iso3166-1-alpha-3",
                        "text": location.country.acron3.strip()
                    })

        except (AttributeError, TypeError):
            pass

        return place_terms

    # MODS: language
    def prepare_mods_language(self, obj):
        """
        Versão otimizada com mapeamento ISO correto
        """
        languages = []

        try:
            if obj.languages.exists():
                for i, lang in enumerate(obj.languages.all()):
                    if not (lang and lang.code2):
                        continue

                    code2 = lang.code2.strip().lower()
                    language_data = {"languageTerm": []}

                    # Código ISO 639-2b (preferido pelo MODS)
                    if code2 in ISO_639_1_TO_2B:
                        language_data["languageTerm"].append({
                            "type": "code",
                            "authority": "iso639-2b",
                            "text": ISO_639_1_TO_2B[code2]
                        })

                    # Nome textual
                    if lang.name:
                        language_data["languageTerm"].append({
                            "type": "text",
                            "text": lang.name.strip()
                        })

                    # Primeiro idioma é primary
                    if i == 0:
                        language_data["usage"] = "primary"

                    # Script latino para idiomas aplicáveis
                    if code2 in LATIN_SCRIPT_LANGUAGES:
                        language_data["scriptTerm"] = [{
                            "type": "code",
                            "authority": "iso15924",
                            "text": "Latn"
                        }]

                    if language_data["languageTerm"]:
                        languages.append(language_data)

        except (AttributeError, TypeError):
            pass

        return languages

    # MODS: identifier
    def prepare_mods_identifier(self, obj):
        """
        Prepara elemento identifier do MODS com taxonomia completa de identificadores SciELO
        """
        identifiers = []

        # 1. DOIs - Padrão internacional (prioridade máxima)
        if obj.doi.exists():
            for doi in obj.doi.all():
                if doi.value:
                    identifier_data = {
                        "type": "doi",
                        "text": doi.value.strip()
                    }

                    if not self._is_valid_doi(doi.value):
                        identifier_data["invalid"] = "yes"

                    identifiers.append(identifier_data)

        # 2. PIDs SciELO - Identificadores primários da plataforma
        if obj.pid_v3:
            identifiers.append({
                "type": "local",
                "displayLabel": "SciELO PID v3",
                "text": obj.pid_v3
            })

        if obj.pid_v2:
            identifiers.append({
                "type": "local",
                "displayLabel": "SciELO PID v2",
                "text": obj.pid_v2
            })

        # 3. Package Identifier - Identificador técnico SPS
        if obj.sps_pkg_name:
            identifiers.append({
                "type": "local",
                "displayLabel": "SPS Package Name",
                "text": obj.sps_pkg_name
            })

        # 4. ISSNs do Journal (via relacionamento otimizado)
        if obj.journal and obj.journal.official:
            official = obj.journal.official

            if official.issn_print:
                identifiers.append({
                    "type": "issn",
                    "displayLabel": "Print ISSN",
                    "text": official.issn_print
                })

            if official.issn_electronic:
                identifiers.append({
                    "type": "issn",
                    "displayLabel": "Electronic ISSN",
                    "text": official.issn_electronic
                })

            if official.issnl:
                identifiers.append({
                    "type": "issnl",
                    "text": official.issnl
                })

        # 5. Identificadores Collection-specific
        collections = self._safe_get_collections(obj)
        for collection in collections:
            # Collection identifiers
            if collection.acron3:
                identifiers.append({
                    "type": "local",
                    "displayLabel": f"Collection Acronym",
                    "text": collection.acron3
                })

            if collection.code:
                identifiers.append({
                    "type": "local",
                    "displayLabel": f"Collection Code",
                    "text": collection.code
                })

        # 6. SciELO Journal identifiers por collection
        if obj.journal:
            for scielo_journal in obj.journal.scielojournal_set.select_related('collection').filter(
                collection__is_active=True
            ):
                collection_label = scielo_journal.collection.acron3

                if scielo_journal.journal_acron:
                    identifiers.append({
                        "type": "local",
                        "displayLabel": f"Journal Acronym ({collection_label})",
                        "text": scielo_journal.journal_acron
                    })

                if scielo_journal.issn_scielo and scielo_journal.issn_scielo != obj.journal.official.issn_print:
                    identifiers.append({
                        "type": "issn",
                        "displayLabel": f"SciELO ISSN ({collection_label})",
                        "text": scielo_journal.issn_scielo
                    })

        # 7. Issue identifiers
        if obj.issue:
            if obj.issue.issue_pid_suffix:
                identifiers.append({
                    "type": "local",
                    "displayLabel": "Issue PID Suffix",
                    "text": obj.issue.issue_pid_suffix
                })

        # 8. URLs estruturados (último para não sobrecarregar)
        for collection in collections:
            if collection.domain and obj.pid_v2:
                # URL canônico principal
                identifiers.append({
                    "type": "uri",
                    "displayLabel": f"Canonical URL ({collection.acron3})",
                    "text": f"https://{collection.domain}/scielo.php?script=sci_arttext&pid={obj.pid_v2}"
                })

        return identifiers

    def _is_valid_doi(self, value):
        """
        Valida formato DOI segundo padrões internacionais
        Referência: https://www.doi.org/doi_handbook/2_Numbering.html
        """
        import re
        if not value:
            return False

        # Remove espaços e converte para minúsculo para validação
        clean_value = value.strip().lower()

        # Padrão básico: 10.xxxx/xxxxx (mínimo 4 dígitos no prefixo)
        basic_pattern = r'^10\.\d{4,}/\S+$'

        return bool(re.match(basic_pattern, clean_value))

    # MODS: subject
    def prepare_mods_subject(self, obj):
        """
        Prepara subject MODS com todas as correlações confirmadas
        """
        subjects = []

        # 1. Keywords do artigo (fonte primária)
        if obj.keywords.exists():
            for keyword in obj.keywords.all():
                subject_data = {"topic": keyword.text}

                if keyword.vocabulary:
                    topic_data = {"text": keyword.text}
                    if keyword.vocabulary.acronym:
                        topic_data["authority"] = keyword.vocabulary.acronym.lower()
                    elif keyword.vocabulary.name:
                        topic_data["authority"] = keyword.vocabulary.name.lower().replace(" ", "-")
                    subject_data = {"topic": topic_data}

                if keyword.language and keyword.language.code2:
                    lang_code = ISO_639_1_TO_2B.get(keyword.language.code2, keyword.language.code2)
                    subject_data["lang"] = lang_code

                subjects.append(subject_data)

        # 2. Subject areas do Journal (CONFIRMADO)
        if obj.journal and obj.journal.subject.exists():
            for subject_area in obj.journal.subject.all():
                if subject_area.value:
                    subjects.append({
                        "topic": {
                            "authority": "scielo-subject-area",
                            "text": subject_area.value
                        }
                    })

        # 3. Subject descriptors do Journal (CONFIRMADO)
        if obj.journal and obj.journal.subject_descriptor.exists():
            for descriptor in obj.journal.subject_descriptor.all():
                if descriptor.value:
                    subjects.append({
                        "topic": {
                            "authority": "scielo-descriptor",
                            "text": descriptor.value
                        }
                    })

        # 4. Web of Knowledge Subject Categories (CONFIRMADO)
        if obj.journal and obj.journal.wos_area.exists():
            for wos_category in obj.journal.wos_area.all():
                if wos_category.value:
                    subjects.append({
                        "topic": {
                            "authority": "wos",
                            "authorityURI": "http://apps.webofknowledge.com/",
                            "text": wos_category.value
                        }
                    })

        # 5. Áreas temáticas do Journal (CONFIRMADO)
        if obj.journal and hasattr(obj.journal, 'thematic_area') and obj.journal.thematic_area.exists():
            for thematic_area_journal in obj.journal.thematic_area.all():
                thematic_area = thematic_area_journal.thematic_area

                # Usar hierarquia: level2 > level1 > level0
                if thematic_area.level2:
                    topic_text = thematic_area.level2
                elif thematic_area.level1:
                    topic_text = thematic_area.level1
                elif thematic_area.level0:
                    topic_text = thematic_area.level0
                else:
                    continue

                subjects.append({
                    "topic": {
                        "authority": "capes-thematic-area",
                        "text": topic_text
                    }
                })

        # 6. TOC Sections (apenas se semanticamente relevantes)
        if obj.toc_sections.exists():
            for section in obj.toc_sections.all():
                if section.plain_text and self._is_subject_relevant_section(section.plain_text):
                    subject_data = {
                        "topic": {
                            "authority": "scielo-toc",
                            "text": section.plain_text
                        }
                    }

                    if section.language and section.language.code2:
                        lang_code = ISO_639_1_TO_2B.get(section.language.code2, section.language.code2)
                        subject_data["lang"] = lang_code

                    subjects.append(subject_data)

        return subjects

    def _is_subject_relevant_section(self, section_text):
        """
        Filtra seções do TOC que representam verdadeiros assuntos temáticos
        """
        if not section_text:
            return False

        section_lower = section_text.lower().strip()

        # Excluir se for exatamente uma seção estrutural
        if section_lower in STRUCTURAL_SECTIONS:
            return False

        # Incluir se parece ser um assunto temático
        # (comprimento razoável, não só números/símbolos)
        if len(section_text.strip()) >= 3 and not section_text.strip().isdigit():
            return True

        return False

    # MODS: abstract
    def prepare_mods_abstract(self, obj):
        """
        Prepara elemento abstract do MODS
        """
        abstracts = []
        if obj.abstracts.exists():
            for abstract in obj.abstracts.all():
                abstract_data = {"text": abstract.plain_text}
                if abstract.language:
                    abstract_data["lang"] = abstract.language.code2

                # DISPLAYLABEL - Rótulo multilíngue
                if abstract.language:
                    if abstract.language.code2 in DISPLAY_LABEL:
                        abstract_data["displayLabel"] = DISPLAY_LABEL[abstract.language.code2]

                abstracts.append(abstract_data)

        return abstracts

    # MODS: accessCondition
    def prepare_mods_access_condition(self, obj):
        """
        Prepara elemento accessCondition do MODS com fontes completamente documentadas.

        FONTES DE DADOS CONFIRMADAS:
        1. Journal.journal_use_license.license_type (JournalLicense)
        2. Journal.use_license.license_type (core.models.License)
        3. Journal.open_access (choices.OA_STATUS)
        4. LicenseStatement.url + license_p (se disponível via relacionamentos)
        5. Collections (políticas inferidas por coleção)
        """
        access_conditions = []

        # 1. LICENÇA ESPECÍFICA DO JOURNAL - FONTE: JournalLicense.license_type
        if (obj.journal and
            obj.journal.journal_use_license and
            obj.journal.journal_use_license.license_type):

            license_type = obj.journal.journal_use_license.license_type
            condition_data = {
                "type": "use and reproduction",
                "text": license_type,
                "authority": "scielo-journal-license"
            }

            # Detectar Creative Commons
            if self._is_creative_commons_license(license_type):
                condition_data.update({
                    "authority": "creativecommons",
                    "authorityURI": "https://creativecommons.org/",
                    "displayLabel": "Creative Commons License"
                })

            access_conditions.append(condition_data)

        # 2. LICENÇA GERAL - FONTE: core.models.License.license_type
        elif (obj.journal and
              obj.journal.use_license and
              obj.journal.use_license.license_type):

            license_type = obj.journal.use_license.license_type
            condition_data = {
                "type": "use and reproduction",
                "text": license_type,
                "authority": "scielo-core-license"
            }

            if self._is_creative_commons_license(license_type):
                condition_data.update({
                    "authority": "creativecommons",
                    "authorityURI": "https://creativecommons.org/"
                })

            access_conditions.append(condition_data)

        # 3. LICENSE STATEMENTS - FONTE: LicenseStatement (se implementado relacionamento)
        license_statements = self._get_license_statements(obj)
        for statement in license_statements:
            condition_data = {
                "type": "use and reproduction",
                "text": statement.get("license_p", statement.get("url", ""))
            }

            # URL da licença
            if statement.get("url"):
                condition_data["xlink:href"] = statement["url"]

                # Parse da URL para detectar Creative Commons
                parsed = self._parse_license_url(statement["url"])
                if parsed.get("license_type"):
                    condition_data.update({
                        "authority": "creativecommons",
                        "authorityURI": "https://creativecommons.org/",
                        "displayLabel": f"Creative Commons {parsed['license_type'].upper()}"
                    })

                    if parsed.get("license_version"):
                        condition_data["displayLabel"] += f" {parsed['license_version']}"

            # Idioma da declaração
            if statement.get("language"):
                condition_data["lang"] = statement["language"]

            access_conditions.append(condition_data)

        # 4. RESTRIÇÕES DE ACESSO - FONTE: Journal.open_access (choices.OA_STATUS)
        if obj.journal and obj.journal.open_access:
            restriction = self._map_oa_status_to_restriction(obj.journal.open_access)
            if restriction:
                access_conditions.append({
                    "type": "restriction on access",
                    "text": restriction,
                    "authority": "scielo-oa-model",
                    "displayLabel": f"Open Access Model: {obj.journal.open_access.title()}"
                })

        # 5. POLÍTICAS DE COLEÇÃO - FONTE: Collections relacionadas
        collections = self._safe_get_collections(obj)
        for collection in collections:
            policy = self._get_collection_policy(collection)
            if policy:
                access_conditions.append({
                    "type": "restriction on access",
                    "text": policy,
                    "authority": "scielo-collection-policy",
                    "displayLabel": f"Collection Policy ({collection.acron3})"
                })

        return access_conditions

    def _get_license_statements(self, obj):
        """
        Obtém LicenseStatement relacionados (se implementado).

        FONTE: core.models.LicenseStatement via relacionamentos
        Nota: Relacionamento precisa ser implementado nos modelos Article/Journal
        """
        statements = []

        # Verificar se existe relacionamento (seria necessário adicionar aos modelos)
        if hasattr(obj, 'license_statements') and obj.license_statements.exists():
            for statement in obj.license_statements.all():
                statement_data = {}

                if statement.url:
                    statement_data["url"] = statement.url
                if statement.license_p:
                    statement_data["license_p"] = statement.license_p
                if statement.language:
                    statement_data["language"] = statement.language.code2

                if statement_data:
                    statements.append(statement_data)

        return statements

    def _parse_license_url(self, url):
        """
        Parse de URL de licença usando método do LicenseStatement.

        FONTE: LicenseStatement.parse_url() (método estático existente)
        """
        try:
            from core.models import LicenseStatement
            return LicenseStatement.parse_url(url)
        except Exception:
            return {}

    def _map_oa_status_to_restriction(self, oa_status):
        """
        Mapeia OA_STATUS para restrições MODS.

        FONTE: journal/choices.py - OA_STATUS
        Valores confirmados: ["", "diamond", "gold", "hybrid", "bronze", "green", "closed"]
        """

        return MAPPING_OAI_STATUS.get(oa_status)

    def _is_creative_commons_license(self, license_text):
        """Detecta Creative Commons no texto da licença."""
        if not license_text:
            return False

        license_lower = license_text.lower()
        cc_indicators = [
            'creative commons', 'cc ', 'cc-', 'attribution',
            'by-', 'cc by', 'creativecommons', 'ccby'
        ]

        return any(indicator in license_lower for indicator in cc_indicators)

    def _get_collection_policy(self, collection):
        """
        Política de acesso por coleção SciELO.

        FONTE: Collection model + conhecimento das políticas SciELO
        """
        if not (hasattr(collection, 'acron3') and collection.acron3):
            return None

        return POLICIES.get(collection.acron3.lower())

    # MODS: relatedItem
    def prepare_mods_related_item(self, obj):
        """
        Prepara elemento relatedItem do MODS baseado APENAS em relacionamentos CONFIRMADOS

        FONTES CONFIRMADAS nos modelos fornecidos:
        1. HOST: obj.issue (ForeignKey), obj.journal (ForeignKey) - models.py issue/journal
        2. OTHER FORMAT: obj.format.all() (ArticleFormat) - models.py article
        3. OTHER VERSION: obj.doi.all() (DOI ManyToMany) - models.py doi
        4. PRECEDING/SUCCEEDING: obj.journal.official.old_title/new_title - models.py journal
        5. REFERENCES: collections property e URLs SciELO padrão - models.py article
        """
        related_items = []

        # 1. HOST: Periódico e Fascículo (CONFIRMADO em Issue e Journal models)
        if obj.issue and obj.journal:
            host_item = {
                "type": "host",
                "displayLabel": "Published in"
            }

            # Título do periódico (CONFIRMADO: Journal.title)
            host_item["titleInfo"] = {"title": obj.journal.title}

            # ISSNs via obj.journal.official (CONFIRMADO: OfficialJournal)
            if hasattr(obj.journal, 'official') and obj.journal.official:
                identifiers = []
                if obj.journal.official.issn_print:
                    identifiers.append({
                        "type": "issn",
                        "displayLabel": "Print ISSN",
                        "text": obj.journal.official.issn_print
                    })
                if obj.journal.official.issn_electronic:
                    identifiers.append({
                        "type": "issn",
                        "displayLabel": "Electronic ISSN",
                        "text": obj.journal.official.issn_electronic
                    })
                if obj.journal.official.issnl:
                    identifiers.append({
                        "type": "issnl",
                        "text": obj.journal.official.issnl
                    })
                if identifiers:
                    host_item["identifier"] = identifiers

            # Detalhes do fascículo (CONFIRMADO: Issue.volume, Issue.number, Issue.supplement)
            part_data = {}
            details = []

            if obj.issue.volume:
                details.append({"type": "volume", "number": obj.issue.volume})
            if obj.issue.number:
                details.append({"type": "issue", "number": obj.issue.number})
            if obj.issue.supplement:
                details.append({"type": "supplement", "number": obj.issue.supplement})

            if details:
                part_data["detail"] = details

            # Data de publicação (CONFIRMADO: Issue.year, Article.pub_date_year)
            if obj.issue.year:
                part_data["date"] = str(obj.issue.year)
            elif obj.pub_date_year:
                part_data["date"] = str(obj.pub_date_year)

            if part_data:
                host_item["part"] = part_data

            related_items.append(host_item)

        # 2. OTHER FORMAT: Formatos disponíveis (CONFIRMADO: ArticleFormat model)
        try:
            if hasattr(obj, 'format') and obj.format.exists():
                for article_format in obj.format.all():
                    if article_format.format_name and article_format.valid:
                        format_item = {
                            "type": "otherFormat",
                            "displayLabel": f"{article_format.format_name.upper()} format"
                        }

                        # URL do arquivo se disponível (CONFIRMADO: ArticleFormat.file)
                        if article_format.file and hasattr(article_format.file, 'url'):
                            format_item["xlink:href"] = article_format.file.url

                        # Metadados específicos por formato (CONFIRMADO em tasks.py)
                        format_mapping = {
                            "crossref": "CrossRef XML",
                            "pubmed": "PubMed XML",
                            "pmc": "PMC XML"
                        }
                        if article_format.format_name in format_mapping:
                            format_item["genre"] = format_mapping[article_format.format_name]

                        related_items.append(format_item)

        except Exception:
            # Falha silenciosa se ArticleFormat não estiver disponível
            pass

        # 3. OTHER VERSION: Versões via DOI (CONFIRMADO: DOI model)
        if obj.doi.exists():
            for doi in obj.doi.all():
                if doi.value:
                    # DOI como versão canônica (CONFIRMADO: DOI.value)
                    doi_item = {
                        "type": "otherVersion",
                        "displayLabel": "Canonical DOI version",
                        "xlink:href": f"https://doi.org/{doi.value.strip()}"
                    }

                    # Idioma se disponível (CONFIRMADO: DOI.language)
                    if doi.language and hasattr(doi.language, 'code2') and doi.language.code2:
                        doi_item["lang"] = doi.language.code2

                    related_items.append(doi_item)

        # 4. REFERENCES: URLs das coleções (CONFIRMADO via collections property)
        collections = self._safe_get_collections(obj)
        for collection in collections:
            if hasattr(collection, 'domain') and collection.domain and obj.pid_v2:
                # URL HTML principal (CONFIRMADO: padrão URL SciELO)
                html_item = {
                    "type": "otherVersion",
                    "displayLabel": f"SciELO {collection.acron3 if hasattr(collection, 'acron3') else ''} HTML",
                    "xlink:href": f"https://{collection.domain}/scielo.php?script=sci_arttext&pid={obj.pid_v2}"
                }
                related_items.append(html_item)

                # URL PDF (CONFIRMADO: padrão URL SciELO)
                pdf_item = {
                    "type": "otherFormat",
                    "displayLabel": f"SciELO {collection.acron3 if hasattr(collection, 'acron3') else ''} PDF",
                    "xlink:href": f"https://{collection.domain}/scielo.php?script=sci_pdf&pid={obj.pid_v2}"
                }
                related_items.append(pdf_item)

        # 5. PRECEDING/SUCCEEDING: Títulos anterior/posterior (CONFIRMADO: OfficialJournal)
        if obj.journal and obj.journal.official:
            try:
                # Título anterior (CONFIRMADO: OfficialJournal.old_title)
                if obj.journal.official.old_title.exists():
                    for old_title in obj.journal.official.old_title.all():
                        if old_title.title:
                            preceding_item = {
                                "type": "preceding",
                                "displayLabel": "Previous journal title",
                                "titleInfo": {"title": old_title.title}
                            }
                            related_items.append(preceding_item)

                # Novo título (CONFIRMADO: OfficialJournal.new_title)
                if obj.journal.official.new_title and obj.journal.official.new_title.title:
                    succeeding_item = {
                        "type": "succeeding",
                        "displayLabel": "New journal title",
                        "titleInfo": {"title": obj.journal.official.new_title.title}
                    }
                    related_items.append(succeeding_item)

            except Exception:
                pass

        return related_items

    # MODS: part
    def prepare_mods_part(self, obj):
        """
        Prepara elemento part do MODS
        """
        parts = []

        # Informações de paginação
        part_data = {}

        if obj.first_page and obj.last_page:
            part_data["extent"] = {
                "unit": "page",
                "start": obj.first_page,
                "end": obj.last_page,
            }
        elif obj.elocation_id:
            part_data["detail"] = {"type": "elocation-id", "number": obj.elocation_id}

        if part_data:
            parts.append(part_data)

        return parts

    # MODS: location
    def prepare_mods_location(self, obj):
        """
        Prepara elemento location do MODS
        """
        locations = []

        # URLs disponíveis
        urls = []
        for fmt in ["html", "pdf"]:
            urls.extend(self._safe_get_available_urls(obj, fmt))

        for item in urls:
            if isinstance(item, dict) and "url" in item:
                location_data = {
                    "url": {
                        "usage": "primary display",
                        "access": "object in context",
                        "text": item["url"],
                    }
                }
                locations.append(location_data)

        return locations

    # ELEMENTOS PRIORIDADE MÉDIA-ALTA
    def prepare_mods_physical_description(self, obj):
        """
        Prepara elemento physicalDescription do MODS
        """
        physical_desc = []

        # Formato digital
        physical_desc.append({"form": "electronic", "authority": "marcform"})

        # Tipo de mídia
        physical_desc.append({"internetMediaType": "text/html"})

        return physical_desc

    def prepare_mods_record_info(self, obj):
        """
        Prepara elemento recordInfo do MODS
        """
        record_info = []

        record_data = {}

        if obj.created:
            record_data["recordCreationDate"] = obj.created.strftime("%Y-%m-%d")
        if obj.updated:
            record_data["recordChangeDate"] = obj.updated.strftime("%Y-%m-%d")

        record_data["recordIdentifier"] = obj.pid_v3 or obj.pid_v2
        record_data["recordOrigin"] = "SciELO"
        record_data["languageOfCataloging"] = {
            "languageTerm": {"type": "code", "authority": "iso639-2b", "text": "por"}
        }

        # Remove valores None
        record_data = {k: v for k, v in record_data.items() if v is not None}

        if record_data:
            record_info.append(record_data)

        return record_info

    def prepare_mods_extension(self, obj):
        """
        Prepara elemento extension do MODS
        Para metadados específicos do SciELO/SPS
        """
        extensions = []

        # Informações específicas do SciELO
        scielo_elements = {}

        if obj.sps_pkg_name:
            scielo_elements["sps_pkg_name"] = obj.sps_pkg_name
        if hasattr(obj, "data_status") and obj.data_status:
            scielo_elements["data_status"] = obj.data_status
        if hasattr(obj, "valid") and obj.valid is not None:
            scielo_elements["valid"] = obj.valid

        # Financiamentos
        if obj.fundings.exists():
            funding_data = []
            for funding in obj.fundings.all():
                funding_info = {
                    "award_id": funding.award_id,
                    "funding_source": (
                        funding.funding_source.name if funding.funding_source else None
                    ),
                }
                # Remove valores None
                funding_info = {k: v for k, v in funding_info.items() if v is not None}
                funding_data.append(funding_info)

            if funding_data:
                scielo_elements["fundings"] = funding_data

        if scielo_elements:
            scielo_extension = {
                "namespace": "http://scielo.org/extensions",
                "elements": scielo_elements,
            }
            extensions.append(scielo_extension)

        return extensions

    def prepare_mods_note(self, obj):
        """
        Prepara elemento note do MODS
        """
        notes = []

        # Informações do pacote SPS
        if obj.sps_pkg_name:
            notes.append({"type": "sps-package", "text": obj.sps_pkg_name})

        # Status dos dados
        if hasattr(obj, "data_status") and obj.data_status:
            notes.append({"type": "data-status", "text": obj.data_status})

        return notes

    def prepare_mods_genre(self, obj):
        """
        Prepara elemento genre do MODS
        """
        genres = []

        if obj.article_type:
            # Mapeamento de tipos de artigo para gêneros MODS
            genre_mapping = {
                "research-article": "research article",
                "review-article": "review article",
                "case-report": "case report",
                "editorial": "editorial",
                "letter": "letter",
                "brief-report": "brief report",
                "correction": "correction",
                "retraction": "retraction",
            }

            genre = genre_mapping.get(obj.article_type, obj.article_type)
            genres.append({"authority": "scielo", "text": genre})

        return genres

    # ELEMENTOS PRIORIDADE MÉDIA
    def prepare_mods_classification(self, obj):
        """
        Prepara elemento classification do MODS
        """
        classifications = []

        # Áreas temáticas baseadas em seções do sumário
        if obj.toc_sections.exists():
            for section in obj.toc_sections.all():
                section_text = (
                    section.plain_text
                    if hasattr(section, "plain_text")
                    else str(section)
                )
                if section_text:
                    classifications.append(
                        {"authority": "scielo-toc", "text": section_text}
                    )

        # Áreas temáticas do periódico
        if (
            obj.journal
            and hasattr(obj.journal, "subject")
            and obj.journal.subject.exists()
        ):
            for subject_area in obj.journal.subject.all():
                if hasattr(subject_area, "value") and subject_area.value:
                    classifications.append(
                        {"authority": "scielo-subject-area", "text": subject_area.value}
                    )

        return classifications

    def prepare_mods_table_of_contents(self, obj):
        """
        Prepara elemento tableOfContents do MODS
        """
        # Por enquanto retorna lista vazia
        # Pode ser implementado quando houver dados de sumário disponíveis
        return []

    def prepare_mods_target_audience(self, obj):
        """
        Prepara elemento targetAudience do MODS
        """
        audiences = []

        # Baseado no tipo de artigo, inferir audiência
        if obj.article_type:
            audience = AUDIENCE_MAPPING.get(obj.article_type, "researchers")
            audiences.append({"authority": "scielo", "text": audience})

        return audiences
