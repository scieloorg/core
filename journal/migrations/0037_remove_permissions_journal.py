from django.db import migrations

def remove_custom_permissions(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    journal_ct = ContentType.objects.get(app_label='journal', model='journal')

    journal_permission = Permission.objects.filter(content_type=journal_ct).delete()

class Migration(migrations.Migration):

    dependencies = [
        ("journal", "0036_alter_journal_options"),
    ]

    operations = [
        migrations.RunPython(remove_custom_permissions),
    ]