from django.conf import settings
from django.db import migrations


def light_theme_for_everyone(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("wagtailusers", "UserProfile")
    for user in User.objects.all():
        UserProfile.objects.update_or_create(user=user, defaults={"theme": "light"})


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("wagtailusers", "0015_userprofile_keyboard_shortcuts"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.RunPython(light_theme_for_everyone, migrations.RunPython.noop)]
