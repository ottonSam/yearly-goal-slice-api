import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone


VERIFICATION_CODE_TTL = timedelta(hours=2)


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _from_email() -> str:
    return (
        getattr(settings, "DEFAULT_FROM_EMAIL", None)
        or getattr(settings, "EMAIL_HOST_USER", None)
        or "no-reply@example.com"
    )


def send_verification_email(user, code: str) -> None:
    subject = "Confirmacao de email"
    message = (
        "Seu codigo de confirmacao de email e: "
        f"{code}\n\n"
        "Este codigo expira em 2 horas."
    )
    html_message = None
    if getattr(settings, "APP_ENV", "dev").lower() == "prod":
        html_message = render_to_string("emails/email_verification.html", {"code": code})

    send_mail(
        subject=subject,
        message=message,
        from_email=_from_email(),
        recipient_list=[user.email],
        fail_silently=False,
        html_message=html_message,
    )


def refresh_verification_code(user) -> str:
    code = _generate_code()
    expires_at = timezone.now() + VERIFICATION_CODE_TTL
    user.set_email_verification_code(code, expires_at)
    user.save(update_fields=["email_verification_code_hash", "email_verification_expires_at"])
    return code


def refresh_and_send_verification_code(user) -> str:
    code = refresh_verification_code(user)
    send_verification_email(user, code)
    return code
