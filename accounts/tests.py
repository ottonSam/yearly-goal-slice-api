from django.contrib.auth import get_user_model
from django.urls import reverse
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
            'email': 'newemail@example.com',
        }

        response = self.client.patch(reverse('auth-update-profile'), data=payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, payload['first_name'])
        self.assertEqual(self.user.last_name, payload['last_name'])
        self.assertEqual(self.user.email, payload['email'])

    def test_update_profile_with_invalid_name(self):
        payload = {
            'first_name': '12',
            'last_name': 'User',
            'email': 'tester@example.com',
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_returns_new_access_token(self):
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
