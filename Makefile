default: build

COMPOSE_FILE_DEV = local.yml

compose = ${COMPOSE_FILE_DEV}

export SCMS_BUILD_DATE=$(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
export SCMS_VCS_REF=$(strip $(shell git rev-parse --short HEAD))
export SCMS_WEBAPP_VERSION=$(strip $(shell cat VERSION))

help: ## Show this help
	@echo 'Usage: make [target] [argument] ...'
	@echo ''
	@echo 'Argument:'
	@echo "\t compose = {compose_file_name}"
	@echo ''
	@echo 'Targets:'
	@egrep '^(.+)\:\ .*##\ (.+)' ${MAKEFILE_LIST} | sed 's/:.*##/#/' | column -t -c 1 -s "#"
	@echo ''
	@echo 'Example:'
	@echo "\t Type 'make' (default target=build) is the same of type 'make build compose=local.yml'"
	@echo "\t Type 'make build' is the same of type 'make build compose=local.yml'"
	@echo "\t Type 'make up' is the same of type 'make up compose=local.yml'"

app_version: ## Show version of webapp
	@echo "Version: " $(SCMS_WEBAPP_VERSION)

latest_commit:  ## Show last commit ref
	@echo "Latest commit: " $(SCMS_VCS_REF)

build_date: ## Show build date
	@echo "Build date: " $(SCMS_BUILD_DATE)

############################################
## atalhos docker-compose desenvolvimento ##
############################################

build:  ## Build app using $(compose)
	@docker-compose -f $(compose) build

build_no_cache:  ## Build app using $(compose)
	@docker-compose -f $(compose) build --no-cache

up:  ## Start app using $(compose)
	@docker-compose -f $(compose) up -d

logs: ## See all app logs using $(compose)
	@docker-compose -f $(compose) logs -f

stop:  ## Stop all app using $(compose)
	@docker-compose -f $(compose) stop

restart:
	@docker-compose -f $(compose) restart
	
ps:  ## See all containers using $(compose)
	@docker-compose -f $(compose) ps

rm:  ## Remove all containers using $(compose)
	@docker-compose -f $(compose) rm -f

django_shell:  ## Open python terminal from django $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py shell

wagtail_sync: ## Wagtail sync Page fields (repeat every time you add a new language and to update the wagtailcore_page translations) $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py sync_page_translation_fields

wagtail_update_translation_field: ## Wagtail update translation fields, user this command first $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py update_translation_fields

django_createsuperuser: ## Create a super user from django $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py createsuperuser

django_bash: ## Open a bash terminar from django container using $(compose)
	@docker-compose -f $(compose) run --rm django bash

django_test: ## Run tests from django container using $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py test

django_fast: ## Run tests fast from django container using $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py test --failfast

django_makemigrations: ## Run makemigrations from django container using $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py makemigrations

django_migrate: ## Run migrate from django container using $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py migrate

django_makemessages: ## Run ./manage.py makemessages $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py makemessages --all

django_compilemessages: ## Run ./manage.py compilemessages $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py compilemessages

django_dump_auth: ## Run manage.py dumpdata auth --indent=2 $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py dumpdata auth --indent=2  --output=fixtures/auth.json

django_load_auth: ## Run manage.py dumpdata auth --indent=2 $(compose)
	@docker-compose -f $(compose) run --rm django python manage.py loaddata --database=default fixtures/auth.json

dump_data: ## Dump database into .sql $(compose)
	docker exec -t scielo_core_local_postgres pg_dumpall -c -U debug > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql

restore_data: ## Restore database into from latest.sql file $(compose)
	cat backup/latest.sql | docker exec -i scielo_core_local_postgres psql -U debug

############################################
## Atalhos Úteis                          ##
############################################

clean_container:  ## Remove all containers
	@docker rm $$(docker ps -a -q --no-trunc)

clean_dangling_images:  ## Remove all dangling images
	@docker rmi -f $$(docker images --filter 'dangling=true' -q --no-trunc)

clean_dangling_volumes:  ## Remove all dangling volumes
	@docker volume rm $$(docker volume ls -f dangling=true -q)

clean_project_images:  ## Remove all images with "core" on name
	@docker rmi -f $$(docker images --filter=reference='*scielo_core*' -q)

volume_down:  ## Remove all volume
	@docker-compose -f $(compose) down -v

clean_migrations: ## Remove all migrations
	@echo "Cleaning migrations..."
	@find . -path "*/migrations/*.py" -not -name "__init__.py" -not -path "./django_celery_beat/migrations*" -not -path "./core_settings/migrations*" -not -path "./core/contrib/sites/migrations*" -not -path "./core/users/migrations*" -delete
	@find . -path "*/migrations/*.pyc" -delete
	@echo "Migrations cleaned successfully."