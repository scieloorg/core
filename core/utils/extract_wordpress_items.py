"""
Extrai itens do WordPress (páginas/posts) de um export WXR,
incluindo conteúdo multilíngue e attachments para documentos.
"""
import re
from xml.etree import ElementTree as ET

NAMESPACES = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "wp": "http://wordpress.org/export/1.2/",
    "excerpt": "http://wordpress.org/export/1.2/excerpt/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "atom": "http://www.w3.org/2005/Atom",
    "sy": "http://purl.org/rss/1.0/modules/syndication/",
    "slash": "http://purl.org/rss/1.0/modules/slash/",
}

LANG_ALIASES = {
    "br": "pt-br",
    "pt": "pt-br",
    "pt-br": "pt-br",
    "en": "en",
    "es": "es",
}

LANG_TOKEN_RE = re.compile(r"{:([a-z]{2}(?:-[a-z]{2})?)}", re.IGNORECASE | re.DOTALL)


def normalize_lang(code):
    """Normaliza um código de idioma."""
    if not code:
        return None
    return LANG_ALIASES.get(code.lower(), code.lower())


def split_wpglobus(text):
    """
    Divide texto codificado com WPGlobus em blocos específicos por idioma.

    Formato WPGlobus: {:pt-br}...{:}{:en}...{:}{:es}...{:}

    Retorna dict mapeando idioma -> conteúdo.
    """
    if not text:
        return {}

    matches = list(LANG_TOKEN_RE.finditer(text))
    if not matches:
        return {"pt-br": text}

    result = {}
    for i, match in enumerate(matches):
        lang = normalize_lang(match.group(1))
        if not lang:
            continue

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()

        if content.endswith("{:}"):
            content = content[:-3].strip()

        if content:
            result[lang] = content

    return result


def get_text(element, path):
    """Extrai texto de um elemento XML."""
    if element is None:
        return None
    found = element.find(path, NAMESPACES)
    return found.text if found is not None else None


def safe_int(value):
    """Converte string para int de forma segura."""
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def collect_categories(item):
    """Coleta categorias do item."""
    categories = []
    for cat in item.findall("category"):
        categories.append({
            "domain": cat.get("domain"),
            "nicename": cat.get("nicename"),
            "text": (cat.text or "").strip(),
        })
    return categories


def collect_postmeta(item):
    """Coleta todos os metadados do post."""
    metas = []
    for meta in item.findall("wp:postmeta", NAMESPACES):
        key_el = meta.find("wp:meta_key", NAMESPACES)
        val_el = meta.find("wp:meta_value", NAMESPACES)
        key = key_el.text if key_el is not None else None
        val = val_el.text if val_el is not None else None
        if key is not None:
            metas.append((key, val))
    return metas


def extract_slug_i18n(metas, default_slug):
    """Extrai slugs multilíngues dos metadados."""
    meta_dict = {k: v for k, v in metas if k}
    slugs = {}

    if default_slug:
        slugs["pt-br"] = default_slug

    slug_mappings = [
        ("_wpglobus_slug_en", "en"),
        ("_wpglobus_slug_es", "es")
    ]

    for meta_key, lang in slug_mappings:
        value = meta_dict.get(meta_key)
        if value:
            slugs[lang] = value.strip()

    return slugs


def extract_links_and_docs(metas):
    """Extrai links externos e documentos dos metadados."""
    links = {}
    docs = {}

    for key, value in metas:
        if not key:
            continue

        key_lower = key.lower()

        # Processar diferentes formatos de campos de link e documento
        if key_lower.startswith("link_"):
            parts = key_lower.split("_", 1)
            if len(parts) == 2:
                _, lang_code = parts
                normalized_lang = normalize_lang(lang_code)
                if normalized_lang:
                    clean_value = (value or "").strip() if value else None
                    if clean_value:
                        links[normalized_lang] = clean_value

        elif key_lower.startswith("document_"):
            parts = key_lower.split("_", 1)
            if len(parts) == 2:
                _, lang_code = parts
                normalized_lang = normalize_lang(lang_code)
                if normalized_lang:
                    clean_value = (value or "").strip() if value else None
                    if clean_value:
                        docs[normalized_lang] = clean_value

    return links, docs


def extract_multilingual_meta_fields(metas):
    """
    Extrai campos de metadados que contêm conteúdo multilíngue.
    Processa campos como pageTitle, pageDescription, etc.
    """
    meta_dict = {k: v for k, v in metas if k and v}

    multilingual_fields = {}

    # Campos que podem ter conteúdo multilíngue
    multilingual_meta_keys = [
        'pageTitle',
        'pageDescription',
        'acordeons_0_title',
        'acordeons_0_content',
        'acordeons_1_title',
        'acordeons_1_content',
        # Adicione mais campos conforme necessário
    ]

    for meta_key in multilingual_meta_keys:
        meta_value = meta_dict.get(meta_key)
        if meta_value and '{:' in meta_value:
            # Processar conteúdo WPGlobus
            parsed_content = split_wpglobus(meta_value)
            if parsed_content:
                multilingual_fields[meta_key] = parsed_content

    return multilingual_fields


def get_page_template(metas):
    """Extrai o template da página."""
    for key, value in metas:
        if key == '_wp_page_template' and value:
            return value
    return 'default'


def extract_attachments(xml_root):
    """
    NOVA FUNÇÃO: Extrai todos os attachments do XML e cria mapeamento ID -> URL.
    """
    attachments = {}

    channel = xml_root.find("channel")
    if channel is None:
        return attachments

    for item in channel.findall("item"):
        post_type = get_text(item, "wp:post_type")
        if post_type != "attachment":
            continue

        post_id = safe_int(get_text(item, "wp:post_id"))
        if not post_id:
            continue

        # Extrair URL do attachment
        attachment_url = get_text(item, "wp:attachment_url")
        if not attachment_url:
            # Fallback: tentar extrair do guid
            guid = get_text(item, "guid")
            if guid and (guid.startswith('http') and any(ext in guid.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx'])):
                attachment_url = guid

        if attachment_url:
            attachments[str(post_id)] = {
                'url': attachment_url,
                'filename': attachment_url.split('/')[-1] if '/' in attachment_url else attachment_url,
                'post_id': post_id,
                'title': get_text(item, "title") or "",
            }

    return attachments


def resolve_document_urls(document_i18n, attachments):
    """
    NOVA FUNÇÃO: Resolve IDs de documentos para URLs reais usando mapeamento de attachments.
    """
    resolved_docs = {}

    for lang_code, doc_value in document_i18n.items():
        if not doc_value:
            continue

        # Se já é uma URL, manter
        if doc_value.startswith(('http://', 'https://')):
            resolved_docs[lang_code] = doc_value
        # Se é ID numérico, tentar resolver
        elif doc_value.isdigit() and doc_value in attachments:
            resolved_docs[lang_code] = attachments[doc_value]['url']
        # Senão, manter original (fallback)
        else:
            resolved_docs[lang_code] = doc_value

    return resolved_docs


def extract_items(xml_path):
    """
    Faz parse de um arquivo de export WXR do WordPress e retorna uma lista
    de itens normalizados (páginas/posts) com campos multilíngues e attachments resolvidos.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    channel = root.find("channel")

    if channel is None:
        return []

    # NOVO: Primeiro, extrair todos os attachments para mapeamento
    attachments = extract_attachments(root)
    print(f"Attachments encontrados: {len(attachments)}")

    items = []
    for item in channel.findall("item"):
        post_type = get_text(item, "wp:post_type")
        if post_type not in ("page", "post"):
            continue

        # Extrair dados básicos
        post_id = safe_int(get_text(item, "wp:post_id"))
        parent_id = safe_int(get_text(item, "wp:post_parent"))
        menu_order = safe_int(get_text(item, "wp:menu_order"))
        is_sticky = safe_int(get_text(item, "wp:is_sticky"))
        status = (get_text(item, "wp:status") or "publish").strip()
        slug = get_text(item, "wp:post_name")

        # Extrair conteúdo multilíngue
        raw_title = get_text(item, "title") or ""
        raw_content = get_text(item, "content:encoded") or ""

        title_i18n = split_wpglobus(raw_title)
        content_i18n = split_wpglobus(raw_content)

        # Extrair metadados
        metas = collect_postmeta(item)
        categories = collect_categories(item)

        # Hint de idioma do WPGlobus
        lang_hint = None
        for key, value in metas:
            if key == "wpglobus_language" and value:
                lang_hint = normalize_lang(value)
                break

        # Extrair slugs, links e documentos multilíngues
        slug_i18n = extract_slug_i18n(metas, slug)
        external_link_i18n, document_i18n = extract_links_and_docs(metas)

        # NOVO: Resolver URLs de documentos usando attachments
        document_i18n = resolve_document_urls(document_i18n, attachments)

        # Extrair campos multilíngues dos metadados
        multilingual_meta = extract_multilingual_meta_fields(metas)

        # Obter template da página
        page_template = get_page_template(metas)

        items.append({
            "post_type": post_type,
            "status": status,
            "post_id": post_id,
            "parent_id": parent_id,
            "menu_order": menu_order,
            "is_sticky": is_sticky,
            "lang_hint": lang_hint,
            "title": title_i18n.get("pt-br", raw_title),
            "title_i18n": title_i18n,
            "content": content_i18n.get("pt-br", raw_content),
            "content_i18n": content_i18n,
            "slug": slug,
            "slug_i18n": slug_i18n,
            "external_link_i18n": external_link_i18n,
            "document_i18n": document_i18n,  # Agora com URLs reais
            "categories": categories,
            "metas": metas,
            "multilingual_meta": multilingual_meta,
            "page_template": page_template,
            # NOVO: Informações de attachments para debug
            "attachments_available": len(attachments),
        })

    return items
