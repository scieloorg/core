from haystack import indexes
from legendarium.formatter import descriptive_format
from django.db.models import Prefetch
from researcher.models import ResearcherAKA

from journal.models import SciELOJournal

from .models import Article


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
        return self.get_model().objects.filter(is_classic_public=True)


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

    # Dublin Core
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

    # MODS - name
    # Nome completo dos autores
    mods_name_text = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.name.text"
    )

    # ORCIDs dos autores
    mods_name_orcid = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.name.orcid"
    )

    # Afiliações estruturadas
    mods_name_affiliation = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.name.affiliation"
    )

    # Papéis (author, editor, etc)
    mods_name_role = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.name.role"
    )

    # MODS - subjects
    # Keywords do artigo
    mods_subject_keyword = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.subject.keyword"
    )

    # Subject areas do journal
    mods_subject_area = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.subject.area"
    )

    # Web of Science categories
    mods_subject_wos = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.subject.wos"
    )

    # Áreas temáticas CAPES
    mods_subject_capes = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.subject.capes"
    )

    # MODS - relatedItem.host
    # Título do periódico
    mods_relateditem_host_title = indexes.CharField(
        null=True, index_fieldname="metadata.mods.relatedItem.host.title"
    )

    # ISSNs do periódico
    mods_relateditem_host_issn = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.relatedItem.host.issn"
    )

    # Volume
    mods_relateditem_host_volume = indexes.CharField(
        null=True, index_fieldname="metadata.mods.relatedItem.host.volume"
    )

    # Número/Issue
    mods_relateditem_host_issue = indexes.CharField(
        null=True, index_fieldname="metadata.mods.relatedItem.host.issue"
    )

    # Suplemento
    mods_relateditem_host_supplement = indexes.CharField(
        null=True, index_fieldname="metadata.mods.relatedItem.host.supplement"
    )

    # MODS - part
    # Página inicial
    mods_part_page_start = indexes.CharField(
        null=True, index_fieldname="metadata.mods.part.pages.start"
    )

    # Página final
    mods_part_page_end = indexes.CharField(
        null=True, index_fieldname="metadata.mods.part.pages.end"
    )

    # Elocation-id (para artigos sem paginação)
    mods_part_elocation = indexes.CharField(
        null=True, index_fieldname="metadata.mods.part.elocation"
    )

    # MODS - identifier
    # ISSN impresso
    mods_identifier_issn_print = indexes.CharField(
        null=True, index_fieldname="metadata.mods.identifier.issn.print"
    )

    # ISSN eletrônico
    mods_identifier_issn_electronic = indexes.CharField(
        null=True, index_fieldname="metadata.mods.identifier.issn.electronic"
    )

    # ISSN-L (linking)
    mods_identifier_issnl = indexes.CharField(
        null=True, index_fieldname="metadata.mods.identifier.issnl"
    )

    # MODS - originInfo
    # Editora(s)
    mods_origininfo_publisher = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.originInfo.publisher"
    )

    # Lugar de publicação
    mods_origininfo_place = indexes.MultiValueField(
        null=True, index_fieldname="metadata.mods.originInfo.place"
    )

    # Data estruturada (w3cdtf)
    mods_origininfo_date = indexes.CharField(
        null=True, index_fieldname="metadata.mods.originInfo.date"
    )

    # MODS - accessCondition
    # Tipo de licença
    mods_accesscondition_license = indexes.CharField(
        null=True, index_fieldname="metadata.mods.accessCondition.license"
    )

    # URL da licença (Creative Commons)
    mods_accesscondition_licenseurl = indexes.CharField(
        null=True, index_fieldname="metadata.mods.accessCondition.licenseURL"
    )

    # Política de Open Access
    mods_accesscondition_openaccess = indexes.CharField(
        null=True, index_fieldname="metadata.mods.accessCondition.openAccess"
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
            return set(
                [
                    j.issn_scielo
                    for j in SciELOJournal.objects.filter(journal=obj.journal)
                ]
            )

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


    # métodos prepare MODS
    def prepare_mods_name_text(self, obj):
        """
        Nomes completos dos autores (flat list)

        JUSTIFICATIVA:
        Complementa dc.creator (Dublin Core) com nomes estruturados no padrão MODS.
        Enquanto dc.creator oferece apenas strings simples, este campo integra-se com
        metadata.mods.name.orcid e metadata.mods.name.affiliation para permitir:
        - Identificação inequívoca de autores via ORCID
        - Rastreamento de produção científica por instituição
        - Métricas bibliométricas precisas
        - Descoberta avançada por autor em sistemas especializados

        MAPEAMENTO:
        Dublin Core dc.creator → MODS <name type="personal"><namePart>

        FONTE DE DADOS:
        - Article.researchers.person_name (pesquisadores individuais)
        - Article.collab.collab (autores corporativos/institucionais)

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <name type="personal">
            <namePart type="given">Neil</namePart>
            <namePart type="family">Brenner</namePart>
            <role>
                <roleTerm type="text">author</roleTerm>
            </role>
        </name>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - Elemento: https://www.loc.gov/standards/mods/userguide/name.html
        - Exemplos: https://www.loc.gov/standards/mods/userguide/examples.html

        Returns:
            list: Lista de strings com nomes completos formatados
            Exemplo: ["Brenner, Neil", "Silva, João", "Instituto Nacional de Pesquisas"]
        """
        names = []

        # Pesquisadores individuais
        if obj.researchers.exists():
            researchers = obj.researchers.select_related("person_name").filter(
                person_name__isnull=False
            )
            names.extend([str(researcher.person_name) for researcher in researchers])

        # Autores corporativos/institucionais
        if obj.collab.exists():
            names.extend([collab.collab for collab in obj.collab.all() if collab.collab])

        return names

    def prepare_mods_name_orcid(self, obj):
        """
        ORCIDs dos autores (flat list)

        JUSTIFICATIVA:
        Identificadores persistentes ORCID são essenciais para:
        - Desambiguação de autores (evita homônimos)
        - Integração com sistemas de gestão de pesquisa (CRIS)
        - Compliance com mandatos de agências de fomento (FAPESP, CNPq, CAPES)
        - Rastreamento de produção científica ao longo do tempo
        - Linkagem com perfis em bases internacionais (WoS, Scopus, PubMed)
        Dublin Core não possui campo para identificadores de pessoa.

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <name><nameIdentifier type="orcid">

        FONTE DE DADOS:
        - ResearcherAKA.researcher_identifier (source_name='ORCID')

        EXEMPLO XML (MODS 3.7):
        <name type="personal">
            <namePart>Silva, João</namePart>
            <nameIdentifier type="orcid" authority="orcid">
                0000-0001-2345-6789
            </nameIdentifier>
            <role>
                <roleTerm type="text" authority="marcrelator">author</roleTerm>
            </role>
        </name>

        REFERÊNCIA OFICIAL:
        - nameIdentifier: https://www.loc.gov/standards/mods/userguide/name.html#nameidentifier
        - ORCID Registry: https://orcid.org/

        Returns:
            list: Lista de ORCIDs no formato 0000-0001-2345-6789
            Exemplo: ["0000-0001-2345-6789", "0000-0002-8765-4321"]
        """
        if not obj.researchers.exists():
            return []

        # Usar set para melhor performance na verificação de duplicatas
        orcids_set = set()

        # Otimização: Prefetch com select_related para evitar N+1 queries
        researchers = obj.researchers.prefetch_related(
            Prefetch(
                'researcheraka_set',
                queryset=ResearcherAKA.objects.select_related('researcher_identifier')
            )
        ).all()

        for researcher in researchers:
            for aka in researcher.researcheraka_set.all():
                if (aka.researcher_identifier and
                    aka.researcher_identifier.source_name and
                    aka.researcher_identifier.source_name.upper() == 'ORCID' and
                    aka.researcher_identifier.identifier):

                    orcid = aka.researcher_identifier.identifier.strip()
                    if orcid:
                        orcids_set.add(orcid)

        # Converter set para lista (ordenada para consistência)
        return sorted(list(orcids_set))

    def prepare_mods_name_affiliation(self, obj):
        """
        Afiliações estruturadas dos autores (flat list)

        JUSTIFICATIVA:
        Informação essencial para:
        - Análises bibliométricas institucionais
        - Rastreamento de colaborações inter-institucionais
        - Estatísticas de produção científica por país/região
        - Validação de compliance com políticas de fomento
        - Identificação de redes de pesquisa
        Dublin Core não possui campo estruturado para afiliações.

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <name><affiliation>

        FONTE DE DADOS:
        - Researcher.affiliation.institution (nome, departamentos, localização)

        EXEMPLO XML (MODS 3.5):
        <name type="personal">
            <namePart>Silva, João</namePart>
            <affiliation>Universidade de São Paulo - Instituto de Física - São Paulo - SP - Brasil</affiliation>
            <role>
                <roleTerm type="text">author</roleTerm>
            </role>
        </name>

        REFERÊNCIA OFICIAL:
        - affiliation: https://www.loc.gov/standards/mods/userguide/name.html#affiliation

        Returns:
            list: Lista de afiliações hierarquicamente estruturadas
            Exemplo: ["USP - Inst. Física - São Paulo - SP - Brasil",
                      "UFRJ - COPPE - Rio de Janeiro - RJ - Brasil"]
        """
        affiliations = []

        if not obj.researchers.exists():
            return affiliations

        researchers = obj.researchers.select_related(
            'affiliation__institution__institution_identification',
            'affiliation__institution__location__city',
            'affiliation__institution__location__state',
            'affiliation__institution__location__country'
        ).all()

        for researcher in researchers:
            if researcher.affiliation:
                affiliation_text = self._format_affiliation(researcher.affiliation)
                if affiliation_text and affiliation_text not in affiliations:
                    affiliations.append(affiliation_text)

        return affiliations

    def prepare_mods_name_role(self, obj):
        """
        Papéis dos autores (flat list)

        JUSTIFICATIVA:
        Distingue tipos de contribuição ao recurso:
        - Autor principal (author)
        - Editor (editor)
        - Tradutor (translator)
        - Revisor (reviewer)
        Utiliza vocabulário controlado MARC Relators para interoperabilidade.

        MAPEAMENTO:
        Dublin Core dc.creator → MODS <name><role><roleTerm authority="marcrelator">

        FONTE DE DADOS:
        - Padrão "author" para todos (artigos científicos SciELO)

        EXEMPLO XML (MODS 3.5):
        <name type="personal">
            <namePart>Brenner, Neil</namePart>
            <role>
                <roleTerm type="text" authority="marcrelator">author</roleTerm>
            </role>
        </name>

        REFERÊNCIA OFICIAL:
        - role: https://www.loc.gov/standards/mods/userguide/name.html#role
        - MARC Relators: https://www.loc.gov/marc/relators/

        Returns:
            list: Lista de papéis sincronizada com mods_name_text
            Exemplo: ["author", "author", "editor"]
        """
        roles = []

        # Pesquisadores individuais = author
        if obj.researchers.exists():
            researchers = obj.researchers.filter(person_name__isnull=False)
            roles.extend(['author'] * researchers.count())

        # Autores corporativos = author
        if obj.collab.exists():
            collabs = [c for c in obj.collab.all() if c.collab]
            roles.extend(['author'] * len(collabs))

        return roles

    def prepare_mods_subject_keyword(self, obj):
        """
        Keywords do artigo com vocabulário controlado

        JUSTIFICATIVA:
        Complementa dc.subject com suporte a vocabulários controlados:
        - Identifica autoridade da keyword (DeCS, MeSH, etc.)
        - Permite buscas mais precisas por assunto
        - Facilita agregação por taxonomias padronizadas
        Dublin Core não diferencia keywords livres de controladas.

        MAPEAMENTO:
        Dublin Core dc.subject → MODS <subject><topic authority="...">

        FONTE DE DADOS:
        - Article.keywords.text
        - Article.keywords.vocabulary (DeCS, MeSH, etc.)

        EXEMPLO XML (MODS 3.7):
        <subject>
            <topic authority="lcsh" valueURI="http://id.loc.gov/authorities/subjects/sh85075538">
                Learning disabilities
            </topic>
        </subject>
        <subject>
            <topic authority="mesh">Diabetes Mellitus</topic>
        </subject>

        Fonte: http://www.loc.gov/standards/mods/v3/mods-3-7-subject-examples.pdf

        REFERÊNCIA OFICIAL:
        - subject: https://www.loc.gov/standards/mods/userguide/subject.html
        - topic: https://www.loc.gov/standards/mods/userguide/subject.html#topic

        Returns:
            list: Lista de keywords
            Exemplo: ["Diabetes Mellitus", "Insulin Resistance", "Obesity"]
        """
        keywords = []

        if obj.keywords.exists():
            for keyword in obj.keywords.all():
                if keyword.text and keyword.text.strip():
                    keywords.append(keyword.text.strip())

        return keywords

    def prepare_mods_subject_area(self, obj):
        """..."""
        areas = []

        # Padronizado: .exists() direto
        if obj.journal and obj.journal.subject.exists():
            for subject_area in obj.journal.subject.all():
                if subject_area.value and subject_area.value.strip():
                    areas.append(subject_area.value.strip())

        return areas

    def prepare_mods_subject_wos(self, obj):
        """..."""
        wos_categories = []

        # Padronizado: .exists() direto
        if obj.journal and obj.journal.wos_area.exists():
            for wos_category in obj.journal.wos_area.all():
                if wos_category.value and wos_category.value.strip():
                    wos_categories.append(wos_category.value.strip())

        return wos_categories

    def prepare_mods_subject_capes(self, obj):
        """
        Áreas temáticas CAPES

        JUSTIFICATIVA:
        Taxonomia oficial brasileira para avaliação de programas de pós-graduação:
        - Classificação de periódicos no Qualis CAPES
        - Avaliação de produção científica de programas
        - Estatísticas nacionais de pesquisa
        - Compliance com políticas de fomento nacionais (CNPq, FAPESP)

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <subject><topic authority="capes-thematic-area">

        FONTE DE DADOS:
        - Journal.thematic_area (hierarquia: level2 > level1 > level0)

        EXEMPLO XML (MODS):
        <subject>
            <topic authority="capes-thematic-area">Medicina II</topic>
        </subject>
        <subject>
            <topic authority="capes-thematic-area">Saúde Coletiva</topic>
        </subject>

        REFERÊNCIA OFICIAL:
        - subject: https://www.loc.gov/standards/mods/userguide/subject.html
        - CAPES Áreas: https://www.gov.br/capes/pt-br/acesso-a-informacao/acoes-e-programas/avaliacao/sobre-a-avaliacao/areas-avaliacao

        Returns:
            list: Lista de áreas CAPES (nível mais específico disponível)
            Exemplo: ["Medicina II", "Enfermagem", "Saúde Coletiva"]
        """
        capes_areas = []

        # Padronizado: .exists() direto no related manager (sem .all() redundante)
        if obj.journal and hasattr(obj.journal, 'thematic_area') and obj.journal.thematic_area.exists():
            for thematic_area_journal in obj.journal.thematic_area.all():
                thematic_area = thematic_area_journal.thematic_area

                # Usar hierarquia: level2 > level1 > level0
                topic_text = None
                if thematic_area.level2:
                    topic_text = thematic_area.level2
                elif thematic_area.level1:
                    topic_text = thematic_area.level1
                elif thematic_area.level0:
                    topic_text = thematic_area.level0

                if topic_text and topic_text.strip():
                    capes_areas.append(topic_text.strip())

        return capes_areas

    def prepare_mods_relateditem_host_title(self, obj):
        """
        Título do periódico pai

        JUSTIFICATIVA:
        Essencial para citação bibliográfica adequada:
        - Identifica o periódico que publicou o artigo
        - Permite busca por periódico específico
        - Necessário para geração automática de citações
        Dublin Core não tem estrutura para relacionamento host/part.

        MAPEAMENTO:
        Sem equivalente direto → MODS <relatedItem type="host"><titleInfo><title>

        FONTE DE DADOS:
        - Article.journal.title

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <relatedItem type="host">
            <titleInfo>
                <title>International Journal of Urban and Regional Research</title>
            </titleInfo>
            <originInfo>
                <issuance>continuing</issuance>
            </originInfo>
        </relatedItem>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - relatedItem: https://www.loc.gov/standards/mods/userguide/relateditem.html

        Returns:
            str: Título do periódico
            Exemplo: "Revista Brasileira de Medicina"
        """
        if obj.journal and obj.journal.title:
            return obj.journal.title.strip()
        return None

    def prepare_mods_relateditem_host_issn(self, obj):
        """
        ISSNs do periódico (todos os tipos)

        JUSTIFICATIVA:
        Identificadores persistentes do periódico:
        - ISSN impresso: versão física histórica
        - ISSN eletrônico: versão online (mais comum)
        - ISSN-L: linking ISSN (agrupa todas as versões)
        Essenciais para citação, linkagem e descoberta de recursos.

        MAPEAMENTO:
        Sem equivalente direto → MODS <relatedItem type="host"><identifier type="issn">

        FONTE DE DADOS:
        - Journal.official.issn_print
        - Journal.official.issn_electronic
        - Journal.official.issnl

        EXEMPLO XML (MODS):
        <relatedItem type="host">
            <identifier type="issn">0363-9061</identifier>
            <identifier type="issn">1468-2427</identifier>
        </relatedItem>

        REFERÊNCIA OFICIAL:
        - identifier: https://www.loc.gov/standards/mods/userguide/identifier.html
        - ISSN: https://www.issn.org/

        Returns:
            list: Lista de ISSNs
            Exemplo: ["1234-5678", "8765-4321", "1111-2222"]
        """
        issns = []

        if obj.journal and obj.journal.official:
            official = obj.journal.official

            if official.issn_print and official.issn_print not in issns:
                issns.append(official.issn_print)

            if official.issn_electronic and official.electronic not in issns:
                issns.append(official.issn_electronic)

            if official.issnl and official.issnl not in issns:
                issns.append(official.issnl)

        return issns

    def prepare_mods_relateditem_host_volume(self, obj):
        """
        Volume do fascículo

        JUSTIFICATIVA:
        Elemento obrigatório para citação bibliográfica:
        - Identifica ano de publicação (tipicamente volume = ano)
        - Necessário para localização precisa do artigo
        - Usado em todas as normas de citação (ABNT, APA, Vancouver)

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <relatedItem><part><detail type="volume">

        FONTE DE DADOS:
        - Article.issue.volume

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <relatedItem type="host">
            <part>
                <detail type="volume">
                    <number>24</number>
                </detail>
            </part>
        </relatedItem>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - part: https://www.loc.gov/standards/mods/userguide/part.html

        Returns:
            str: Volume do fascículo
            Exemplo: "37"
        """
        if obj.issue and obj.issue.volume:
            return str(obj.issue.volume).strip()
        return None

    def prepare_mods_relateditem_host_issue(self, obj):
        """
        Número do fascículo

        JUSTIFICATIVA:
        Elemento para citação bibliográfica:
        - Identifica fascículo específico dentro do volume
        - Necessário para localização precisa do artigo
        - Tipicamente: número sequencial dentro do ano/volume

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <relatedItem><part><detail type="issue">

        FONTE DE DADOS:
        - Article.issue.number

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <relatedItem type="host">
            <part>
                <detail type="issue">
                    <number>2</number>
                    <caption>no.</caption>
                </detail>
            </part>
        </relatedItem>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - part: https://www.loc.gov/standards/mods/userguide/part.html

        Returns:
            str: Número do fascículo
            Exemplo: "7"
        """
        if obj.issue and obj.issue.number:
            return str(obj.issue.number).strip()
        return None

    def prepare_mods_relateditem_host_supplement(self, obj):
        """
        Suplemento do fascículo

        JUSTIFICATIVA:
        Identifica fascículos especiais:
        - Suplementos temáticos
        - Números especiais dedicados
        - Anais de congressos publicados como suplemento
        Necessário para citação bibliográfica completa.

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <relatedItem><part><detail type="supplement">

        FONTE DE DADOS:
        - Article.issue.supplement

        EXEMPLO XML (MODS):
        <relatedItem type="host">
            <part>
                <detail type="supplement">
                    <number>suppl.1</number>
                </detail>
            </part>
        </relatedItem>

        REFERÊNCIA OFICIAL:
        - part: https://www.loc.gov/standards/mods/userguide/part.html

        Returns:
            str: Designação do suplemento ou None
            Exemplo: "suppl.1"
        """
        if obj.issue and obj.issue.supplement:
            return str(obj.issue.supplement).strip()
        return None

    def prepare_mods_part_page_start(self, obj):
        """
        Página inicial do artigo

        JUSTIFICATIVA:
        Elemento obrigatório para citação bibliográfica tradicional:
        - Localização física do artigo no fascículo impresso
        - Necessário em normas ABNT, APA, Vancouver
        - Para artigos eletrônicos sem páginação, usar elocation-id

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <part><extent unit="pages"><start>

        FONTE DE DADOS:
        - Article.first_page

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <part>
            <extent unit="pages">
                <start>361</start>
                <end>378</end>
            </extent>
        </part>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - part/extent: https://www.loc.gov/standards/mods/userguide/part.html#extent

        Returns:
            str: Número da página inicial
            Exemplo: "123"
        """
        if obj.first_page:
            return str(obj.first_page).strip()
        return None

    def prepare_mods_part_page_end(self, obj):
        """
        Página final do artigo

        JUSTIFICATIVA:
        Completa a informação de paginação:
        - Permite calcular extensão do artigo
        - Necessário para citação completa
        - Usado em métricas de produtividade (páginas publicadas)

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <part><extent unit="pages"><end>

        FONTE DE DADOS:
        - Article.last_page

        EXEMPLO XML (MODS 3.5 - Journal Article):
        <part>
            <extent unit="pages">
                <start>361</start>
                <end>378</end>
            </extent>
        </part>

        Fonte: https://www.loc.gov/standards/mods/v3/modsjournal.xml

        REFERÊNCIA OFICIAL:
        - part/extent: https://www.loc.gov/standards/mods/userguide/part.html#extent

        Returns:
            str: Número da página final
            Exemplo: "145"
        """
        if obj.last_page:
            return str(obj.last_page).strip()
        return None

    def prepare_mods_part_elocation(self, obj):
        """
        elocation-id (para artigos sem paginação tradicional)

        JUSTIFICATIVA:
        Identificador para artigos eletrônicos publicados sem páginas:
        - Artigos em periódicos 100% eletrônicos (born-digital)
        - Publicação contínua (continuous publishing)
        - Substitui paginação tradicional mantendo localização única
        - Padrão crescente em periódicos científicos modernos

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <part><detail type="elocation-id">

        FONTE DE DADOS:
        - Article.elocation_id (apenas se não houver first_page)

        EXEMPLO XML (MODS):
        <part>
            <detail type="elocation-id">
                <number>e370704</number>
            </detail>
        </part>

        REFERÊNCIA OFICIAL:
        - part/detail: https://www.loc.gov/standards/mods/userguide/part.html#detail
        - elocation-id: https://jats.nlm.nih.gov/publishing/tag-library/1.3/element/elocation-id.html

        Returns:
            str: elocation-id ou None (se houver paginação tradicional)
            Exemplo: "e370704"
        """
        # Só retorna elocation se NÃO houver paginação tradicional válida
        # Verifica se first_page está vazio ou é só whitespace
        has_pagination = obj.first_page and str(obj.first_page).strip()

        if not has_pagination and obj.elocation_id:
            elocation = str(obj.elocation_id).strip()
            return elocation if elocation else None

        return None

    def prepare_mods_identifier_issn_print(self, obj):
        """
        ISSN da versão impressa

        JUSTIFICATIVA:
        Identificador persistente da versão física do periódico:
        - ISSN histórico (muitos periódicos nasceram impressos)
        - Usado em indexação retrospectiva
        - Necessário para vinculação com acervos físicos
        - Importante para periódicos híbridos (impresso + online)

        MAPEAMENTO:
        Dublin Core dc.identifier → MODS <identifier type="issn" displayLabel="Print ISSN">

        FONTE DE DADOS:
        - Journal.official.issn_print

        EXEMPLO XML (MODS):
        <identifier type="issn" displayLabel="Print ISSN">0363-9061</identifier>

        REFERÊNCIA OFICIAL:
        - identifier: https://www.loc.gov/standards/mods/userguide/identifier.html
        - ISSN: https://www.issn.org/understanding-the-issn/what-is-an-issn/

        Returns:
            str: ISSN impresso no formato ####-####
            Exemplo: "1234-5678"
        """
        if obj.journal and obj.journal.official and obj.journal.official.issn_print:
            return obj.journal.official.issn_print
        return None

    def prepare_mods_identifier_issn_electronic(self, obj):
        """
        ISSN da versão eletrônica

        JUSTIFICATIVA:
        Identificador persistente da versão online do periódico:
        - ISSN específico para versão digital
        - Principal identificador para periódicos eletrônicos
        - Usado em bases de dados internacionais (WoS, Scopus)
        - Diferente do ISSN impresso (mesmo periódico, mídias distintas)

        MAPEAMENTO:
        Dublin Core dc.identifier → MODS <identifier type="issn" displayLabel="Electronic ISSN">

        FONTE DE DADOS:
        - Journal.official.issn_electronic

        EXEMPLO XML (MODS):
        <identifier type="issn" displayLabel="Electronic ISSN">1468-2427</identifier>

        REFERÊNCIA OFICIAL:
        - identifier: https://www.loc.gov/standards/mods/userguide/identifier.html
        - ISSN-e: https://www.issn.org/understanding-the-issn/assignment-rules/the-issn-for-electronic-media/

        Returns:
            str: ISSN eletrônico no formato ####-####
            Exemplo: "8765-4321"
        """
        if obj.journal and obj.journal.official and obj.journal.official.issn_electronic:
            return obj.journal.official.issn_electronic
        return None

    def prepare_mods_identifier_issnl(self, obj):
        """
        ISSN-L (linking ISSN)

        JUSTIFICATIVA:
        ISSN de ligação que agrupa todas as versões de um periódico:
        - Vincula ISSN impresso, eletrônico, e outras versões
        - Facilita identificação inequívoca do periódico
        - Usado para agregação de métricas (todas as versões)
        - Padrão ISO 3297:2007 para identificação de publicações seriadas

        MAPEAMENTO:
        Dublin Core dc.identifier → MODS <identifier type="issnl">

        FONTE DE DADOS:
        - Journal.official.issnl

        EXEMPLO XML (MODS):
        <identifier type="issnl">1111-2222</identifier>

        REFERÊNCIA OFICIAL:
        - identifier: https://www.loc.gov/standards/mods/userguide/identifier.html
        - ISSN-L: https://www.issn.org/understanding-the-issn/assignment-rules/the-issn-l-for-publications-on-multiple-media/

        Returns:
            str: ISSN-L no formato ####-####
            Exemplo: "1111-2222"
        """
        if obj.journal and obj.journal.official and obj.journal.official.issnl:
            return obj.journal.official.issnl
        return None

    def prepare_mods_origininfo_publisher(self, obj):
        """
        Editora(s) do periódico

        JUSTIFICATIVA:
        Identifica responsável pela publicação:
        - Nome oficial da editora
        - Importante para avaliação de credibilidade
        - Necessário para citação bibliográfica completa
        - Usado em análises de concentração editorial
        Dublin Core dc.publisher tem limitações de estruturação.

        MAPEAMENTO:
        Dublin Core dc.publisher → MODS <originInfo><publisher>

        FONTE DE DADOS:
        - Journal.publisher_history.organization.name (prioridade)
        - Journal.publisher_history.institution (fallback legado)

        EXEMPLO XML (MODS):
        <originInfo>
            <publisher>Sociedade Brasileira de Medicina (SBM)</publisher>
        </originInfo>

        REFERÊNCIA OFICIAL:
        - originInfo: https://www.loc.gov/standards/mods/userguide/origininfo.html
        - publisher: https://www.loc.gov/standards/mods/userguide/origininfo.html#publisher

        Returns:
            list: Lista de editoras com acrônimos
            Exemplo: ["Sociedade Brasileira de Medicina (SBM)", "Editora FIOCRUZ"]
        """
        publishers = []

        # Early return se não houver histórico de publishers
        has_publisher_history = (
            obj.journal and
            hasattr(obj.journal, 'publisher_history') and
            obj.journal.publisher_history.exists()
        )

        if not has_publisher_history:
            return publishers

        for pub_history in obj.journal.publisher_history.select_related(
            'institution__institution__institution_identification',
            'organization'
        ):
            pub_name = None

            # Tentar nova estrutura Organization primeiro
            if pub_history.organization:
                name, acronym = self._get_organization_name_and_acronym(pub_history.organization)
                if name:
                    pub_name = self._format_name_with_acronym(name, acronym)

            # Fallback para estrutura Institution legada
            if not pub_name:
                name, acronym = self._get_legacy_institution_name_and_acronym(pub_history)
                if name:
                    pub_name = self._format_name_with_acronym(name, acronym)

            # Check defensivo: garantir que pub_name está stripped e não é duplicado
            if pub_name:
                pub_name = pub_name.strip()
                if pub_name and pub_name not in publishers:
                    publishers.append(pub_name)

        return publishers

    def prepare_mods_origininfo_place(self, obj):
        """
        Lugar(es) de publicação

        JUSTIFICATIVA:
        Localização geográfica da publicação:
        - Cidade, estado, país da editora
        - Usado para análises regionais de produção científica
        - Elemento tradicional de catalogação bibliográfica
        - Importante para contexto histórico de publicações antigas

        MAPEAMENTO:
        Dublin Core dc.coverage → MODS <originInfo><place><placeTerm>

        FONTE DE DADOS:
        - Journal.contact_location (prioridade alta)
        - Journal.publisher_history.organization.location (fallback)

        EXEMPLO XML (MODS):
        <originInfo>
            <place>
                <placeTerm type="text">São Paulo, SP, Brasil</placeTerm>
            </place>
        </originInfo>

        REFERÊNCIA OFICIAL:
        - originInfo/place: https://www.loc.gov/standards/mods/userguide/origininfo.html#place

        Returns:
            list: Lista de localizações formatadas
            Exemplo: ["São Paulo, SP, Brasil", "Rio de Janeiro, RJ, Brasil"]
        """
        places = []

        if not obj.journal:
            return places

        # Fonte 1: contact_location do Journal (prioridade alta)
        has_contact_location = (
            hasattr(obj.journal, 'contact_location') and
            obj.journal.contact_location
        )

        if has_contact_location:
            place_text = self._format_place_location(obj.journal.contact_location)
            if place_text:
                places.append(place_text)

        # Fonte 2: Location via Publisher Organizations (se não há contact_location)
        has_publisher_history = (
            not places and
            hasattr(obj.journal, 'publisher_history') and
            obj.journal.publisher_history.exists()
        )

        if has_publisher_history:
            for pub_history in obj.journal.publisher_history.select_related(
                'organization__location__city',
                'organization__location__state',
                'organization__location__country'
            ):
                if pub_history.organization and pub_history.organization.location:
                    place_text = self._format_place_location(pub_history.organization.location)
                    if place_text and place_text not in places:
                        places.append(place_text)

        return places

    def prepare_mods_origininfo_date(self, obj):
        """
        Data de publicação estruturada (w3cdtf)

        JUSTIFICATIVA:
        Data estruturada em formato ISO 8601/W3CDTF:
        - Permite ordenação cronológica precisa
        - Facilita filtros por período (2020-2025)
        - Formato padrão para intercâmbio internacional
        - Suporta granularidade variável (ano, ano-mês, ano-mês-dia)
        Dublin Core dc.date aceita texto livre (menos estruturado).

        MAPEAMENTO:
        Dublin Core dc.date → MODS <originInfo><dateIssued encoding="w3cdtf">

        FONTE DE DADOS:
        - Article.pub_date_year, pub_date_month, pub_date_day

        EXEMPLO XML (MODS):
        <originInfo>
            <dateIssued encoding="w3cdtf" keyDate="yes">2000</dateIssued>
        </originInfo>

        REFERÊNCIA OFICIAL:
        - dateIssued: https://www.loc.gov/standards/mods/userguide/origininfo.html#dateissued
        - W3CDTF: https://www.w3.org/TR/NOTE-datetime

        Returns:
            str: Data no formato YYYY ou YYYY-MM ou YYYY-MM-DD
            Exemplo: "2023-06-15"
        """
        if not (hasattr(obj, 'pub_date_year') and obj.pub_date_year and
                str(obj.pub_date_year).strip()):
            return None

        date_parts = [str(obj.pub_date_year)]

        # Validar e adicionar mês
        if (hasattr(obj, 'pub_date_month') and obj.pub_date_month and
            str(obj.pub_date_month).strip()):
            try:
                month_int = int(obj.pub_date_month)
                if 1 <= month_int <= 12:
                    date_parts.append(f"{month_int:02d}")

                    # Validar e adicionar dia apenas se mês for válido
                    if (hasattr(obj, 'pub_date_day') and obj.pub_date_day and
                        str(obj.pub_date_day).strip()):
                        try:
                            day_int = int(obj.pub_date_day)
                            if 1 <= day_int <= 31:
                                date_parts.append(f"{day_int:02d}")
                        except (ValueError, TypeError):
                            # Ignora dia inválido, mantém apenas ano-mês
                            pass
            except (ValueError, TypeError):
                # Ignora mês inválido, mantém apenas ano
                pass

        return "-".join(date_parts)

    def prepare_mods_accesscondition_license(self, obj):
        """
        Tipo de licença do artigo

        JUSTIFICATIVA:
        Especifica direitos de uso e reutilização:
        - Creative Commons (BY, BY-NC, BY-SA, etc.)
        - Licenças proprietárias
        - Essencial para compliance com mandatos de Open Access
        - Determina legalidade de text mining e reuso
        Dublin Core dc.rights tem texto livre (menos estruturado).

        MAPEAMENTO:
        Dublin Core dc.rights → MODS <accessCondition type="use and reproduction">

        FONTE DE DADOS:
        - Article.license.license_type (prioridade)
        - Journal.journal_use_license.license_type (fallback)
        - Journal.use_license.license_type (fallback secundário)

        EXEMPLO XML (MODS):
        <accessCondition type="use and reproduction"
                         authority="creativecommons"
                         authorityURI="https://creativecommons.org/">
            Creative Commons BY 4.0
        </accessCondition>

        REFERÊNCIA OFICIAL:
        - accessCondition: https://www.loc.gov/standards/mods/userguide/accesscondition.html
        - Creative Commons: https://creativecommons.org/licenses/

        Returns:
            str: Tipo de licença
            Exemplo: "Creative Commons BY 4.0"
        """
        # Fonte 1: Licença do artigo
        if obj.license and obj.license.license_type:
            return obj.license.license_type.strip()

        # Fonte 2: Licença do journal
        if obj.journal:
            if (obj.journal.journal_use_license and
                obj.journal.journal_use_license.license_type):
                return obj.journal.journal_use_license.license_type.strip()

            if (obj.journal.use_license and
                obj.journal.use_license.license_type):
                return obj.journal.use_license.license_type.strip()

        return None

    def prepare_mods_accesscondition_licenseurl(self, obj):
        """
        URL da licença Creative Commons

        JUSTIFICATIVA:
        Link direto para texto legal da licença:
        - Permite verificação automática de termos
        - URL canônica da licença CC
        - Facilita compliance check de políticas OA
        - Usado por harvesters para validação de direitos

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <accessCondition xlink:href="...">

        FONTE DE DADOS:
        - LicenseStatement.url (se disponível via relacionamento)

        EXEMPLO XML (MODS):
        <accessCondition type="use and reproduction"
                         xlink:href="https://creativecommons.org/licenses/by/4.0/">
            Creative Commons BY 4.0
        </accessCondition>

        REFERÊNCIA OFICIAL:
        - accessCondition: https://www.loc.gov/standards/mods/userguide/accesscondition.html
        - XLink: https://www.w3.org/TR/xlink11/

        Returns:
            str: URL da licença ou None
            Exemplo: "https://creativecommons.org/licenses/by/4.0/"
        """
        # Tentar extrair URL de license_statements (se relacionamento existir)
        if hasattr(obj, 'license_statements') and obj.license_statements.exists():
            # Coletar todas as URLs válidas
            valid_urls = [
                statement.url.strip()
                for statement in obj.license_statements.all()
                if statement.url and statement.url.strip()
            ]

            if valid_urls:
                # Retornar a primeira URL válida encontrada
                # Nota: Normalmente há apenas 1 LicenseStatement por artigo.
                # Se houver múltiplos, considerar adicionar ordenação por
                # campo de prioridade ou data se disponível no modelo.
                return valid_urls[0]

        # Se não tiver URL explícita, retornar None
        # (não vamos construir URLs artificiais)
        return None

    def prepare_mods_accesscondition_openaccess(self, obj):
        """
        Política de Open Access do periódico

        JUSTIFICATIVA:
        Classifica modelo de acesso aberto segundo taxonomia SHERPA/RoMEO:
        - diamond: OA sem APC (autor ou leitor)
        - gold: OA com APC (author pays)
        - hybrid: Periódico de assinatura com opção OA
        - bronze: Acesso livre sem licença clara
        - green: Auto-arquivamento permitido
        - closed: Acesso restrito por assinatura
        Essencial para análises de compliance com políticas de fomento.

        MAPEAMENTO:
        Sem equivalente em Dublin Core → MODS <accessCondition type="restriction on access">

        FONTE DE DADOS:
        - Journal.open_access (valores do choices.OA_STATUS)

        EXEMPLO XML (MODS):
        <accessCondition type="restriction on access"
                         authority="scielo-oa-model">
            gold
        </accessCondition>

        REFERÊNCIA OFICIAL:
        - accessCondition: https://www.loc.gov/standards/mods/userguide/accesscondition.html
        - SHERPA/RoMEO: https://v2.sherpa.ac.uk/romeo/

        Returns:
            str: Tipo de OA (diamond/gold/hybrid/bronze/green/closed)
            Exemplo: "gold"
        """
        if obj.journal and obj.journal.open_access:
            return obj.journal.open_access.strip()
        return None

    # métodos auxiliares privados
    def _format_location_parts(self, location, separator=", "):
        """
        Formata partes de localização com separador customizável

        Args:
            location: objeto Location
            separator: string separadora (default: ", ")

        Returns:
            str: Localização formatada ou None
            Exemplos:
                separator=", " → "São Paulo, SP, Brasil"
                separator=" - " → "São Paulo - SP - Brasil"
        """
        if not location:
            return None

        parts = []

        try:
            # Cidade
            if location.city and location.city.name:
                parts.append(location.city.name.strip())

            # Estado (preferir sigla se disponível)
            if location.state:
                state_text = location.state.acronym or location.state.name
                if state_text:
                    parts.append(state_text.strip())

            # País
            if location.country and location.country.name:
                parts.append(location.country.name.strip())

        except (AttributeError, TypeError):
            return None

        return separator.join(parts) if parts else None

    def _format_affiliation(self, affiliation):
        """
        Formata afiliação em string hierárquica

        Args:
            affiliation: objeto Affiliation

        Returns:
            str: "Instituição - Depto - Cidade - Estado - País"
        """
        if not affiliation or not affiliation.institution:
            return None

        parts = []
        institution = affiliation.institution

        try:
            # Nome da instituição
            if institution.institution_identification:
                if institution.institution_identification.name:
                    parts.append(institution.institution_identification.name.strip())

            # Níveis organizacionais (departamentos, divisões)
            for level in [institution.level_1, institution.level_2, institution.level_3]:
                if level and level.strip():
                    parts.append(level.strip())

            # Localização geográfica (reutiliza método helper)
            if institution.location:
                location_str = self._format_location_parts(institution.location, separator=" - ")
                if location_str:
                    parts.append(location_str)

        except (AttributeError, TypeError):
            # Fallback para string simples
            return str(affiliation) if affiliation else None

        return " - ".join(parts) if parts else None

    def _format_place_location(self, location):
        """
        Formata localização em string: "Cidade, Estado, País"

        Args:
            location: objeto Location

        Returns:
            str: "São Paulo, SP, Brasil"
        """
        return self._format_location_parts(location, separator=", ")

    def _format_name_with_acronym(self, name, acronym):
        """
        Formata nome com acrônimo entre parênteses

        Args:
            name: Nome principal (ex: "Universidade de São Paulo")
            acronym: Acrônimo (ex: "USP")

        Returns:
            str: Nome formatado (ex: "Universidade de São Paulo (USP)")
                 ou None se name for vazio
        """
        if not name:
            return None

        result = name.strip()
        if acronym and acronym.strip():
            result += f" ({acronym.strip()})"

        return result

    def _get_organization_name_and_acronym(self, organization):
        """
        Extrai nome e acrônimo de Organization

        Args:
            organization: objeto Organization

        Returns:
            tuple: (name, acronym) ou (None, None)
        """
        if not organization:
            return None, None

        name = organization.name.strip() if organization.name else None
        acronym = organization.acronym.strip() if organization.acronym else None

        return name, acronym

    def _get_legacy_institution_name_and_acronym(self, pub_history):
        """
        Extrai nome e acrônimo de estrutura Institution legada

        Args:
            pub_history: objeto PublisherHistory

        Returns:
            tuple: (name, acronym) ou (None, None)
        """
        if not (pub_history.institution and
                pub_history.institution.institution and
                pub_history.institution.institution.institution_identification):
            return None, None

        inst_id = pub_history.institution.institution.institution_identification
        name = inst_id.name.strip() if inst_id.name else None
        acronym = inst_id.acronym.strip() if inst_id.acronym else None

        return name, acronym

    def get_model(self):
        return Article

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_classic_public=True)

