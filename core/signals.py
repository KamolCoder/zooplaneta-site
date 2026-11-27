"""Every editor works in the light admin theme (the site's team asked for one look for all)."""
from django.conf import settings
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from wagtail.users.models import UserProfile

ADMIN_THEME = "light"


@receiver(pre_save, sender=UserProfile)
def force_light_theme(sender, instance, **kwargs):
    instance.theme = ADMIN_THEME


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.get_for_user(instance).save()


@receiver(post_save, sender="core.SiteSettings")
def default_season_periods(sender, instance, created, **kwargs):
    """A new site gets the standard seasons and holidays (see core/season.py)."""
    if created:
        from core.models import SeasonPeriod
        from core.season import add_default_periods
        add_default_periods(instance, SeasonPeriod)
