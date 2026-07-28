# Documentação Técnica — SciELO Core

## Sumário

- [Introdução](#introdução)
- [Visão geral da arquitetura](#visão-geral-da-arquitetura)
- [Tecnologias e dependências principais](#tecnologias-e-dependências-principais)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Componentes (apps Django)](#componentes-apps-django)
  - [Núcleo da aplicação](#núcleo-da-aplicação)
  - [Modelagem editorial e bibliográfica](#modelagem-editorial-e-bibliográfica)
  - [Identificadores e provedores](#identificadores-e-provedores)
  - [Pessoas, instituições e localização](#pessoas-instituições-e-localização)
  - [Vocabulários e taxonomias](#vocabulários-e-taxonomias)
  - [Ingestão, validação e processamento de XML](#ingestão-validação-e-processamento-de-xml)
  - [Busca e indexação](#busca-e-indexação)
  - [Armazenamento de arquivos](#armazenamento-de-arquivos)
  - [Operação, monitoramento e relatórios](#operação-monitoramento-e-relatórios)
- [Serviços de infraestrutura](#serviços-de-infraestrutura)
- [Configuração e ambientes](#configuração-e-ambientes)
- [APIs](#apis)
- [Tarefas assíncronas (Celery)](#tarefas-assíncronas-celery)
- [Internacionalização](#internacionalização)
- [Testes, lint e qualidade](#testes-lint-e-qualidade)
- [Como executar localmente](#como-executar-localmente)

---

## Introdução

O **SciELO Core** é a aplicação central do ecossistema SciELO responsável por
gerenciar os metadados, conteúdos e fluxos editoriais que sustentam a rede de
periódicos científicos da SciELO. A aplicação centraliza informações sobre
coleções, periódicos, fascículos, artigos, referências bibliográficas,
pesquisadores, instituições, áreas temáticas, vocabulários controlados,
identificadores persistentes (DOI/PID) e métricas associadas (Altmetric).

O projeto é construído em **Django** com o CMS **Wagtail** sobre o template
[`scieloorg/template-scms`](https://github.com/scieloorg/template-scms),
oferecendo um painel administrativo unificado, APIs REST autenticadas via JWT,
busca textual com Solr/Haystack e processamento assíncrono com Celery.

### Objetivos da aplicação

- Servir como **fonte autoritativa de metadados** dos artigos, periódicos,
  fascículos e demais entidades do SciELO.
- Oferecer **interfaces administrativas** (Wagtail/Django Admin) para curadoria
  por equipes editoriais e operacionais.
- Expor **APIs REST** para integração com aplicações satélites (sites públicos,
  ferramentas de produção, depósitos de DOI, etc.).
- Prover **serviços de PID/DOI** (provisionamento e gestão de identificadores
  persistentes).
- Suportar **ingestão, validação e indexação** de pacotes XML SPS (SciELO
  Publishing Schema).
- Orquestrar **tarefas assíncronas** de ingestão, validação, harvesting e
  manutenção via Celery.

---

## Visão geral da arquitetura

```
                        ┌───────────────────────────┐
                        │   Navegador / Aplicações  │
                        └─────────────┬─────────────┘
                                      │ HTTP(S)
                          ┌───────────▼───────────┐
                          │      Traefik (TLS)    │
                          └───────────┬───────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │     Django + Wagtail (gunicorn)   │
                    │  - Admin / Wagtail / DRF (JWT)    │
                    │  - Sites / páginas (journalpage)  │
                    └──┬───────┬────────────┬───────────┘
                       │       │            │
            ┌──────────▼┐  ┌───▼────┐  ┌────▼─────┐  ┌──────────┐
            │ PostgreSQL│  │  Solr  │  │  MinIO   │  │  Redis   │
            │ (dados)   │  │(busca) │  │(arquivos)│  │ (broker) │
            └───────────┘  └────────┘  └──────────┘  └────┬─────┘
                                                          │
                                            ┌─────────────▼──────────────┐
                                            │ Celery worker / beat / flower│
                                            └──────────────────────────────┘

   Stack opcional de observabilidade (monitoring_stack/):
     Prometheus, Grafana, Logstash, Kibana
```

A aplicação adota uma arquitetura **modular orientada a apps Django**, em que
cada domínio de negócio (artigo, periódico, instituição, etc.) é
implementado em um app independente com seus próprios modelos, views,
templates, tarefas Celery, hooks Wagtail e (quando aplicável) endpoints REST
em um submódulo `api/`.

---

## Tecnologias e dependências principais

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3 |
| Framework web | Django 5.2 |
| CMS / admin estendido | Wagtail 7.1 |
| API REST | Django REST Framework + SimpleJWT |
| Banco de dados | PostgreSQL |
| Busca | Apache Solr 9 + django-haystack |
| Armazenamento de objetos | MinIO (compatível S3) |
| Fila de tarefas | Celery + Redis (broker) |
| Agendador | django-celery-beat |
| Monitoramento de tasks | Flower |
| Proxy reverso | Traefik |
| Observabilidade | Prometheus, Grafana, Logstash, Kibana |
| Autenticação | django-allauth + wagtail_2fa |
| Frontend admin | Wagtail + django-crispy-forms (Bootstrap 5) |
| Internacionalização | Django i18n (pt-br, es, en) |

A lista completa está em [`requirements/base.txt`](../requirements/base.txt),
[`requirements/local.txt`](../requirements/local.txt) e
[`requirements/production.txt`](../requirements/production.txt).

---

## Estrutura do repositório

```
core/                       Repositório raiz
├── config/                 Configurações Django (settings, urls, celery, menu)
│   ├── settings/           base.py, local.py, production.py, test.py
│   ├── api_router.py       Rotas DRF
│   ├── celery_app.py       Inicialização do Celery
│   └── urls.py             Roteamento principal
├── core/                   App "núcleo": usuários, home, libs, utilitários
├── compose/                Dockerfiles e scripts (local/ e production/)
├── docs/                   Documentação (Sphinx + este arquivo)
├── fixtures/               Dados iniciais
├── locale/                 Traduções (pt-br, es, en)
├── monitoring_stack/       Configurações de observabilidade
├── requirements/           Dependências por ambiente
├── local.yml               docker-compose para desenvolvimento
├── production.yml          docker-compose para produção
├── manage.py
└── <apps de domínio>/      Um diretório por app Django (ver seção seguinte)
```

---

## Componentes (apps Django)

A relação canônica de apps locais está em
[`config/settings/base.py`](../config/settings/base.py) (variável `LOCAL_APPS`).
A seguir, cada app é descrito por seu propósito e principais funcionalidades.

### Núcleo da aplicação

#### `core`
App fundacional que reúne componentes compartilhados pelos demais apps:
- subapp `core.users` — modelo de usuário customizado (`AUTH_USER_MODEL = "users.User"`);
- `home` — páginas de entrada do Wagtail;
- `libs`, `utils`, `validators.py` — utilidades comuns (validações, helpers,
  middlewares);
- `search_site` — integração de busca em nível de site;
- `mongodb.py`, `routers.py`, `forms.py` — integrações e roteadores.

#### `core_settings`
Configurações dinâmicas e parametrizáveis da aplicação editáveis pelo admin
(modelos, views e templates para preferências globais).

### Modelagem editorial e bibliográfica

#### `collection`
Coleções SciELO (ex.: SciELO Brasil, SciELO Saúde Pública). Define a entidade
agregadora de periódicos por país/temática, com APIs e hooks Wagtail.

#### `journal`
Periódicos científicos: metadados de revistas, ISSN, indexação, formatos de
importação, validações específicas e fontes (`sources/`). Inclui controllers,
APIs REST e fixtures.

#### `journalpage`
Páginas públicas de periódicos no Wagtail (templates, templatetags e views
para apresentação dos periódicos no site).

#### `issue`
Fascículos (issues) dos periódicos, incluindo integração com formatos
ArticleMeta, validação e serialização de metadados.

#### `article`
Artigos científicos: modelos, controllers, ingestão a partir de fontes
externas (`sources/`), API REST, índices de busca (`search_indexes.py`) e
fluxos de extração/validação.

#### `book`
Livros e capítulos publicados pelo SciELO Books, com modelos, formulários,
fontes e admin Wagtail dedicados.

#### `reference`
Referências bibliográficas associadas aos artigos.

#### `editorialboard`
Conselho editorial dos periódicos: membros, papéis, vínculos institucionais,
importação por CSV e API.

### Identificadores e provedores

#### `pid_provider`
Provisionamento e gestão de **PIDs (Persistent Identifiers)** SciELO. Inclui
provider/base provider, controller, modelos, fixtures, fontes e API REST. É
um dos serviços críticos do SciELO Core.

#### `doi`
Modelagem de **DOIs** atribuídos a artigos/recursos.

#### `doi_manager`
Gestão e fluxos de depósito/atualização de DOIs (modelos e migrações).

### Pessoas, instituições e localização

#### `researcher`
Pesquisadores (autores) com seus identificadores (ORCID etc.), filiações,
formulários, tarefas de carga e API.

#### `institution`
Instituições, com importação por CSV (`chkcsvfmt.fmt`, `scimago_chkcsvfmt.fmt`),
fixtures, hooks Wagtail e API.

#### `organization`
Organizações em sentido amplo, com modelos dinâmicos
(`dynamic_models.py`), tarefas e API. Complementa `institution` em casos em que
a estrutura organizacional precisa ser parametrizada.

#### `location`
Países, estados e cidades (localizações geográficas), com fixtures, formato
CSV de importação (`country_chkcsvfmt.fmt`) e API.

### Vocabulários e taxonomias

#### `thematic_areas`
Áreas temáticas (taxonomia controlada) com importação CSV
(`fixtures_thematic_areas.csv`, `thematic_areas.csv`), templates próprios,
URLs, controller e tarefas.

#### `vocabulary`
Vocabulários controlados utilizados por outros apps (palavras-chave,
descritores, etc.), com API e admin Wagtail.

### Ingestão, validação e processamento de XML

#### `xml_validation`
Validação de pacotes XML SPS (SciELO Publishing Schema): modelos para
representar resultados de validação, API e admin Wagtail.

#### `tracker`
Rastreamento (auditoria/log) de eventos de processamento — choices, modelos
e tarefas Celery, com integração ao Wagtail.

#### `bigbang`
Conjunto de scripts e tarefas Celery (`tasks.py`, `tasks_scheduler.py`,
`utils/`) para **operações em larga escala** — cargas iniciais, reprocessamentos
massivos e migrações de dados ("big bang" data loads).

### Busca e indexação

#### `search`
Frontend de busca: views, URLs, templates, templatetags e modelos auxiliares
para a busca pública do SciELO Core (sustentada por Solr via Haystack).
Configurações de Haystack (`HAYSTACK_CONNECTIONS`) ficam em
`config/settings/base.py`, com cores `default` e `oai`.

### Armazenamento de arquivos

#### `files_storage`
Abstração de armazenamento de arquivos sobre **MinIO** (`minio.py`), com
controller, exceções e utilitários. Usado por outros apps para persistir XMLs,
PDFs e demais ativos.

### Operação, monitoramento e relatórios

#### `altmetric`
Integração com **Altmetric** para coleta e exibição de métricas alternativas
de impacto, com tarefas Celery agendadas.

#### `report`
Geração de relatórios operacionais e gerenciais (modelos, views, scripts e
tarefas).

---

## Serviços de infraestrutura

Os arquivos [`local.yml`](../local.yml) e [`production.yml`](../production.yml)
descrevem a stack Docker Compose. Os serviços típicos são:

| Serviço | Função |
|---|---|
| `django` | Aplicação web (gunicorn em produção) |
| `postgres` | Banco de dados relacional |
| `solr` | Servidor de busca (Solr 9.3, cores `core` e `oai`) |
| `redis` | Broker Celery e cache |
| `celeryworker` | Worker de tarefas assíncronas |
| `celerybeat` | Scheduler de tarefas periódicas |
| `flower` | Monitoramento das filas Celery |
| `traefik` (prod) | Proxy reverso e terminação TLS |
| `adminer` (local) | Cliente web para PostgreSQL |
| `minio` | Armazenamento de objetos (S3-compatível) |

A pasta [`monitoring_stack/`](../monitoring_stack) contém configurações
opcionais de **Prometheus**, **Grafana**, **Logstash** e **Kibana** para
métricas e logs centralizados (a aplicação já expõe métricas via
`django-prometheus`, configurado no middleware).

---

## Configuração e ambientes

As configurações Django ficam em [`config/settings/`](../config/settings):

- `base.py` — base comum (apps, middleware, autenticação, JWT, Haystack,
  Wagtail, idiomas, etc.).
- `local.py` — desenvolvimento.
- `production.py` — produção.
- `test.py` — execução de testes.

Variáveis de ambiente são lidas com `django-environ` e organizadas em
arquivos `.envs/` (não versionados em produção). Veja
[`merge_production_dotenvs_in_dotenv.py`](../merge_production_dotenvs_in_dotenv.py)
para o utilitário de consolidação.

---

## APIs

As APIs REST são expostas via Django REST Framework. As rotas são
registradas em [`config/api_router.py`](../config/api_router.py) e
consolidadas em [`config/urls.py`](../config/urls.py).

- Autenticação: **JWT** (`rest_framework_simplejwt`) com `Bearer` tokens.
  Tempo padrão: 60 minutos para o access token e 1 dia para o refresh token.
- Paginação padrão: `PageNumberPagination` (tamanho controlado por
  `DRF_PAGE_SIZE`).
- Apps que expõem APIs possuem submódulo `api/`: `article`, `collection`,
  `editorialboard`, `institution`, `issue`, `journal`, `location`,
  `organization`, `pid_provider`, `researcher`, `vocabulary`,
  `xml_validation`, `doi`.

### Registro de publicação de artigo

O endpoint `POST /api/v1/publish_article/` registra que um artigo já
identificado pelo PID Provider foi publicado ou atualizado no site público. A
operação usa `pid_v3` e `sps_pkg_name` para localizar o `PidProviderXML`,
carrega os metadados do XML SPS versionado, cria ou atualiza o `Article` e
marca o registro como público.

Autenticação:

```bash
curl -X POST http://localhost:8000/api/v2/auth/token/ \
  -d 'username=scms-upload&password=secret'
```

Resposta:

```json
{
  "refresh": "eyJhbGciOi...",
  "access": "eyJhbGciOi..."
}
```

Requisição:

```bash
curl -X POST http://localhost:8000/api/v1/publish_article/ \
  -H 'Authorization: Bearer eyJhbGciOi...' \
  -H 'Content-Type: application/json' \
  -d '{
    "pid_v3": "67CrZnsyZLpV7dyR7dgp6Vt",
    "sps_pkg_name": "2236-8906-hoehnea-49-e1082020"
  }'
```

Resposta para criação (`201 Created`) ou atualização (`200 OK`):

```json
{
  "article_id": 123,
  "pid_v3": "67CrZnsyZLpV7dyR7dgp6Vt",
  "sps_pkg_name": "2236-8906-hoehnea-49-e1082020",
  "operation": "created",
  "data_status": "PUBLIC",
  "is_public": true,
  "timestamp": "2026-06-23T15:00:00+00:00"
}
```

Cenários de erro:

- `400 Bad Request`: `pid_v3` ou `sps_pkg_name` ausente, vazio ou inválido.
- `400 Bad Request`: o `PidProviderXML` existe, mas o XML não pôde ser
  convertido em `Article` por inconsistência de metadados.
- `401 Unauthorized`: token JWT ausente, expirado ou inválido.
- `404 Not Found`: nenhum `PidProviderXML` foi encontrado para o par
  `pid_v3` e `sps_pkg_name`.

Pré-requisitos para exposição OAI-PMH:

- O `PidProviderXML` precisa existir no Core e possuir XML SPS versionado.
- O XML precisa conter metadados suficientes para localizar periódico e
  fascículo e criar o `Article`.
- Após sucesso no endpoint, o `Article` fica com status público e os flags de
  publicação usados pelo índice OAI; assim, a exposição passa a depender apenas
  do fluxo normal de indexação do Core/Solr.

---

## Tarefas assíncronas (Celery)

Configuração em [`config/celery_app.py`](../config/celery_app.py) e
[`config/celery_signals.py`](../config/celery_signals.py). Tarefas periódicas
são gerenciadas pelo **django-celery-beat** (com agendamento persistido no
banco). Apps com `tasks.py` definem operações assíncronas — por exemplo:

- `article/tasks.py` — ingestão e processamento de artigos.
- `pid_provider/tasks.py` — provisionamento de PIDs.
- `altmetric/tasks.py` — coleta de métricas Altmetric.
- `bigbang/tasks.py` e `bigbang/tasks_scheduler.py` — cargas em lote.

O monitoramento das filas pode ser feito pelo **Flower** (serviço `flower`).

---

## Internacionalização

A aplicação suporta três idiomas, declarados em `LANGUAGES` no `base.py`:

- `pt-br` — Português (Brasil)
- `es` — Español
- `en` — English

As traduções ficam em [`locale/`](../locale) e o Wagtail está configurado
com `WAGTAIL_I18N_ENABLED = True`, permitindo conteúdo multilíngue no CMS.

---

## Testes, lint e qualidade

- **Testes:** executados com `pytest` (configuração em
  [`pytest.ini`](../pytest.ini)). Cada app possui seu `tests.py` (ou
  arquivos `test_*.py`).
- **Lint/format:** `pre-commit` configurado em
  [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) inclui **isort**
  (perfil black) e **black**. A pipeline de CI
  ([`.github/workflows/ci.yml`](../.github/workflows/ci.yml)) falha em caso
  de divergência de formatação ou ordenação de imports.
- **Estilo adicional:** `setup.cfg` define configurações de flake8/isort.

---

## Como executar localmente

A forma recomendada de executar o ambiente de desenvolvimento é via
**Docker Compose**:

```bash
# Build e subida da stack local
docker compose -f local.yml build
docker compose -f local.yml up
```

O script [`start-dev.sh`](../start-dev.sh) automatiza passos comuns de
inicialização. Para mais detalhes sobre setup, consulte o
[README.md](../README.md) e o template base
[`scieloorg/template-scms`](https://github.com/scieloorg/template-scms).

---

> Este documento descreve a arquitetura e os componentes do SciELO Core no
> momento de sua redação. Para detalhes sempre atualizados sobre apps,
> modelos e endpoints, consulte o código-fonte e as definições em
> `config/settings/base.py` (`LOCAL_APPS`) e `config/api_router.py`.
