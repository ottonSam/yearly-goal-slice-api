from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Wallet


User = get_user_model()


class WalletAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='wallet_owner',
            email='wallet_owner@example.com',
            password='StrongPass123!',
            first_name='Wallet',
            last_name='Owner',
            email_verified=True,
        )
        self.other_user = User.objects.create_user(
            username='wallet_other',
            email='wallet_other@example.com',
            password='StrongPass123!',
            first_name='Wallet',
            last_name='Other',
            email_verified=True,
        )
        self.client.force_authenticate(user=self.user)

    def create_wallet(self, **overrides):
        payload = {
            'name': 'Wallet Principal',
            'limit': '5000.00',
            'cycle_limit_default': '3000.00',
            'cycle_starts': 25,
            'cycle_ends': 9,
        }
        payload.update(overrides)
        return self.client.post('/api/v1/wallets/', payload, format='json')

    def test_requires_authentication(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/wallets/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_crud_wallet_with_soft_delete(self):
        create_response = self.create_wallet()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        wallet_id = create_response.data['id']

        list_response = self.client.get('/api/v1/wallets/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        retrieve_response = self.client.get(f'/api/v1/wallets/{wallet_id}/')
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data['name'], 'Wallet Principal')

        patch_response = self.client.patch(
            f'/api/v1/wallets/{wallet_id}/',
            {'name': 'Wallet Atualizada', 'cycle_limit_default': '3200.00'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['name'], 'Wallet Atualizada')

        delete_response = self.client.delete(f'/api/v1/wallets/{wallet_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        wallet = Wallet.objects.get(id=wallet_id)
        self.assertFalse(wallet.active)

        list_after_delete = self.client.get('/api/v1/wallets/')
        self.assertEqual(list_after_delete.status_code, status.HTTP_200_OK)
        self.assertEqual(list_after_delete.data, [])

    def test_user_cannot_access_other_user_wallet(self):
        wallet = Wallet.objects.create(
            user=self.user,
            name='Wallet Privada',
            limit=Decimal('2000.00'),
            cycle_limit_default=Decimal('1000.00'),
            cycle_starts=5,
            cycle_ends=20,
        )

        self.client.force_authenticate(user=self.other_user)

        retrieve_response = self.client.get(f'/api/v1/wallets/{wallet.id}/')
        self.assertEqual(retrieve_response.status_code, status.HTTP_404_NOT_FOUND)

        patch_response = self.client.patch(
            f'/api/v1/wallets/{wallet.id}/',
            {'name': 'Tentativa de Alteração'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)

        delete_response = self.client.delete(f'/api/v1/wallets/{wallet.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_name_unique_per_user_case_insensitive(self):
        first = self.create_wallet(name='Reserva Mensal')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        duplicate_same_user = self.create_wallet(name='reserva mensal')
        self.assertEqual(duplicate_same_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', duplicate_same_user.data)

        self.client.force_authenticate(user=self.other_user)
        other_user_same_name = self.client.post(
            '/api/v1/wallets/',
            {
                'name': 'RESERVA MENSAL',
                'limit': '9000.00',
                'cycle_limit_default': '4000.00',
                'cycle_starts': 1,
                'cycle_ends': 15,
            },
            format='json',
        )
        self.assertEqual(other_user_same_name.status_code, status.HTTP_201_CREATED)

    def test_validates_limits_and_cycle_days(self):
        invalid = self.create_wallet(
            limit='0.00',
            cycle_limit_default='0.00',
            cycle_starts=0,
            cycle_ends=32,
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('limit', invalid.data)
        self.assertIn('cycle_limit_default', invalid.data)
        self.assertIn('cycle_starts', invalid.data)
        self.assertIn('cycle_ends', invalid.data)

        invalid_relation = self.create_wallet(limit='100.00', cycle_limit_default='150.00')
        self.assertEqual(invalid_relation.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('limit', invalid_relation.data)

    def test_rejects_cycle_start_equal_cycle_end(self):
        response = self.create_wallet(cycle_starts=10, cycle_ends=10)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cycle_ends', response.data)

    def test_accepts_cycle_that_wraps_month(self):
        response = self.create_wallet(cycle_starts=25, cycle_ends=9)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cycle_starts'], 25)
        self.assertEqual(response.data['cycle_ends'], 9)

    def test_user_is_defined_by_authenticated_user(self):
        response = self.client.post(
            '/api/v1/wallets/',
            {
                'user': str(self.other_user.id),
                'name': 'Wallet Segura',
                'limit': '2000.00',
                'cycle_limit_default': '1000.00',
                'cycle_starts': 3,
                'cycle_ends': 18,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], str(self.user.id))
