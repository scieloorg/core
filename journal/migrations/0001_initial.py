# Generated by Django 3.2.12 on 2023-02-02 13:48

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import modelcluster.fields
import wagtail.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wagtailimages', '0023_add_choose_permissions'),
        ('collection', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('institution', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OfficialJournal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('title', models.CharField(blank=True, max_length=256, null=True, verbose_name='Official Title')),
                ('foundation_year', models.CharField(blank=True, max_length=4, null=True, verbose_name='Foundation Year')),
                ('issn_print', models.CharField(blank=True, max_length=9, null=True, verbose_name='ISSN Print')),
                ('issn_electronic', models.CharField(blank=True, max_length=9, null=True, verbose_name='ISSN Eletronic')),
                ('issnl', models.CharField(blank=True, max_length=9, null=True, verbose_name='ISSNL')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='officialjournal_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='officialjournal_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'verbose_name': 'Official Journal',
                'verbose_name_plural': 'Official Journals',
            },
        ),
        migrations.CreateModel(
            name='ScieloJournal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('name', models.CharField(blank=True, choices=[('facebook', 'Facebook'), ('twitter', 'Twitter'), ('journal', 'Journal URL')], max_length=255, null=True, verbose_name='Name')),
                ('url', models.URLField(blank=True, max_length=255, null=True, verbose_name='URL')),
                ('issn_scielo', models.CharField(blank=True, max_length=9, null=True, verbose_name='ISSN SciELO')),
                ('title', models.CharField(blank=True, max_length=255, null=True, verbose_name='SciELO Journal Title')),
                ('short_title', models.CharField(blank=True, max_length=100, null=True, verbose_name='Short Title')),
                ('submission_online_url', models.URLField(blank=True, max_length=255, null=True, verbose_name='Submission online URL')),
                ('collection', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='collection.collection', verbose_name='Collection')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scielojournal_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('logo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='wagtailimages.image')),
                ('official', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='journal.officialjournal', verbose_name='Official Journal')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='scielojournal_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
            options={
                'verbose_name': 'SciELO Journal',
                'verbose_name_plural': 'SciELO Journals',
            },
        ),
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('institutionhistory_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='institution.institutionhistory')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='sponsor', to='journal.scielojournal')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
            bases=('institution.institutionhistory', models.Model),
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('institutionhistory_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='institution.institutionhistory')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='publisher', to='journal.scielojournal')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
            bases=('institution.institutionhistory', models.Model),
        ),
        migrations.CreateModel(
            name='Owner',
            fields=[
                ('institutionhistory_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='institution.institutionhistory')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='owner', to='journal.scielojournal')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
            bases=('institution.institutionhistory', models.Model),
        ),
        migrations.CreateModel(
            name='Mission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Creation date')),
                ('updated', models.DateTimeField(auto_now=True, verbose_name='Last update date')),
                ('text', wagtail.fields.RichTextField(blank=True, null=True)),
                ('language', models.CharField(blank=True, choices=[('aa', 'Afar'), ('af', 'Afrikaans'), ('ak', 'Akan'), ('sq', 'Albanian'), ('am', 'Amharic'), ('ar', 'Arabic'), ('an', 'Aragonese'), ('hy', 'Armenian'), ('as', 'Assamese'), ('av', 'Avaric'), ('ae', 'Avestan'), ('ay', 'Aymara'), ('az', 'Azerbaijani'), ('bm', 'Bambara'), ('ba', 'Bashkir'), ('eu', 'Basque'), ('be', 'Belarusian'), ('bn', 'Bengali'), ('bi', 'Bislama'), ('bs', 'Bosnian'), ('br', 'Breton'), ('bg', 'Bulgarian'), ('my', 'Burmese'), ('ca', 'Catalan, Valencian'), ('ch', 'Chamorro'), ('ce', 'Chechen'), ('ny', 'Chichewa, Chewa, Nyanja'), ('zh', 'Chinese'), ('cu', 'Church Slavic, Old Slavonic, Church Slavonic, Old Bulgarian, Old Church Slavonic'), ('cv', 'Chuvash'), ('kw', 'Cornish'), ('co', 'Corsican'), ('cr', 'Cree'), ('hr', 'Croatian'), ('cs', 'Czech'), ('da', 'Danish'), ('dv', 'Divehi, Dhivehi, Maldivian'), ('nl', 'Dutch, Flemish'), ('dz', 'Dzongkha'), ('en', 'English'), ('eo', 'Esperanto'), ('et', 'Estonian'), ('ee', 'Ewe'), ('fo', 'Faroese'), ('fj', 'Fijian'), ('fi', 'Finnish'), ('fr', 'French'), ('fy', 'Western Frisian'), ('ff', 'Fulah'), ('gd', 'Gaelic, Scottish Gaelic'), ('gl', 'Galician'), ('lg', 'Ganda'), ('ka', 'Georgian'), ('de', 'German'), ('el', 'Greek, Modern (1453–)'), ('kl', 'Kalaallisut, Greenlandic'), ('gn', 'Guarani'), ('gu', 'Gujarati'), ('ht', 'Haitian, Haitian Creole'), ('ha', 'Hausa'), ('he', 'Hebrew'), ('hz', 'Herero'), ('hi', 'Hindi'), ('ho', 'Hiri Motu'), ('hu', 'Hungarian'), ('is', 'Icelandic'), ('io', 'Ido'), ('ig', 'Igbo'), ('id', 'Indonesian'), ('ia', 'Interlingua (International Auxiliary Language Association)'), ('ie', 'Interlingue, Occidental'), ('iu', 'Inuktitut'), ('ik', 'Inupiaq'), ('ga', 'Irish'), ('it', 'Italian'), ('ja', 'Japanese'), ('jv', 'Javanese'), ('kn', 'Kannada'), ('kr', 'Kanuri'), ('ks', 'Kashmiri'), ('kk', 'Kazakh'), ('km', 'Central Khmer'), ('ki', 'Kikuyu, Gikuyu'), ('rw', 'Kinyarwanda'), ('ky', 'Kirghiz, Kyrgyz'), ('kv', 'Komi'), ('kg', 'Kongo'), ('ko', 'Korean'), ('kj', 'Kuanyama, Kwanyama'), ('ku', 'Kurdish'), ('lo', 'Lao'), ('la', 'Latin'), ('lv', 'Latvian'), ('li', 'Limburgan, Limburger, Limburgish'), ('ln', 'Lingala'), ('lt', 'Lithuanian'), ('lu', 'Luba-Katanga'), ('lb', 'Luxembourgish, Letzeburgesch'), ('mk', 'Macedonian'), ('mg', 'Malagasy'), ('ms', 'Malay'), ('ml', 'Malayalam'), ('mt', 'Maltese'), ('gv', 'Manx'), ('mi', 'Maori'), ('mr', 'Marathi'), ('mh', 'Marshallese'), ('mn', 'Mongolian'), ('na', 'Nauru'), ('nv', 'Navajo, Navaho'), ('nd', 'North Ndebele'), ('nr', 'South Ndebele'), ('ng', 'Ndonga'), ('ne', 'Nepali'), ('no', 'Norwegian'), ('nb', 'Norwegian Bokmål'), ('nn', 'Norwegian Nynorsk'), ('ii', 'Sichuan Yi, Nuosu'), ('oc', 'Occitan'), ('oj', 'Ojibwa'), ('or', 'Oriya'), ('om', 'Oromo'), ('os', 'Ossetian, Ossetic'), ('pi', 'Pali'), ('ps', 'Pashto, Pushto'), ('fa', 'Persian'), ('pl', 'Polish'), ('pt', 'Portuguese'), ('pa', 'Punjabi, Panjabi'), ('qu', 'Quechua'), ('ro', 'Romanian, Moldavian, Moldovan'), ('rm', 'Romansh'), ('rn', 'Rundi'), ('ru', 'Russian'), ('se', 'Northern Sami'), ('sm', 'Samoan'), ('sg', 'Sango'), ('sa', 'Sanskrit'), ('sc', 'Sardinian'), ('sr', 'Serbian'), ('sn', 'Shona'), ('sd', 'Sindhi'), ('si', 'Sinhala, Sinhalese'), ('sk', 'Slovak'), ('sl', 'Slovenian'), ('so', 'Somali'), ('st', 'Southern Sotho'), ('es', 'Spanish, Castilian'), ('su', 'Sundanese'), ('sw', 'Swahili'), ('ss', 'Swati'), ('sv', 'Swedish'), ('tl', 'Tagalog'), ('ty', 'Tahitian'), ('tg', 'Tajik'), ('ta', 'Tamil'), ('tt', 'Tatar'), ('te', 'Telugu'), ('th', 'Thai'), ('bo', 'Tibetan'), ('ti', 'Tigrinya'), ('to', 'Tonga (Tonga Islands)'), ('ts', 'Tsonga'), ('tn', 'Tswana'), ('tr', 'Turkish'), ('tk', 'Turkmen'), ('tw', 'Twi'), ('ug', 'Uighur, Uyghur'), ('uk', 'Ukrainian'), ('ur', 'Urdu'), ('uz', 'Uzbek'), ('ve', 'Venda'), ('vi', 'Vietnamese'), ('vo', 'Volapük'), ('wa', 'Walloon'), ('cy', 'Welsh'), ('wo', 'Wolof'), ('xh', 'Xhosa'), ('yi', 'Yiddish'), ('yo', 'Yoruba'), ('za', 'Zhuang, Chuang'), ('zu', 'Zulu')], max_length=2, null=True, verbose_name='Idioma')),
                ('creator', models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mission_creator', to=settings.AUTH_USER_MODEL, verbose_name='Creator')),
                ('journal', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='mission', to='journal.scielojournal')),
                ('updated_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mission_last_mod_user', to=settings.AUTH_USER_MODEL, verbose_name='Updater')),
            ],
        ),
        migrations.CreateModel(
            name='JournalSocialNetwork',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('name', models.CharField(blank=True, choices=[('facebook', 'Facebook'), ('twitter', 'Twitter'), ('journal', 'Journal URL')], max_length=255, null=True, verbose_name='Name')),
                ('url', models.URLField(blank=True, max_length=255, null=True, verbose_name='URL')),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='journalsocialnetwork', to='journal.scielojournal')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='EditorialManager',
            fields=[
                ('institutionhistory_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='institution.institutionhistory')),
                ('sort_order', models.IntegerField(blank=True, editable=False, null=True)),
                ('page', modelcluster.fields.ParentalKey(on_delete=django.db.models.deletion.CASCADE, related_name='editorialmanager', to='journal.scielojournal')),
            ],
            options={
                'ordering': ['sort_order'],
                'abstract': False,
            },
            bases=('institution.institutionhistory', models.Model),
        ),
        migrations.AddIndex(
            model_name='scielojournal',
            index=models.Index(fields=['issn_scielo'], name='journal_sci_issn_sc_bfe46e_idx'),
        ),
        migrations.AddIndex(
            model_name='scielojournal',
            index=models.Index(fields=['title'], name='journal_sci_title_2b7b30_idx'),
        ),
        migrations.AddIndex(
            model_name='scielojournal',
            index=models.Index(fields=['short_title'], name='journal_sci_short_t_54db21_idx'),
        ),
        migrations.AddIndex(
            model_name='scielojournal',
            index=models.Index(fields=['submission_online_url'], name='journal_sci_submiss_fa957f_idx'),
        ),
        migrations.AddIndex(
            model_name='officialjournal',
            index=models.Index(fields=['title'], name='journal_off_title_2bbaa8_idx'),
        ),
        migrations.AddIndex(
            model_name='officialjournal',
            index=models.Index(fields=['foundation_year'], name='journal_off_foundat_fcc7eb_idx'),
        ),
        migrations.AddIndex(
            model_name='officialjournal',
            index=models.Index(fields=['issn_print'], name='journal_off_issn_pr_dccb39_idx'),
        ),
        migrations.AddIndex(
            model_name='officialjournal',
            index=models.Index(fields=['issn_electronic'], name='journal_off_issn_el_89169a_idx'),
        ),
        migrations.AddIndex(
            model_name='officialjournal',
            index=models.Index(fields=['issnl'], name='journal_off_issnl_4304c5_idx'),
        ),
        migrations.AddIndex(
            model_name='mission',
            index=models.Index(fields=['journal'], name='journal_mis_journal_386d75_idx'),
        ),
        migrations.AddIndex(
            model_name='mission',
            index=models.Index(fields=['language'], name='journal_mis_languag_bfebee_idx'),
        ),
    ]
