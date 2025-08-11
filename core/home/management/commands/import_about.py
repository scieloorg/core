import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from django.core.management.base import BaseCommand
from wagtail.models import Page, Locale
from core.home.models import AboutScieloOrgPage, HomePage
from django.utils.text import slugify


def parse_multilang(text):
    if not text:
        return {}
    matches = re.findall(r"{:([a-z]{2})\}(.*?)(?=\{:[a-z]{2}\}|{:}|$)", text, flags=re.DOTALL)
    return {lang: value.strip() for lang, value in matches if value.strip()}

def get_text(item, *paths):
    for path in paths:
        v = item.findtext(path)
        if v:
            return v
    return ""

def normalize_slug(title, post_id=None, max_length=45):
    base_slug = slugify(title)[:max_length]
    return f"{base_slug}-{post_id}" if post_id else base_slug

def build_page_data(item):
    post_id = get_text(item, "{http://wordpress.org/export/1.2/}post_id", "wp:post_id")
    parent_id = get_text(item, "{http://wordpress.org/export/1.2/}post_parent", "wp:post_parent") or "0"
    title_raw = get_text(item, "title")
    content_raw = get_text(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
    link = get_text(item, "link")

    title_ml = parse_multilang(title_raw)
    content_ml = parse_multilang(content_raw)

    main_title = title_ml.get("br") or title_ml.get("en") or title_ml.get("es") or "pagina-sem-titulo"
    main_slug = normalize_slug(main_title, post_id)
    menu_order = int(get_text(item, "{http://wordpress.org/export/1.2/}menu_order", "wp:menu_order") or "0")

    # Preencher bodies por idioma
    body_br = content_ml.get('br', '').strip()
    body_en = content_ml.get('en', '').strip()
    body_es = content_ml.get('es', '').strip()
    has_content = any([body_br, body_en, body_es])

    external_link = ""
    if not has_content and link:
        external_link = link

    return {
        'pt-br': {
            "post_id": post_id,
            "parent_id": parent_id,
            "main_title": main_title,
            'title': title_ml.get('br', ''),
            "lang": "pt-br",
            'body': body_br,
            "external_link": external_link,
            "menu_order": menu_order,
            "slug": main_slug,
        },
        'en': {
            "post_id": post_id,
            "parent_id": parent_id,
            "main_title": main_title,
            'title': title_ml.get('en', ''),
            "lang": "pt-br",
            'body': body_en,
            "external_link": external_link,
            "menu_order": menu_order,
            "slug": main_slug,
        },
        'es': {
            "post_id": post_id,
            "parent_id": parent_id,
            "main_title": main_title,
            'title': title_ml.get('es', ''),
            "lang": "pt-br",
            'body': body_es,
            "external_link": external_link,
            "menu_order": menu_order,
            "slug": main_slug,
        }
    }


class Command(BaseCommand):
    help = "Importa conteúdo do Sobre o SciELO a partir do XML do WordPress, respeitando a hierarquia."

    def add_arguments(self, parser):
        parser.add_argument("xml_path", type=str)

    def get_children_map(self, xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        items = []
        item_by_id = {}
        children_map = defaultdict(list)

        for item in root.findall(".//item"):
            page_content = build_page_data(item)
            for lang_code, page_data in page_content.items():
                # Pular itens sem título
                if page_data["main_title"] == "pagina-sem-titulo":
                    continue

                items.append(page_data)
                item_by_id[page_data["post_id"]] = page_data
                children_map[page_data["parent_id"]].append(page_data)

        return children_map, item_by_id

    def handle(self, *args, **options):
        def create_pages(parent_wagtail_page, post_id):
            children = sorted(children_map.get(post_id, []), key=lambda d: d["menu_order"])
            for data in children:
                try:
                    locale = Locale.objects.get(language_code=data["lang"])
                except Locale.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Locale {data["lang"]} não existe. Criando...')
                    )
                    locale = Locale.objects.create(language_code=data["lang"])
                page = AboutScieloOrgPage(
                    title=data["title"],
                    slug=data["slug"],
                    body=data["body"],
                    external_link=data["external_link"],
                    list_page=[],
                    locale=locale,
                )
                parent_wagtail_page.add_child(instance=page)
                page.save_revision().publish()
                create_pages(page, data["post_id"])

        about_page = self.start_and_clean()

        children_map, item_by_id = self.get_children_map(options["xml_path"])

        # Criar árvore de páginas
        create_pages(about_page, about_xml_post_id)
        about_page.save_revision().publish()
        self.stdout.write(self.style.SUCCESS("Páginas 'Sobre o SciELO' criadas/atualizadas respeitando hierarquia!"))

    def start_and_clean(self):
        DEFAULT_LANG = "pt-br"
        title_br = "Sobre o SciELO"
        title_en = "About SciELO"
        title_es = "Sobre el SciELO"
        slug_root = "sobre-o-scielo"
        body_br = "Página institucional Sobre o SciELO."
        body_en = "Institutional About SciELO page."
        body_es = "Página institucional Sobre el SciELO."

        translations = {
            "pt-br": {"title": title_br, "body": body_br, "slug": slug_root},
            "en": {"title": title_en, "body": body_en, "slug": "about-scielo"},
            "es": {"title": title_es, "body": body_es, "slug": "sobre-el-scielo"},
        }

        # 1) Garantir HomePage publicada
        homepage = HomePage.objects.first()
        if not homepage:
            root = Page.get_first_root_node()
            homepage = HomePage(title="Homepage", slug="homepage")
            root.add_child(instance=homepage)
            homepage.save_revision().publish()
        else:
            homepage.save_revision().publish()

        # 2) Garantir Locale padrão
        try:
            pt_locale = Locale.objects.get(language_code=DEFAULT_LANG)
        except Locale.DoesNotExist:
            pt_locale = Locale.objects.create(language_code=DEFAULT_LANG)

        # 3) Garantir/ criar a página raiz pt-br
        about_page = (
            AboutScieloOrgPage.objects
            .child_of(homepage)
            .filter(slug=slug_root, locale=pt_locale)
            .first()
        )

        if not about_page:
            about_page = AboutScieloOrgPage(
                title=translations["pt-br"]["title"],
                slug=translations["pt-br"]["slug"],
                body=translations["pt-br"]["body"],
                external_link="",
                list_page=[],
                locale=pt_locale,
            )
            homepage.add_child(instance=about_page)
            about_page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"Criada raiz pt-br: {about_page.title}"))
        else:
            # limpa apenas a subárvore (descendentes), preservando a raiz
            for p in about_page.get_descendants().specific().order_by("-depth"):
                p.delete()
            self.stdout.write(self.style.WARNING("Subárvore existente limpa (descendentes removidos)."))

        # 4) Criar/atualizar traduções en/es a partir da pt-br
        for lang in ("en", "es"):
            data = translations[lang]
            try:
                target_locale = Locale.objects.get(language_code=lang)
            except Locale.DoesNotExist:
                target_locale = Locale.objects.create(language_code=lang)

            # Se já existir tradução, atualiza; senão, copia
            tr_page = AboutScieloOrgPage.objects.filter(
                translation_key=about_page.translation_key,
                locale=target_locale,
            ).first()

            if tr_page is None:
                if hasattr(about_page, "copy_for_translation"):
                    tr_page = about_page.copy_for_translation(locale=target_locale, copy_parents=True)
                else:
                    tr_page = AboutScieloOrgPage(
                        title=data["title"],
                        slug=data["slug"],
                        body=data["body"],
                        external_link="",
                        list_page=[],
                        locale=target_locale,
                    )
                    homepage.add_child(instance=tr_page)

            tr_page.title = data["title"]
            tr_page.slug = data["slug"]
            tr_page.body = data["body"]
            tr_page.external_link = ""
            tr_page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS(f"Tradução {lang} pronta: {tr_page.title}"))

        return about_page

