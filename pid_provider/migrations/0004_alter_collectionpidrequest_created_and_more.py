# Generated by Django 5.0.8 on 2025-05-26 14:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pid_provider", "0003_pidproviderendpoint_fixpidv2"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="collectionpidrequest",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="collectionpidrequest",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="collectionpidrequest",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="collectionpidrequest",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="correct_pid_v2",
            field=models.CharField(
                blank=True, max_length=24, null=True, verbose_name="V2 correto"
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="incorrect_pid_v2",
            field=models.CharField(
                blank=True, max_length=24, null=True, verbose_name="V2 incorreto"
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="fixpidv2",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="otherpid",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="otherpid",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="otherpid",
            name="pid_type",
            field=models.CharField(
                blank=True, max_length=7, null=True, verbose_name="Tipo de PID"
            ),
        ),
        migrations.AlterField(
            model_name="otherpid",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="otherpid",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="api_password",
            field=models.TextField(blank=True, null=True, verbose_name="Senha da API"),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="api_username",
            field=models.TextField(
                blank=True, null=True, verbose_name="Nome de usuário da API"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="pid_provider_api_get_token",
            field=models.TextField(
                blank=True, null=True, verbose_name="Obter URI do Token"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="pid_provider_api_post_xml",
            field=models.TextField(
                blank=True, null=True, verbose_name="URI de Postagem XML"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="timeout",
            field=models.IntegerField(
                blank=True, null=True, verbose_name="Tempo limite"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderconfig",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="name",
            field=models.CharField(
                blank=True,
                choices=[("fix-pid-v2", "fix-pid-v2")],
                max_length=16,
                null=True,
                verbose_name="Nome do Endpoint",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderendpoint",
            name="url",
            field=models.URLField(
                blank=True, max_length=128, null=True, verbose_name="URL do Endpoint"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="aop_pid",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="PID AOP"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="article_pub_year",
            field=models.CharField(
                blank=True,
                max_length=4,
                null=True,
                verbose_name="Ano de Publicação do Documento",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="available_since",
            field=models.CharField(
                blank=True, max_length=10, null=True, verbose_name="Disponível desde"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="elocation_id",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="id_elocation"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="fpage",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="página_inicial"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="fpage_seq",
            field=models.CharField(
                blank=True, max_length=8, null=True, verbose_name="página_inicial_seq"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="lpage",
            field=models.CharField(
                blank=True, max_length=20, null=True, verbose_name="página_final"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="main_toc_section",
            field=models.TextField(
                blank=True, null=True, verbose_name="seção_principal_toc"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="number",
            field=models.CharField(
                blank=True, max_length=16, null=True, verbose_name="número"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="origin_date",
            field=models.CharField(
                blank=True, max_length=10, null=True, verbose_name="Data de origem"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="pkg_name",
            field=models.TextField(
                blank=True, null=True, verbose_name="Nome do Pacote"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="pub_year",
            field=models.CharField(
                blank=True, max_length=4, null=True, verbose_name="ano_publicação"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="suppl",
            field=models.CharField(
                blank=True, max_length=16, null=True, verbose_name="supl"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="z_article_titles_texts",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                verbose_name="textos_titulos_artigo",
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="z_collab",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="colab"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="z_journal_title",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="título do periódico"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="z_partial_body",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="corpo_parcial"
            ),
        ),
        migrations.AlterField(
            model_name="pidproviderxml",
            name="z_surnames",
            field=models.CharField(
                blank=True, max_length=64, null=True, verbose_name="sobrenomes"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="detail",
            field=models.JSONField(blank=True, null=True, verbose_name="Detalhe"),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="origin",
            field=models.CharField(
                blank=True,
                max_length=124,
                null=True,
                verbose_name="Origem da Requisição",
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="origin_date",
            field=models.CharField(
                blank=True, max_length=10, null=True, verbose_name="Data de origem"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="result_msg",
            field=models.TextField(
                blank=True, null=True, verbose_name="Mensagem de Resultado"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="result_type",
            field=models.TextField(
                blank=True, null=True, verbose_name="Tipo de Resultado"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="pidrequest",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
        migrations.AlterField(
            model_name="xmlversion",
            name="created",
            field=models.DateTimeField(
                auto_now_add=True, verbose_name="Data de criação"
            ),
        ),
        migrations.AlterField(
            model_name="xmlversion",
            name="creator",
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_creator",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Criador",
            ),
        ),
        migrations.AlterField(
            model_name="xmlversion",
            name="updated",
            field=models.DateTimeField(
                auto_now=True, verbose_name="Data da última atualização"
            ),
        ),
        migrations.AlterField(
            model_name="xmlversion",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="%(class)s_last_mod_user",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Atualizador",
            ),
        ),
    ]
