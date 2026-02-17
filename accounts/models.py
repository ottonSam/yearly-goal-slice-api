import uuid

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """
    Custom user that uses UUID as primary key instead of integer autoincrement.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    email_verification_code_hash = models.CharField(max_length=128, blank=True, null=True)
    email_verification_expires_at = models.DateTimeField(blank=True, null=True)

    def set_email_verification_code(self, code: str, expires_at):
        self.email_verification_code_hash = make_password(code)
        self.email_verification_expires_at = expires_at

    def check_email_verification_code(self, code: str) -> bool:
        if not self.email_verification_code_hash:
            return False
        return check_password(code, self.email_verification_code_hash)

    def is_email_verification_expired(self, now=None) -> bool:
        if not self.email_verification_expires_at:
            return True
        current = now or timezone.now()
        return self.email_verification_expires_at <= current

# Create your models here.
