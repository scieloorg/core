import re
import uuid
from collections import defaultdict

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from wagtail.documents.models import Document
from wagtail.models import Page, Locale, Site

from core.home.models import AboutScieloOrgPage, HomePage
from core.utils.extract_wordpress_items import extract_items


class Command(BaseCommand):
    help = "Importa conteúdo multilíngue do WordPress XML para Wagtail com suporte a attachments"

    # MODIFICAÇÃO: Slugs específicos por idioma
    LANGUAGES = {
        "pt-br": {
            "home_title": "Página Inicial",
            "about_title": "Sobre o SciELO",
            "about_slug": "sobre-o-scielo"
        },
        "en": {
            "home_title": "Home Page",
            "about_title": "About SciELO",
            "about_slug": "about-scielo"
        },
        "es": {
            "home_title": "Página Principal",
            "about_title": "Sobre el SciELO",
            "about_slug": "sobre-el-scielo"
        },
    }

    SOURCE_LOCALE = "pt-br"
    DOCUMENT_TEMPLATES = ["pageModel-linkToDocument.php"]
    EXTERNAL_LINK_TEMPLATES = ["pageModel-linkExternal.php"]
    ABOUT_KEYWORDS = ["about", "sobre", "scielo"]

    def add_arguments(self, parser):
        parser.add_argument("xml_path", type=str, help="Caminho para o arquivo XML")
        parser.add_argument("--clean", action="store_true", help="Limpar páginas existentes")
        parser.add_argument("--about-parent-id", type=str, default=None,
                            help="ID da página parent das páginas About")

    def handle(self, *args, **options):
        if options.get("clean"):
            self.clean_pages()

        self.setup_locales()
        pages_data = self.parse_xml(options["xml_path"])
        about_parent_id = options.get("about_parent_id") or self.detect_about_parent(pages_data)

        if not about_parent_id:
            self.stdout.write(self.style.ERROR("Parent ID das páginas About não encontrado"))
            return

        self.stdout.write(f"Parent ID detectado: {about_parent_id}")
        self.create_structure(pages_data, about_parent_id)
        self.stdout.write(self.style.SUCCESS("Importação concluída!"))

    def setup_locales(self):
        """Configura locales necessários"""
        for lang_code in self.LANGUAGES.keys():
            locale, created = Locale.objects.get_or_create(language_code=lang_code)
            if created:
                self.stdout.write(f"Locale criado: {lang_code}")

    def clean_pages(self):
        """Remove páginas existentes de forma simplificada"""
        self.stdout.write("Limpando páginas...")

        # Remove AboutScieloOrgPage
        count = AboutScieloOrgPage.objects.count()
        AboutScieloOrgPage.objects.all().delete()
        self.stdout.write(f"Removidas {count} páginas About")

        # Remove HomePage que não são root de sites
        site_roots = set(Site.objects.values_list("root_page_id", flat=True))
        home_pages = HomePage.objects.exclude(id__in=site_roots)
        count = home_pages.count()
        home_pages.delete()
        self.stdout.write(f"Removidas {count} HomePage")

        # Remove HomePage filhas do root_page
        for site in Site.objects.all():
            children = HomePage.objects.filter(
                path__startswith=site.root_page.path
            ).exclude(id=site.root_page.id)
            count = children.count()
            if count > 0:
                children.delete()
                self.stdout.write(f"Removidas {count} HomePage filhas")

        # Limpar traduções órfãs
        self._clean_translations()
        Page.fix_tree(destructive=True)

    def _clean_translations(self):
        """Helper para limpar traduções órfãs"""
        try:
            from wagtail_localize.models import Translation, TranslationSource
            Translation.objects.all().delete()
            TranslationSource.objects.all().delete()
            self.stdout.write("Traduções órfãs removidas")
        except ImportError:
            self.stdout.write("wagtail_localize não instalado")

    def parse_xml(self, xml_path):
        """Parse do XML e organização dos dados"""
        self.stdout.write(f"Processando XML: {xml_path}")
        items = extract_items(xml_path)
        pages = [item for item in items if item["post_type"] == "page" and item["status"] == "publish"]

        self.stdout.write(f"Páginas válidas encontradas: {len(pages)}")

        pages_by_id = {}
        for page in pages:
            processed = self.process_page(page)
            if processed:
                pages_by_id[str(page["post_id"])] = {
                    "wp_data": page,
                    "processed": processed,
                }

        self.stdout.write(f"Páginas processadas: {len(pages_by_id)}")
        return pages_by_id

    def detect_about_parent(self, pages_data):
        """Detecta parent ID das páginas About com fallback"""
        self.stdout.write("Detectando parent das páginas About...")

        # Primeira tentativa: procurar parent com filhas que contenham palavras-chave
        for post_id, page_info in pages_data.items():
            wp_data = page_info["wp_data"]

            if wp_data["parent_id"] == 0:  # É uma página root
                children_count = sum(1 for pid, pinfo in pages_data.items()
                                     if pinfo["wp_data"]["parent_id"] == wp_data["post_id"])

                if children_count > 0:
                    # Verificar se alguma filha tem palavras-chave relacionadas a "about"
                    for pid, pinfo in pages_data.items():
                        if pinfo["wp_data"]["parent_id"] == wp_data["post_id"]:
                            source_data = pinfo["processed"].get(self.SOURCE_LOCALE, {})
                            title = source_data.get("title", "").lower()
                            if any(word in title for word in self.ABOUT_KEYWORDS):
                                self.stdout.write(f"Detectado parent About: {post_id} (filha: {title})")
                                return post_id

        # Fallback: parent com mais filhas
        parent_counts = defaultdict(int)
        for page_info in pages_data.values():
            parent_id = page_info["wp_data"]["parent_id"]
            if parent_id and parent_id != 0:
                parent_counts[str(parent_id)] += 1

        if parent_counts:
            most_common = max(parent_counts.items(), key=lambda x: x[1])
            self.stdout.write(f"Usando parent com mais filhas: {most_common[0]} ({most_common[1]} filhas)")
            return most_common[0]

        return None

    def process_page(self, page_item):
        """Processa página do XML para estrutura multilíngue"""
        result = {}

        for lang_code in self.LANGUAGES.keys():
            title = page_item["title_i18n"].get(lang_code, "")
            content = page_item["content_i18n"].get(lang_code, "")
            slug = page_item["slug_i18n"].get(lang_code, page_item["slug"] or "")

            if not title:
                continue

            # Processar links e documentos com URLs reais
            page_template = page_item.get("page_template", "default")
            external_link = page_item["external_link_i18n"].get(lang_code, "") or ""
            document_url = page_item["document_i18n"].get(lang_code, "") or ""

            content_type, final_url = self.process_links(page_template, external_link, document_url)

            # Usar slug específico do idioma ou fallback
            if not slug:
                slug = self.clean_slug(title)

            result[lang_code] = {
                "post_id": str(page_item["post_id"]),
                "parent_id": str(page_item["parent_id"] or 0),
                "title": title,
                "slug": slug,
                "body": content,
                "external_link": final_url if content_type == "external_link" else "",
                "document_url": final_url if content_type == "document" else "",
                "content_type": content_type,
                "menu_order": page_item["menu_order"] or 0,
                "page_template": page_template,
            }

        return result

    def process_links(self, page_template, external_link, document_url):
        """Processa links baseado no template"""
        # Documento
        if page_template in self.DOCUMENT_TEMPLATES:
            if self._is_valid_url(document_url):
                return "document", document_url
            elif self._is_valid_url(external_link):
                return "document", external_link
            else:
                return "html_content", ""

        # Link externo
        elif page_template in self.EXTERNAL_LINK_TEMPLATES and self._is_valid_url(external_link):
            return "external_link", external_link

        # HTML padrão
        else:
            return "html_content", ""

    def _is_valid_url(self, url):
        """Valida se URL é válida"""
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        return url.startswith(("http://", "https://")) and "." in url

    def clean_slug(self, title):
        """Gera slug válido"""
        if not title:
            return "untitled-page"

        slug = slugify(title)
        if not slug:
            return "page"

        # Validação Wagtail
        slug = re.sub(r"[^a-z0-9\-_]", "-", slug.lower())
        slug = re.sub(r"-+", "-", slug).strip("-")

        return slug[:255] if slug else "page"

    def create_structure(self, pages_data, about_parent_id):
        """Cria estrutura multilíngue principal"""
        site = Site.objects.get(is_default_site=True)
        source_locale = Locale.objects.get(language_code=self.SOURCE_LOCALE)
        root_page = site.root_page

        if not hasattr(root_page, "locale") or root_page.locale != source_locale:
            self.stdout.write(f"Configurando root_page para locale {self.SOURCE_LOCALE}")
            root_page.locale = source_locale
            root_page.save()

        # Criar páginas About para cada idioma
        self.stdout.write("=== Criando páginas About ===")
        about_pages = self.create_about_pages(root_page)

        # Validar criação das páginas About
        if not self._validate_about_pages(about_pages):
            return

        # Criar páginas filhas
        self.stdout.write(f"\n=== Criando páginas filhas (parent ID: {about_parent_id}) ===")
        self.create_children_pages(about_pages, about_parent_id, pages_data)

        self.stdout.write("\n=== Estrutura criada ===")

    def _validate_about_pages(self, about_pages):
        """Valida se todas as páginas About foram criadas"""
        self.stdout.write("\n=== Status das páginas About ===")
        missing_locales = []

        for lang_code in self.LANGUAGES.keys():
            if lang_code in about_pages:
                page = about_pages[lang_code]
                self.stdout.write(f"{lang_code}: {page.title} → {page.url}")
            else:
                self.stdout.write(f"{lang_code}: NÃO ENCONTRADO")
                missing_locales.append(lang_code)

        if missing_locales:
            self.stdout.write(self.style.ERROR(f"Páginas About faltando para: {missing_locales}"))
            return False
        else:
            self.stdout.write(self.style.SUCCESS("Todas as páginas About criadas"))
            return True

    def create_about_pages(self, parent):
        """Cria páginas About para todos os idiomas"""
        about_pages = {}
        source_locale = Locale.objects.get(language_code=self.SOURCE_LOCALE)
        base_translation_key = str(uuid.uuid4())

        # Primeiro, criar página About no idioma fonte
        source_about = self.create_single_about_page(
            parent, source_locale, self.SOURCE_LOCALE, base_translation_key
        )
        if source_about:
            about_pages[self.SOURCE_LOCALE] = source_about

        # Depois, tentar criar traduções para outros idiomas
        for lang_code in self.LANGUAGES.keys():
            if lang_code == self.SOURCE_LOCALE:
                continue

            target_locale = Locale.objects.get(language_code=lang_code)

            # Tentar copy_for_translation primeiro
            if source_about:
                translated_about = self._try_copy_for_translation(
                    source_about, target_locale, lang_code
                )
                if translated_about:
                    about_pages[lang_code] = translated_about
                    continue

            # Fallback: criar página independente
            fallback_about = self.create_single_about_page(
                parent, target_locale, lang_code, base_translation_key
            )
            if fallback_about:
                about_pages[lang_code] = fallback_about

        return about_pages

    def create_single_about_page(self, parent, locale, lang_code, translation_key):
        """Cria uma única página About"""
        # MODIFICAÇÃO: Usar slug específico do idioma
        about_slug = self.LANGUAGES[lang_code]["about_slug"]

        # Verificar se já existe
        existing = AboutScieloOrgPage.objects.filter(
            locale=locale, slug=about_slug, path__startswith=parent.path
        ).first()

        if existing:
            self.stdout.write(f"About existente: {lang_code} → {existing.url}")
            return existing

        # Criar nova página About
        about_page = AboutScieloOrgPage(
            title=self.LANGUAGES[lang_code]["about_title"],
            slug=self.get_unique_slug(parent, about_slug),
            locale=locale,
            translation_key=translation_key,
        )

        return self._save_page(about_page, parent, f"About {lang_code}")

    def _try_copy_for_translation(self, source_page, target_locale, lang_code):
        """Tenta criar tradução usando copy_for_translation"""
        try:
            # Verificar se tradução já existe
            existing = source_page.get_translation(target_locale)
            if existing:
                self.stdout.write(f"Tradução About existente: {lang_code} → {existing.url}")
                return existing
        except source_page.__class__.DoesNotExist:
            pass

        try:
            translated_page = source_page.copy_for_translation(target_locale)
            translated_page.title = self.LANGUAGES[lang_code]["about_title"]
            translated_page.slug = self.LANGUAGES[lang_code]["about_slug"]  # MODIFICAÇÃO: slug específico
            translated_page.body = f"Página institucional sobre o SciELO - {lang_code.upper()}."
            translated_page.save_revision().publish()

            self.stdout.write(f"About traduzido (copy_for_translation): {lang_code} → {translated_page.url}")
            return translated_page
        except Exception as e:
            self.stdout.write(f"copy_for_translation falhou para {lang_code}: {e}")
            return None

    def get_unique_slug(self, parent, base_slug):
        """Gera slug único"""
        slug = base_slug
        counter = 1

        while parent.get_children().filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
            if counter > 100:
                break

        return slug

    def _save_page(self, page, parent, description="página"):
        """Helper para salvar página com tratamento de erro"""
        try:
            parent.add_child(instance=page)
            page.save_revision().publish()
            self.stdout.write(f"{description} criada: {page.title} → {page.url}")
            return page
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao criar {description}: {e}"))
            return None

    def create_children_pages(self, about_pages, parent_post_id, pages_data):
        """Cria páginas filhas recursivamente mantendo hierarquia e ordem"""
        children = self._get_children_data(parent_post_id, pages_data)

        if not children:
            return

        self.stdout.write(f"Processando {len(children)} páginas filhas do parent {parent_post_id}")

        for post_id, page_info in children:
            self._process_child_page(post_id, page_info, about_pages, pages_data)

    def _get_children_data(self, parent_post_id, pages_data):
        """Obtém e ordena dados das páginas filhas"""
        children = []
        for post_id, page_info in pages_data.items():
            processed = page_info["processed"]
            if self.SOURCE_LOCALE in processed:
                source_data = processed[self.SOURCE_LOCALE]
                if source_data["parent_id"] == parent_post_id:
                    children.append((post_id, page_info))

        # Ordenar por menu_order
        children.sort(key=lambda x: x[1]["processed"][self.SOURCE_LOCALE]["menu_order"])
        return children

    def _process_child_page(self, post_id, page_info, about_pages, pages_data):
        """Processa uma página filha e suas traduções"""
        processed = page_info["processed"]
        source_data = processed[self.SOURCE_LOCALE]

        if not source_data["title"]:
            self.stdout.write(f"Pulando página {post_id} sem título")
            return

        if self.SOURCE_LOCALE not in about_pages:
            self.stdout.write(f"About page não encontrada para {self.SOURCE_LOCALE}")
            return

        # Criar página no idioma fonte
        source_parent = about_pages[self.SOURCE_LOCALE]
        child_page = self.create_child_page(source_parent, source_data)

        if not child_page:
            return

        # Criar traduções
        child_translations = {self.SOURCE_LOCALE: child_page}
        self._create_child_translations(child_page, processed, about_pages, child_translations)

        # Recursão para filhas das filhas
        self.create_children_pages(child_translations, post_id, pages_data)

    def _create_child_translations(self, source_page, processed, about_pages, child_translations):
        """Cria traduções de uma página filha"""
        for lang_code in self.LANGUAGES.keys():
            if (lang_code == self.SOURCE_LOCALE or
                lang_code not in processed or
                lang_code not in about_pages):
                continue

            target_data = processed[lang_code]
            target_parent = about_pages[lang_code]

            translated_child = self.create_translated_child(
                source_page, target_parent, target_data
            )

            if translated_child:
                child_translations[lang_code] = translated_child
                self.stdout.write(f"Tradução criada: {target_data['title']} → {lang_code}")

    def create_child_page(self, parent, page_data):
        """Cria uma página filha preservando hierarquia"""
        # Verificar se página já existe
        existing = AboutScieloOrgPage.objects.filter(
            locale=parent.locale,
            slug=page_data["slug"],
            path__startswith=parent.path
        ).first()

        if existing:
            self.stdout.write(f"Página existente: {page_data['title']} → {existing.url}")
            return existing

        # Criar nova página
        page_kwargs = self.prepare_page_data(page_data)
        unique_slug = self.get_unique_slug(parent, page_data["slug"])

        child_page = AboutScieloOrgPage(
            title=page_data["title"],
            slug=unique_slug,
            locale=parent.locale,
            **page_kwargs
        )

        return self._save_page(child_page, parent, f"Página {page_data['title']}")

    def create_translated_child(self, source_page, target_parent, target_data):
        """Cria tradução de página filha"""
        # Verificar se tradução já existe
        try:
            existing = source_page.get_translation(target_parent.locale)
            if existing:
                self.stdout.write(f"Tradução existente: {target_data['title']} → {existing.url}")
                return existing
        except source_page.__class__.DoesNotExist:
            pass

        # Tentar copy_for_translation
        translated_page = self._try_child_copy_for_translation(source_page, target_parent, target_data)
        if translated_page:
            return translated_page

        # Fallback: criar página independente
        return self._create_fallback_translation(source_page, target_parent, target_data)

    def _try_child_copy_for_translation(self, source_page, target_parent, target_data):
        """Tenta criar tradução usando copy_for_translation para páginas filhas"""
        try:
            translated_page = source_page.copy_for_translation(target_parent.locale)

            # Atualizar com dados traduzidos
            translated_page.title = target_data["title"]
            translated_page.slug = self.clean_slug(target_data["slug"] or target_data["title"])

            page_kwargs = self.prepare_page_data(target_data)
            for key, value in page_kwargs.items():
                setattr(translated_page, key, value)

            translated_page.save_revision().publish()
            self.stdout.write(f"Tradução via copy_for_translation: {target_data['title']} → {translated_page.url}")
            return translated_page

        except Exception as e:
            self.stdout.write(f"copy_for_translation falhou para {target_data['title']}: {e}")
            return None

    def _create_fallback_translation(self, source_page, target_parent, target_data):
        """Cria tradução usando fallback (página independente)"""
        self.stdout.write(f"Usando fallback para {target_data['title']}")

        fallback_page = AboutScieloOrgPage(
            title=target_data["title"],
            slug=self.get_unique_slug(
                target_parent,
                self.clean_slug(target_data["slug"] or target_data["title"])
            ),
            locale=target_parent.locale,
            translation_key=source_page.translation_key,
            **self.prepare_page_data(target_data)
        )

        return self._save_page(fallback_page, target_parent, f"Tradução fallback {target_data['title']}")

    def prepare_page_data(self, page_data):
        """Prepara dados da página com processamento de documentos e links"""
        page_kwargs = {
            "body": page_data.get("body", ""),
            "external_link": "",
            "attached_document": None,
            "list_page": [],
        }

        content_type = page_data.get("content_type", "html_content")

        if content_type == "document":
            self._process_document_content(page_data, page_kwargs)
        elif content_type == "external_link":
            self._process_external_link_content(page_data, page_kwargs)

        return page_kwargs

    def _process_document_content(self, page_data, page_kwargs):
        """Processa conteúdo tipo documento"""
        document_url = page_data.get("document_url", "")
        if not document_url:
            return

        if document_url.startswith("http"):
            document = self.download_document(document_url, page_data["title"])
            if document:
                page_kwargs["attached_document"] = document
                page_kwargs["body"] = f"<p>Documento anexado: {page_data['title']}</p>"
                self.stdout.write(f"Documento anexado com sucesso: {page_data['title']}")
            else:
                # Fallback: link direto
                page_kwargs["external_link"] = document_url
                page_kwargs[
                    "body"] = f"<p>Documento: <a href='{document_url}' target='_blank'>{page_data['title']}</a></p>"
                self.stdout.write(f"Documento como link direto: {page_data['title']}")
        else:
            # ID ou formato inválido
            page_kwargs["body"] = page_data.get("body") or f"<p>Documento: {document_url}</p>"

    def _process_external_link_content(self, page_data, page_kwargs):
        """Processa conteúdo tipo link externo"""
        external_link = page_data.get("external_link", "")
        if external_link and external_link.startswith("http"):
            page_kwargs["external_link"] = external_link
            page_kwargs[
                "body"] = f"<p>Link externo: <a href='{external_link}' target='_blank'>{page_data['title']}</a></p>"
        else:
            page_kwargs["body"] = page_data.get("body", "")

    def download_document(self, document_url, title):
        """Baixa documento do URL"""
        try:
            # Verificar se já existe
            existing = Document.objects.filter(title=title).first()
            if existing:
                return existing

            response = requests.get(document_url, timeout=30)
            if response.status_code != 200:
                return None

            filename = document_url.split("/")[-1]
            if not filename or "." not in filename:
                filename = f"{self.clean_slug(title)}.pdf"

            document = Document(title=title)
            document.file.save(filename, ContentFile(response.content), save=True)
            return document

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao baixar documento {document_url}: {e}"))
            return None
