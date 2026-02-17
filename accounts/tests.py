from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


User = get_user_model()


class AccountUpdateTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester',
            email='tester@example.com',
            password='Oldpass123',
            first_name='Test',
            last_name='User',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_update_basic_profile(self):
        payload = {
            'first_name': 'Updated',
            'last_name': 'Name',
        }

        response = self.client.patch(reverse('auth-update-profile'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, payload['first_name'])
        self.assertEqual(self.user.last_name, payload['last_name'])

    def test_update_profile_with_invalid_name(self):
        payload = {
            'first_name': '12',
            'last_name': 'User',
        }

        response = self.client.patch(reverse('auth-update-profile'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('first_name', response.data)

    def test_change_password_successfully(self):
        payload = {
            'current_password': 'Oldpass123',
            'new_password': 'Newpass123!',
        }

        response = self.client.post(reverse('auth-change-password'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))

    def test_change_password_with_wrong_current(self):
        payload = {
            'current_password': 'WrongPassword',
            'new_password': 'AnotherNew123!',
        }

        response = self.client.post(reverse('auth-change-password'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_password', response.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('Oldpass123'))

    def test_change_password_rejects_weak_password(self):
        payload = {
            'current_password': 'Oldpass123',
            'new_password': 'short',
        }

        response = self.client.post(reverse('auth-change-password'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data)

    def test_change_password_accepts_exactly_eight_characters(self):
        payload = {
            'current_password': 'Oldpass123',
            'new_password': 'Aa1!aaaa',
        }

        response = self.client.post(reverse('auth-change-password'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload['new_password']))


class AccountAuthFlowTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='authuser',
            email='auth@example.com',
            password='ValidPass123!',
            first_name='Auth',
            last_name='User',
        )

    def verify_email(self, user):
        user.email_verified = True
        user.email_verification_code_hash = None
        user.email_verification_expires_at = None
        user.save(update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"])

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_login_rejects_expired_code_and_sends_new_one(self):
        expired_code = "123456"
        self.user.email_verified = False
        self.user.email_verification_code_hash = make_password(expired_code)
        self.user.email_verification_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save(
            update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"]
        )

        response = self.client.post(
            reverse("auth-login"),
            data={"username": "authuser", "password": "ValidPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Code expired. A new code was sent to your email.", response.data["detail"])
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_verify_email_rejects_expired_code_and_sends_new_one(self):
        expired_code = "654321"
        self.user.email_verified = False
        self.user.email_verification_code_hash = make_password(expired_code)
        self.user.email_verification_expires_at = timezone.now() - timedelta(minutes=1)
        self.user.save(
            update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"]
        )

        response = self.client.post(
            reverse("auth-verify-email"),
            data={"email": "auth@example.com", "code": expired_code},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Code expired. A new code was sent to your email.", response.data["detail"])
        self.assertEqual(len(mail.outbox), 1)

    def test_verify_email_rejects_invalid_code_when_not_expired(self):
        valid_code = "987654"
        self.user.email_verified = False
        self.user.email_verification_code_hash = make_password(valid_code)
        self.user.email_verification_expires_at = timezone.now() + timedelta(hours=1)
        self.user.save(
            update_fields=["email_verified", "email_verification_code_hash", "email_verification_expires_at"]
        )

        response = self.client.post(
            reverse("auth-verify-email"),
            data={"email": "auth@example.com", "code": "000000"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid code.", response.data["code"])

    def test_register_creates_user_with_strong_password(self):
        payload = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'StrongPass123!',
            'first_name': 'New',
            'last_name': 'User',
        }

        response = self.client.post(reverse('auth-register'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(username='newuser')
        self.assertTrue(created.check_password(payload['password']))

    def test_login_returns_tokens(self):
        payload = {
            'username': 'authuser',
            'password': 'ValidPass123!',
        }

        response = self.client.post(reverse('auth-login'), data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

        self.verify_email(self.user)
        response = self.client.post(reverse('auth-login'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_returns_new_access_token(self):
        self.verify_email(self.user)
        login_response = self.client.post(
            reverse('auth-login'),
            data={'username': 'authuser', 'password': 'ValidPass123!'},
            format='json',
        )
        refresh_token = login_response.data['refresh']

        response = self.client.post(reverse('auth-refresh'), data={'refresh': refresh_token}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_me_returns_authenticated_user_data(self):
        self.verify_email(self.user)
        login_response = self.client.post(
            reverse('auth-login'),
            data={'username': 'authuser', 'password': 'ValidPass123!'},
            format='json',
        )
        access_token = login_response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        response = self.client.get(reverse('auth-me'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'authuser')
        self.assertEqual(response.data['email'], 'auth@example.com')
