from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    """
    Enforces passwords with length > 8 including upper, lower, number and special char.
    """

    def validate(self, password, user=None):
        errors = []
        if len(password) <= 8:
            errors.append("Password must be longer than 8 characters.")
        if not any(char.islower() for char in password):
            errors.append("Password must include at least one lowercase letter.")
        if not any(char.isupper() for char in password):
            errors.append("Password must include at least one uppercase letter.")
        if not any(char.isdigit() for char in password):
            errors.append("Password must include at least one number.")
        if not any(not char.isalnum() for char in password):
            errors.append("Password must include at least one special character.")

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Password must be longer than 8 characters and include uppercase, lowercase, "
            "number and special character."
        )
