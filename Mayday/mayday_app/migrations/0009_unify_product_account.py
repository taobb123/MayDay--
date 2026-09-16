from django.db import migrations


def unify_accounts(apps, schema_editor):
    from mayday_app.identity import unify_product_account
    unify_product_account()


class Migration(migrations.Migration):

    dependencies = [
        ('mayday_app', '0008_membershiporder'),
    ]

    operations = [
        migrations.RunPython(unify_accounts, migrations.RunPython.noop),
    ]
