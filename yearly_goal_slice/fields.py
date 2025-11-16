import uuid

from django.db import models


class UUIDAutoField(models.AutoField):
    """
    AutoField-like primary key that stores UUID4 instead of integers.
    """

    default_validators = []

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("primary_key", True)
        kwargs.setdefault("default", uuid.uuid4)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if value is None or isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(self.to_python(value))

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.pop("primary_key", None)
        kwargs.pop("editable", None)
        if kwargs.get("default") is uuid.uuid4:
            kwargs.pop("default")
        return name, path, args, kwargs

    def get_internal_type(self):
        # Ensure the DB column type matches standard UUIDField.
        return "UUIDField"

    def db_type(self, connection):
        return models.UUIDField().db_type(connection)

    def rel_db_type(self, connection):
        return self.db_type(connection)
