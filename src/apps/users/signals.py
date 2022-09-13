from django.conf import settings
from rest_framework.authtoken.models import Token
from django.dispatch import receiver
from django.db.models.signals import pre_delete, post_save


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
