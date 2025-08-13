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

def build_page_data(item):
    ns = {"wp": "http://wordpress.org/export/1.2/"}

    post_id = get_text(item, "{http://wordpress.org/export/1.2/}post_id", "wp:post_id")
    parent_id = get_text(item, "{http://wordpress.org/export/1.2/}post_parent", "wp:post_parent") or "0"
    title_raw = get_text(item, "title")
    content_raw = get_text(item, "{http://purl.org/rss/1.0/modules/content/}encoded")
    link = get_text(item, "link")

    title_ml = parse_multilang(title_raw)
    content_ml = parse_multilang(content_raw)

    main_title = title_ml.get("br") or title_ml.get("en") or title_ml.get("es")

    slug = item.findtext("wp:post_name", namespaces=ns)
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
            "slug": slug,
        },
        'en': {
            "post_id": post_id,
            "parent_id": parent_id,
            "main_title": main_title,
            'title': title_ml.get('en', ''),
            "lang": "en",
            'body': body_en,
            "external_link": external_link,
            "menu_order": menu_order,
            "slug": slug,
        },
        'es': {
            "post_id": post_id,
            "parent_id": parent_id,
            "main_title": main_title,
            'title': title_ml.get('es', ''),
            "lang": "es",
            'body': body_es,
            "external_link": external_link,
            "menu_order": menu_order,
            "slug": slug,
        }
    }


class Command(BaseCommand):
    help = "Importa conteúdo do Sobre o SciELO a partir do XML do WordPress, respeitando a hierarquia."

    def add_arguments(self, parser):
        parser.add_argument("xml_path", type=str)

    def get_children_map(self, xml_path):
        tree = ET.parse(xml_path)
        root = tree.getroot()
        item_by_id = {}
        children_map = defaultdict(list)

        for item in root.findall(".//item"):
            page_content = build_page_data(item)
            for lang_code, page_data in page_content.items():
                # Pular itens sem título
                if not page_data["main_title"] or not page_data["title"]:
                    continue

                item_by_id[page_data["post_id"]] = page_data
                children_map[page_data["parent_id"]].append(page_data)

        return children_map, item_by_id

    def handle(self, *args, **options):
        def create_pages(parent_wagtail_page, post_id):
            children = sorted(children_map.get(post_id, []), key=lambda d: d["menu_order"])
            for data in children:
                # só cria se o idioma do item bater com o locale do pai
                if data["lang"].lower() != parent_wagtail_page.locale.language_code.lower():
                    continue
                page = AboutScieloOrgPage(
                    title=data["title"],
                    slug=data["slug"],
                    body=data["body"],
                    external_link=data["external_link"],
                    list_page=[],
                    locale=parent_wagtail_page.locale,
                )
                parent_wagtail_page.add_child(instance=page)
                page.save_revision().publish()
                create_pages(page, data["post_id"])

        children_map, item_by_id = self.get_children_map(options["xml_path"])
        for about_page in self.start_and_clean():
            # Criar árvore de páginas
            create_pages(about_page, "93")
            about_page.save_revision().publish()
            self.stdout.write(self.style.SUCCESS("Páginas 'Sobre o SciELO' criadas/atualizadas respeitando hierarquia!"))


    def start_and_clean(self):
        translations = {
            "pt-br": {
                "home": "Página Inicial",
                "slug_home": "pagina-inicial-pt-br",
                "title": "Sobre o SciELO",
                "body": "Página institucional Sobre o SciELO.",
                "slug": "sobre-o-scielo"
            },
            "en": {
                "home": "Home Page",
                "slug_home": "home-page-en",
                "title": "About SciELO",
                "body": "Institutional About SciELO page.",
                "slug": "about-scielo"
            },
            "es": {
                "home": "Página Principal",
                "slug_home": "pagina-principal-es",
                "title": "Sobre el SciELO",
                "body": "Página institucional Sobre el SciELO.",
                "slug": "sobre-el-scielo"
            },
        }

        for lang_code, info in translations.items():
            locale, _ = Locale.objects.get_or_create(language_code=lang_code)

            homepage = HomePage.objects.filter(locale=locale, slug=info["slug_home"]).order_by('id').first()
            if not homepage:
                root = Page.get_first_root_node()
                # refresca o root do banco para evitar instância "stale"
                root = Page.objects.get(pk=root.pk)
                homepage = HomePage(title=info["home"], slug=info["slug_home"], locale=locale)
                root.add_child(instance=homepage)
                homepage.save_revision().publish()

            translated = homepage.get_translation_or_none(locale)
            if not translated:
                translated = homepage.copy_for_translation(locale)
                translated.title = info["title"]
                translated.slug = info["slug"]
                translated.body = info["body"]
                translated.external_link = ""
                translated.list_page = []
                translated.locale = locale

                homepage.add_child(instance=translated)
                translated.save_revision().publish()

            about_page = AboutScieloOrgPage.objects.filter(locale=locale, slug=info["slug"]).order_by('id').first()
            if about_page:
                for p in about_page.get_children():
                    p.specific.delete()
            else:
                about_page = AboutScieloOrgPage(
                    title=info["title"],
                    slug=info["slug"],
                    body=info["body"],
                    external_link="",
                    list_page=[],
                    locale=locale,
                )

            homepage.add_child(instance=about_page)
            about_page.save_revision().publish()

            yield about_page
