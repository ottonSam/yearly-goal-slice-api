import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user that uses UUID as primary key instead of integer autoincrement.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

# Create your models here.
