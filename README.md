# Template SCMS

Project that contains a generic template for content management SciELO context.

[![Black code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)

License: GPLv3


## Startup the development environment and operations

You can use docker commands for the following if you wish, just check our makefile

What about commands in the makefile?

Type inside de project ```make help```:

```bash
    Usage: make [target] [argument] ...

    Argument:
        compose = {compose_file_name}

        targets:

        help                                           show this help
        app_version                                    Show version of webapp
        vcs_ref                                        Show last commit ref
        build_date                                     Show build date
        build                              Build app using $(COMPOSE_FILE_DEV)
        up                                 Start app using $(COMPOSE_FILE_DEV)
        logs                               See all app logs using $(COMPOSE_FILE_DEV)
        stop                               Stop all app using $(COMPOSE_FILE_DEV)
        ps                                 See all containers using $(COMPOSE_FILE_DEV)
        rm                                 Remove all containers using $(COMPOSE_FILE_DEV)
        django_shell                       Open python terminal from django $(COMPOSE_FILE_DEV)
        wagtail_sync                       Wagtail sync Page fields (repeat every time you add a new language and to update the wagtailcore_page translations) $(COMPOSE_FILE_DEV)
        wagtail_update_translation_field   Wagtail update translation fields, user this command first $(COMPOSE_FILE_DEV)
        django_createsuperuser             Create a super user from django $(COMPOSE_FILE_DEV)
        django_bash                        Open a bash terminar from django container using $(COMPOSE_FILE_DEV)
        django_test                        Run tests from django container using $(COMPOSE_FILE_DEV)
        django_fast                        Run tests fast from django container using $(COMPOSE_FILE_DEV)
        django_makemigrations              Run makemigrations from django container using $(COMPOSE_FILE_DEV)
        django_migrate                     Run migrate from django container using $(COMPOSE_FILE_DEV)
        django_makemessages                Run ./manage.py makemessages $(COMPOSE_FILE_DEV)
        django_compilemessages             Run ./manage.py compilemessages $(COMPOSE_FILE_DEV)
        django_dump_auth                   Run manage.py dumpdata auth --indent=2 $(COMPOSE_FILE_DEV)
        django_load_auth                   Run manage.py dumpdata auth --indent=2 $(COMPOSE_FILE_DEV)
        dump_data                          Dump database into .sql $(COMPOSE_FILE_DEV)
        restore_data                       Restore database into from latest.sql file $(COMPOSE_FILE_DEV)

```

To build the stack for development enviroment you can use the following command:

```bash
    make build compose=local.yml
```

is the same of type:

```bash
    make
```

To run the project type:

```bash
    make up
```

To stop the project type:

```bash
    make stop
```

If you want to build, run, wherever with other params on .yml or from production or duplicate a subfolder in .envs and a subfolder on compose and "listo" you can user the make command with argument compose.

Note that the stack is configured with 2 files docker-compose environment development=local.yml and production=production.yml.

Below are some actions you must follow for properly running applications.

## Settings

Moved to [settings](http://cookiecutter-django.readthedocs.io/en/latest/settings.html).

## Basic Commands

### Setting Up Your Users

-   To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

-   To create a **superuser account**, use this command:

        $ python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    $ mypy core

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    $ coverage run -m pytest
    $ coverage html
    $ open htmlcov/index.html

#### Running tests with pytest

    $ pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/developing-locally.html#sass-compilation-live-reloading).

### Celery

This app comes with Celery.

To run a celery worker:

``` bash
cd core
celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important *where* the celery commands are run. If you are in the same folder with *manage.py*, you should be right.

### Email Server

In development, it is often nice to be able to see emails that are being sent from your application. For that reason local SMTP server [MailHog](https://github.com/mailhog/MailHog) with a web interface is available as docker container.

Container mailhog will start automatically when you will run all docker containers.
Please check [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html) for more details how to start all containers.

With MailHog running, to view messages that are sent by your application, open your browser and go to `http://127.0.0.1:8025`

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](http://cookiecutter-django.readthedocs.io/en/latest/deployment-with-docker.html).
