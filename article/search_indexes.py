from haystack import indexes

from journal.models import SciELOJournal

from .models import Article

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


# NOVA CLASSE ADICIONADA: ArticleOAIMODSIndex
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

    # location (0-n) - Localização física ou eletrônica
    mods_location = indexes.MultiValueField(null=True, index_fieldname="mods.location")

    # ELEMENTOS MODS - PRIORIDADE MÉDIA-ALTA
    # physicalDescription (0-n) - Características físicas do recurso
    mods_physical_description = indexes.MultiValueField(
        null=True, index_fieldname="mods.physicalDescription"
    )

    # recordInfo (0-n) - Informações sobre o registro de metadados
    mods_record_info = indexes.MultiValueField(
        null=True, index_fieldname="mods.recordInfo"
    )

    # extension (0-n) - Metadados não cobertos pelos elementos padrão
    mods_extension = indexes.MultiValueField(
        null=True, index_fieldname="mods.extension"
    )

    # note (0-n) - Informação geral em forma de nota
    mods_note = indexes.MultiValueField(null=True, index_fieldname="mods.note")

    # genre (0-n) - Categoria que caracteriza estilo/forma
    mods_genre = indexes.MultiValueField(null=True, index_fieldname="mods.genre")

    # ELEMENTOS MODS - PRIORIDADE MÉDIA
    # classification (0-n) - Número ou código de classificação
    mods_classification = indexes.MultiValueField(
        null=True, index_fieldname="mods.classification"
    )

    # tableOfContents (0-n) - Sumário ou índice do conteúdo
    mods_table_of_contents = indexes.MultiValueField(
        null=True, index_fieldname="mods.tableOfContents"
    )

    # targetAudience (0-n) - Público-alvo do recurso
    mods_target_audience = indexes.MultiValueField(
        null=True, index_fieldname="mods.targetAudience"
    )

    # Campo compile para template XML completo
    compile = indexes.CharField(
        null=True, index_fieldname="item.compile", use_template=True
    )

    # CONFIGURAÇÃO DO ÍNDICE
    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        """
        Define o queryset base para indexação com otimizações.
        Filtra apenas artigos válidos e publicados, com queries otimizadas.
        """
        return (
            self.get_model()
            .objects.select_related(
                "journal",
                "issue",
                "license",
                "creator",
            )
            .prefetch_related(
                "titles",
                "researchers__person_name",
                # Otimizações para MODS - Afiliações estruturadas dos pesquisadores
                "researchers__affiliation__institution__institution_identification",
                "researchers__affiliation__institution__location__city",
                "researchers__affiliation__institution__location__state",
                "researchers__affiliation__institution__location__country",
                # Otimizações para MODS - Múltiplos identificadores via ResearcherAKA
                "researchers__researcheraka_set__researcher_identifier",
                # Otimizações para MODS - Colaboradores corporativos estruturados
                "collab__affiliation__institution__institution_identification",
                "collab__affiliation__institution__location__city",
                "collab__affiliation__institution__location__state",
                "collab__affiliation__institution__location__country",
                # Campos originais mantidos
                "collab",
                "languages",
                "keywords",
                "doi",
                "abstracts",
                "license_statements",
                "fundings__funding_source",
                "toc_sections",
                "journal__scielojournal_set__collection",
            )
            .filter(data_status__in=["PUBLIC", "DELETED"])  # Permite soft delete
        )

    # MÉTODOS AUXILIARES PRIVADOS
    def _prepare_oai_identifier(self, obj):
        """Método auxiliar para gerar identificador OAI padrão."""
        identifier = obj.pid_v2 or obj.pid_v3
        if obj.doi.exists():
            identifier = identifier or str(obj.doi.first())
        return f"oai:scielo:{identifier}" if identifier else None

    def _safe_get_collections(self, obj):
        """Método auxiliar seguro para obter coleções."""
        try:
            return (
                list(obj.collections)
                if hasattr(obj, "collections") and obj.collections
                else []
            )
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

    # MODS: name - Implementação Enriquecida
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
            Mapeia article_type para valores MODS apropriados
            """
        # Mapeamento básico de tipos de artigo para tipos MODS
        type_mapping = {
            "research-article": "text",
            "review-article": "text",
            "case-report": "text",
            "editorial": "text",
            "letter": "text",
            "brief-report": "text",
            "correction": "text",
            "retraction": "text",
        }

        article_type = obj.article_type
        return type_mapping.get(article_type, "text") if article_type else "text"

    # MODS: originInfo
    def prepare_mods_origin_info(self, obj):
        """
        Prepara elemento originInfo do MODS
        Inclui informações de publicação
        """
        origin_info = []

        origin_data = {}

        # Data de publicação usando a propriedade pub_date
        if hasattr(obj, "pub_date") and obj.pub_date:
            origin_data["dateIssued"] = obj.pub_date
            origin_data["encoding"] = "w3cdtf"

        # Editor/Publicador
        if obj.journal and hasattr(obj.journal, "publisher") and obj.journal.publisher:
            origin_data["publisher"] = obj.journal.publisher.name

        # Local de publicação
        if obj.journal:
            origin_data["place"] = obj.journal.title

        if origin_data:
            origin_info.append(origin_data)

        return origin_info

    # MODS: language
    def prepare_mods_language(self, obj):
        """
        Prepara elemento language do MODS
        """
        languages = []
        if obj.languages.exists():
            for language in obj.languages.all():
                lang_data = {
                    "languageTerm": {
                        "type": "code",
                        "authority": "iso639-2b",
                        "text": language.code2,
                    }
                }
                languages.append(lang_data)
        return languages

    # MODS: identifier
    def prepare_mods_identifier(self, obj):
        """
        Prepara elemento identifier do MODS
        Inclui PIDs, DOIs e outros identificadores
        """
        identifiers = []

        # PID v2
        if obj.pid_v2:
            identifiers.append({"type": "scielo-pid-v2", "text": obj.pid_v2})

        # PID v3
        if obj.pid_v3:
            identifiers.append({"type": "scielo-pid-v3", "text": obj.pid_v3})

        # DOIs
        if obj.doi.exists():
            for doi in obj.doi.all():
                identifiers.append({"type": "doi", "text": doi.value})

        # URLs disponíveis (HTML e PDF)
        for fmt in ["html", "pdf"]:
            for item in self._safe_get_available_urls(obj, fmt):
                if isinstance(item, dict) and "url" in item:
                    identifiers.append({"type": "uri", "text": item["url"]})

        return identifiers

    # MODS: subject
    def prepare_mods_subject(self, obj):
        """
        Prepara elemento subject do MODS
        """
        subjects = []
        if obj.keywords.exists():
            for keyword in obj.keywords.all():
                subject_data = {"topic": keyword.text}
                # Adiciona idioma se disponível
                if hasattr(keyword, "language") and keyword.language:
                    subject_data["lang"] = keyword.language.code2
                subjects.append(subject_data)
        return subjects

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
                    display_labels = {
                        'pt': 'Resumo',
                        'en': 'Abstract',
                        'es': 'Resumen',
                    }
                    if abstract.language.code2 in display_labels:
                        abstract_data["displayLabel"] = display_labels[abstract.language.code2]

                abstracts.append(abstract_data)

        return abstracts

    # MODS: accessCondition
    def prepare_mods_access_condition(self, obj):
        """
        Prepara elemento accessCondition do MODS
        """
        access_conditions = []

        # Licença principal
        if obj.license:
            license_text = obj.license.license_type or obj.license.name
            if license_text:
                access_conditions.append(
                    {"type": "use and reproduction", "text": license_text}
                )

        # Declarações de licença adicionais
        if obj.license_statements.exists():
            for statement in obj.license_statements.all():
                if statement.statement:
                    access_conditions.append(
                        {"type": "use and reproduction", "text": statement.statement}
                    )

        return access_conditions

    # MODS: relatedItem
    def prepare_mods_related_item(self, obj):
        """
        Prepara elemento relatedItem do MODS
        """
        related_items = []

        # Fascículo (Issue)
        if obj.issue:
            related_item = {"type": "host"}

            # Título do periódico
            if obj.journal:
                related_item["titleInfo"] = {"title": obj.journal.title}

            # Detalhes da parte
            part_details = []
            if obj.issue.volume:
                part_details.append({"type": "volume", "number": obj.issue.volume})
            if obj.issue.number:
                part_details.append({"type": "issue", "number": obj.issue.number})

            if part_details or obj.issue.year:
                related_item["part"] = {}
                if part_details:
                    related_item["part"]["detail"] = part_details
                if obj.issue.year:
                    related_item["part"]["date"] = obj.issue.year

            related_items.append(related_item)

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
            audience_mapping = {
                "research-article": "researchers",
                "review-article": "researchers",
                "case-report": "practitioners",
                "editorial": "general",
                "letter": "general",
                "brief-report": "practitioners",
            }

            audience = audience_mapping.get(obj.article_type, "researchers")
            audiences.append({"authority": "scielo", "text": audience})

        return audiences
