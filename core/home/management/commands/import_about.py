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

    LANGUAGES = {
        "pt-br": {"home_title": "Página Inicial", "about_title": "Sobre o SciELO"},
        "en": {"home_title": "Home Page", "about_title": "About SciELO"},
        "es": {"home_title": "Página Principal", "about_title": "Sobre el SciELO"},
    }

    SOURCE_LOCALE = "pt-br"

    def add_arguments(self, parser):
        parser.add_argument("xml_path", type=str, help="Caminho para o arquivo XML")
        parser.add_argument(
            "--clean", action="store_true", help="Limpar páginas existentes"
        )
        parser.add_argument(
            "--about-parent-id",
            type=str,
            default=None,
            help="ID da página parent das páginas About",
        )

    def handle(self, *args, **options):
        if options.get("clean"):
            self.clean_pages()

        self.setup_locales()
        pages_data = self.parse_xml(options["xml_path"])
        about_parent_id = options.get("about_parent_id") or self.detect_about_parent(
            pages_data
        )

        if not about_parent_id:
            self.stdout.write(
                self.style.ERROR("Parent ID das páginas About não encontrado")
            )
            return

        self.stdout.write(f"Parent ID detectado: {about_parent_id}")
        self.create_structure(pages_data, about_parent_id)
        self.stdout.write(self.style.SUCCESS("Importação concluída!"))

    def setup_locales(self):
        """Configura locales necessários"""
        for lang_code in self.LANGUAGES.keys():
            Locale.objects.get_or_create(language_code=lang_code)

    def clean_pages(self):
        """Remove páginas existentes de forma simplificada"""
        self.stdout.write("Limpando páginas...")

        # Remove AboutScieloOrgPage
        AboutScieloOrgPage.objects.all().delete()

        # Remove HomePage que não são root de sites
        site_roots = set(Site.objects.values_list("root_page_id", flat=True))
        HomePage.objects.exclude(id__in=site_roots).delete()

        # Remove HomePage filhas do root_page
        for site in Site.objects.all():
            HomePage.objects.filter(path__startswith=site.root_page.path).exclude(
                id=site.root_page.id
            ).delete()

        # Limpar traduções órfãs
        try:
            from wagtail_localize.models import Translation, TranslationSource

            Translation.objects.all().delete()
            TranslationSource.objects.all().delete()
        except ImportError:
            pass

        Page.fix_tree(destructive=True)

    def parse_xml(self, xml_path):
        """Parse do XML e organização dos dados"""
        items = extract_items(xml_path)
        pages = [
            item
            for item in items
            if item["post_type"] == "page" and item["status"] == "publish"
        ]

        pages_by_id = {}
        for page in pages:
            processed = self.process_page(page)
            if processed:
                pages_by_id[str(page["post_id"])] = {
                    "wp_data": page,
                    "processed": processed,
                }

        return pages_by_id

    def detect_about_parent(self, pages_data):
        """Detecta parent ID das páginas About com fallback inteligente"""
        # Primeira tentativa: procurar parent com filhas que contenham palavras-chave
        for post_id, page_info in pages_data.items():
            wp_data = page_info["wp_data"]

            if wp_data["parent_id"] == 0:  # É uma página root
                children_count = sum(
                    1
                    for pid, pinfo in pages_data.items()
                    if pinfo["wp_data"]["parent_id"] == wp_data["post_id"]
                )

                if children_count > 0:
                    # Verificar se alguma filha tem palavras-chave relacionadas a "about"
                    for pid, pinfo in pages_data.items():
                        if pinfo["wp_data"]["parent_id"] == wp_data["post_id"]:
                            source_data = pinfo["processed"].get(self.SOURCE_LOCALE, {})
                            title = source_data.get("title", "").lower()
                            if any(
                                word in title for word in ["about", "sobre", "scielo"]
                            ):
                                self.stdout.write(
                                    f"Detectado parent About: {post_id} (filha: {title})"
                                )
                                return post_id

        # Fallback: parent com mais filhas
        parent_counts = defaultdict(int)
        for page_info in pages_data.values():
            parent_id = page_info["wp_data"]["parent_id"]
            if parent_id and parent_id != 0:
                parent_counts[str(parent_id)] += 1

        if parent_counts:
            most_common = max(parent_counts.items(), key=lambda x: x[1])
            self.stdout.write(
                f"Usando parent com mais filhas: {most_common[0]} ({most_common[1]} filhas)"
            )
            return most_common[0]

        return None

    def process_page(self, page_item):
        """Processa página do XML para estrutura multilíngue"""
        result = {}

        for lang_code in self.LANGUAGES.keys():
            title = page_item["title_i18n"].get(lang_code, "")
            content = page_item["content_i18n"].get(
                lang_code, ""
            )  # Apenas content:encoded
            slug = page_item["slug_i18n"].get(lang_code, page_item["slug"] or "")

            if not title:
                continue

            # Processar links e documentos com URLs reais
            page_template = page_item.get("page_template", "default")
            external_link = page_item["external_link_i18n"].get(lang_code, "") or ""
            document_url = (
                page_item["document_i18n"].get(lang_code, "") or ""
            )

            content_type, final_url = self.process_links(
                page_template, external_link, document_url
            )

            # Usar slug específico do idioma ou fallback
            if not slug:
                slug = self.clean_slug(title)

            result[lang_code] = {
                "post_id": str(page_item["post_id"]),
                "parent_id": str(page_item["parent_id"] or 0),
                "title": title,
                "slug": slug,
                "body": content,  # Apenas content:encoded, sem enriquecimento
                "external_link": final_url if content_type == "external_link" else "",
                "document_url": final_url if content_type == "document" else "",
                "content_type": content_type,
                "menu_order": page_item["menu_order"] or 0,
                "page_template": page_template,
            }

        return result

    def process_links(self, page_template, external_link, document_url):
        """Processa links baseado no template com melhoria para documentos"""

        def is_valid_url(url):
            if not url or not isinstance(url, str):
                return False
            url = url.strip()
            return url.startswith(("http://", "https://")) and "." in url

        if page_template == "pageModel-linkToDocument.php":
            # Para páginas de documento, priorizar document_url (URLs reais)
            if is_valid_url(document_url):
                return "document", document_url
            elif is_valid_url(external_link):
                return "document", external_link
            else:
                return "html_content", ""

        elif page_template == "pageModel-linkExternal.php" and is_valid_url(
            external_link
        ):
            return "external_link", external_link
        else:
            return "html_content", ""

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
            self.stdout.write(
                f"Configurando root_page para locale {self.SOURCE_LOCALE}"
            )
            root_page.locale = source_locale
            root_page.save()

        # Criar páginas About para cada idioma
        self.stdout.write("=== Criando páginas About ===")
        about_pages = self.create_about_pages(root_page)

        # Debug: mostrar status das páginas About
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
            self.stdout.write(
                self.style.ERROR(f"Páginas About faltando para: {missing_locales}")
            )
            return
        else:
            self.stdout.write(self.style.SUCCESS("✅ Todas as páginas About criadas"))

        # Criar páginas filhas
        self.stdout.write(
            f"\nCriando páginas filhas (parent ID: {about_parent_id})"
        )
        self.create_children_pages(about_pages, about_parent_id, pages_data)

        self.stdout.write("\nEstrutura criada")

    def create_about_pages(self, parent):
        """Cria páginas About para todos os idiomas com fallback robusto"""
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
                translated_about = self.try_copy_for_translation(
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
        # Verificar se já existe
        existing = AboutScieloOrgPage.objects.filter(
            locale=locale, slug="about", path__startswith=parent.path
        ).first()

        if existing:
            self.stdout.write(f"About existente: {lang_code} → {existing.url}")
            return existing

        # Criar nova página About
        about_page = AboutScieloOrgPage(
            title=self.LANGUAGES[lang_code]["about_title"],
            slug=self.get_unique_slug(parent, "about"),
            locale=locale,
            body=f"Página institucional sobre o SciELO - {lang_code.upper()}.",
            translation_key=translation_key,
        )

        try:
            parent.add_child(instance=about_page)
            about_page.save_revision().publish()
            self.stdout.write(f"About criado: {lang_code} → {about_page.url}")
            return about_page
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao criar About {lang_code}: {e}"))
            return None

    def try_copy_for_translation(self, source_page, target_locale, lang_code):
        """Tenta criar tradução usando copy_for_translation"""
        try:
            # Verificar se tradução já existe
            existing = source_page.get_translation(target_locale)
            if existing:
                self.stdout.write(
                    f"Tradução About existente: {lang_code} → {existing.url}"
                )
                return existing
        except source_page.__class__.DoesNotExist:
            pass

        try:
            translated_page = source_page.copy_for_translation(target_locale)
            translated_page.title = self.LANGUAGES[lang_code]["about_title"]
            translated_page.body = (
                f"Página institucional sobre o SciELO - {lang_code.upper()}."
            )
            translated_page.save_revision().publish()

            self.stdout.write(
                f"About traduzido (copy_for_translation): {lang_code} → {translated_page.url}"
            )
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

    def create_children_pages(self, about_pages, parent_post_id, pages_data):
        """Cria páginas filhas recursivamente mantendo hierarquia e ordem"""
        # Filtrar filhas do parent_post_id
        children = []
        for post_id, page_info in pages_data.items():
            processed = page_info["processed"]
            if self.SOURCE_LOCALE in processed:
                source_data = processed[self.SOURCE_LOCALE]
                if source_data["parent_id"] == parent_post_id:
                    children.append((post_id, page_info))

        # Ordenar por menu_order (importante para manter ordem original)
        children.sort(key=lambda x: x[1]["processed"][self.SOURCE_LOCALE]["menu_order"])

        self.stdout.write(
            f"Processando {len(children)} páginas filhas do parent {parent_post_id}"
        )

        for post_id, page_info in children:
            processed = page_info["processed"]
            source_data = processed[self.SOURCE_LOCALE]

            if not source_data["title"]:
                self.stdout.write(f"Pulando página {post_id} sem título")
                continue

            if self.SOURCE_LOCALE not in about_pages:
                self.stdout.write(
                    f"About page não encontrada para {self.SOURCE_LOCALE}"
                )
                continue

            # Criar página no idioma fonte com parent correto
            source_parent = about_pages[self.SOURCE_LOCALE]
            child_page = self.create_child_page(source_parent, source_data)

            if not child_page:
                continue

            # Armazenar traduções desta página filha
            child_translations = {self.SOURCE_LOCALE: child_page}

            # Criar traduções para outros idiomas
            for lang_code in self.LANGUAGES.keys():
                if (
                    lang_code == self.SOURCE_LOCALE
                    or lang_code not in processed
                    or lang_code not in about_pages
                ):
                    continue

                target_data = processed[lang_code]
                target_parent = about_pages[lang_code]

                translated_child = self.create_translated_child(
                    child_page, target_parent, target_data
                )

                if translated_child:
                    child_translations[lang_code] = translated_child
                    self.stdout.write(
                        f"Tradução criada: {target_data['title']} → {lang_code}"
                    )

            # Recursão para filhas das filhas (hierarquia completa)
            self.create_children_pages(child_translations, post_id, pages_data)

    def create_child_page(self, parent, page_data):
        """Cria uma página filha preservando hierarquia"""
        # Verificar se página já existe primeiro
        existing = AboutScieloOrgPage.objects.filter(
            locale=parent.locale, slug=page_data["slug"], path__startswith=parent.path
        ).first()

        if existing:
            self.stdout.write(
                f"Página existente: {page_data['title']} → {existing.url}"
            )
            return existing

        page_kwargs = self.prepare_page_data(page_data)

        # Garantir slug único antes de criar
        unique_slug = self.get_unique_slug(parent, page_data["slug"])

        child_page = AboutScieloOrgPage(
            title=page_data["title"],
            slug=unique_slug,
            locale=parent.locale,
            **page_kwargs,
        )

        try:
            parent.add_child(instance=child_page)
            child_page.save_revision().publish()
            self.stdout.write(f"Página criada: {page_data['title']} → {child_page.url}")
            return child_page
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao criar página {page_data['title']}: {e}")
            )
            return None

    def create_translated_child(self, source_page, target_parent, target_data):
        """Cria tradução de página filha com parent correto"""
        try:
            # Verificar se tradução já existe
            existing = source_page.get_translation(target_parent.locale)
            if existing:
                self.stdout.write(
                    f"Tradução existente: {target_data['title']} → {existing.url}"
                )
                return existing
        except source_page.__class__.DoesNotExist:
            pass

        try:
            # Tentar copy_for_translation primeiro
            translated_page = source_page.copy_for_translation(target_parent.locale)

            # Atualizar com dados traduzidos
            translated_page.title = target_data["title"]
            translated_page.slug = self.clean_slug(
                target_data["slug"] or target_data["title"]
            )

            page_kwargs = self.prepare_page_data(target_data)
            for key, value in page_kwargs.items():
                setattr(translated_page, key, value)

            translated_page.save_revision().publish()
            self.stdout.write(
                f"Tradução via copy_for_translation: {target_data['title']} → {translated_page.url}"
            )
            return translated_page

        except Exception as e:
            # Fallback: criar página independente com mesmo translation_key
            self.stdout.write(
                f"copy_for_translation falhou para {target_data['title']}, usando fallback"
            )

            # Criar nova página no parent correto
            fallback_page = AboutScieloOrgPage(
                title=target_data["title"],
                slug=self.get_unique_slug(
                    target_parent,
                    self.clean_slug(target_data["slug"] or target_data["title"]),
                ),
                locale=target_parent.locale,
                translation_key=source_page.translation_key,  # Vincular como tradução
                **self.prepare_page_data(target_data),
            )

            try:
                target_parent.add_child(instance=fallback_page)
                fallback_page.save_revision().publish()
                self.stdout.write(
                    f"Tradução via fallback: {target_data['title']} → {fallback_page.url}"
                )
                return fallback_page
            except Exception as e2:
                self.stdout.write(
                    self.style.ERROR(
                        f"Erro no fallback para {target_data['title']}: {e2}"
                    )
                )
                return None

    def prepare_page_data(self, page_data):
        """Prepara dados da página com processamento melhorado de documentos"""
        page_kwargs = {
            "body": page_data.get("body", ""),
            "external_link": "",
            "attached_document": None,
            "list_page": [],
        }

        content_type = page_data.get("content_type", "html_content")

        if content_type == "document":
            document_url = page_data.get("document_url", "")
            if document_url:
                # document_url já vem com URL real do utilitário
                if document_url.startswith("http"):
                    document = self.download_document(document_url, page_data["title"])
                    if document:
                        page_kwargs["attached_document"] = document
                        page_kwargs["body"] = (
                            f"<p>Documento anexado: {page_data['title']}</p>"
                        )
                        self.stdout.write(
                            f"Documento anexado com sucesso: {page_data['title']}"
                        )
                    else:
                        # Fallback: link direto se download falhar
                        page_kwargs["external_link"] = document_url
                        page_kwargs["body"] = (
                            f"<p>Documento: <a href='{document_url}' target='_blank'>{page_data['title']}</a></p>"
                        )
                        self.stdout.write(
                            f"Documento como link direto: {page_data['title']}"
                        )
                else:
                    # ID ou formato inválido - tratar como conteúdo
                    page_kwargs["body"] = (
                        page_data.get("body") or f"<p>Documento: {document_url}</p>"
                    )

        elif content_type == "external_link":
            external_link = page_data.get("external_link", "")
            if external_link and external_link.startswith("http"):
                page_kwargs["external_link"] = external_link
                page_kwargs["body"] = (
                    f"<p>Link externo: <a href='{external_link}' target='_blank'>{page_data['title']}</a></p>"
                )
            else:
                page_kwargs["body"] = page_data.get("body", "")

        else:  # html_content
            page_kwargs["body"] = page_data.get("body", "")

        return page_kwargs

    def download_document(self, document_url, title):
        """Baixa documento do URL"""
        try:
            response = requests.get(document_url, timeout=30)
            if response.status_code != 200:
                return None

            filename = document_url.split("/")[-1]
            if not filename or "." not in filename:
                filename = f"{self.clean_slug(title)}.pdf"

            # Verificar se já existe
            existing = Document.objects.filter(title=title).first()
            if existing:
                return existing

            document = Document(title=title)
            document.file.save(filename, ContentFile(response.content), save=True)
            return document

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Erro ao baixar documento {document_url}: {e}")
            )
            return None
