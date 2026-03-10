from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("article", "0047_articleaffiliation_normalized_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="relatedarticle",
            name="crossref_update_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("addendum", "Addendum"),
                    ("clarification", "Clarification"),
                    ("correction", "Correction"),
                    ("corrigendum", "Corrigendum"),
                    ("erratum", "Erratum"),
                    ("expression_of_concern", "Expression of Concern"),
                    ("new_edition", "New Edition"),
                    ("new_version", "New Version"),
                    ("partial_retraction", "Partial Retraction"),
                    ("removal", "Removal"),
                    ("retraction", "Retraction"),
                    ("withdrawal", "Withdrawal"),
                ],
                help_text=(
                    "Crossref CrossMark update type corresponding to this related article. "
                    "Derived from the JATS related-article-type or explicitly set via custom-meta."
                ),
                max_length=50,
                null=True,
                verbose_name="CrossRef Update Type",
            ),
        ),
    ]
