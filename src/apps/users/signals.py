from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    from django.conf import settings
    from rest_framework.authtoken.models import Token

    if created and settings.ENABLE_DRF_TOKEN_AUTH:
        Token.objects.create(user=instance)
