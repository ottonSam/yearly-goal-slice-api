from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from .models import ExpenseCategory, Wallet


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


class ExpenseCategoryAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='category_owner',
            email='category_owner@example.com',
            password='StrongPass123!',
            first_name='Category',
            last_name='Owner',
            email_verified=True,
        )
        self.other_user = User.objects.create_user(
            username='category_other',
            email='category_other@example.com',
            password='StrongPass123!',
            first_name='Category',
            last_name='Other',
            email_verified=True,
        )
        self.client.force_authenticate(user=self.user)

    def create_category(self, **overrides):
        payload = {
            'name': 'Alimentacao',
            'icon': 'mdi:food',
            'color': '#FF6B00',
        }
        payload.update(overrides)
        return self.client.post('/api/v1/wallets/categories/', payload, format='json')

    def test_crud_category(self):
        create_response = self.create_category()
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        category_id = create_response.data['id']

        list_response = self.client.get('/api/v1/wallets/categories/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['name'], 'Alimentacao')

        detail_response = self.client.get(f'/api/v1/wallets/categories/{category_id}/')
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data['icon'], 'mdi:food')

        patch_response = self.client.patch(
            f'/api/v1/wallets/categories/{category_id}/',
            {'color': '#00C2FF'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.data['color'], '#00C2FF')

        delete_response = self.client.delete(f'/api/v1/wallets/categories/{category_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExpenseCategory.objects.filter(id=category_id).exists())

    def test_category_isolation_by_user(self):
        category = ExpenseCategory.objects.create(
            user=self.user,
            name='Private Category',
            icon='mdi:shield',
            color='#111111',
        )
        self.client.force_authenticate(user=self.other_user)

        retrieve_response = self.client.get(f'/api/v1/wallets/categories/{category.id}/')
        self.assertEqual(retrieve_response.status_code, status.HTTP_404_NOT_FOUND)

        patch_response = self.client.patch(
            f'/api/v1/wallets/categories/{category.id}/',
            {'color': '#333333'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)

        delete_response = self.client.delete(f'/api/v1/wallets/categories/{category.id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_name_unique_per_user_case_insensitive(self):
        first = self.create_category(name='Health')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        duplicate = self.create_category(name='health')
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', duplicate.data)

        self.client.force_authenticate(user=self.other_user)
        allowed = self.client.post(
            '/api/v1/wallets/categories/',
            {'name': 'HEALTH', 'icon': 'mdi:heart', 'color': '#AA0000'},
            format='json',
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)

    def test_icon_and_color_are_required(self):
        missing_fields = self.client.post(
            '/api/v1/wallets/categories/',
            {'name': 'Transport'},
            format='json',
        )
        self.assertEqual(missing_fields.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_fields.data['icon'][0], 'Icon is required.')
        self.assertEqual(missing_fields.data['color'][0], 'Color is required.')

        blank_fields = self.client.post(
            '/api/v1/wallets/categories/',
            {'name': 'Transport', 'icon': '', 'color': ''},
            format='json',
        )
        self.assertEqual(blank_fields.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(blank_fields.data['icon'][0], 'Icon is required.')
        self.assertEqual(blank_fields.data['color'][0], 'Color is required.')

    def test_user_is_defined_by_authenticated_user(self):
        response = self.client.post(
            '/api/v1/wallets/categories/',
            {
                'user': str(self.other_user.id),
                'name': 'Bills',
                'icon': 'mdi:file-document',
                'color': '#123456',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user'], str(self.user.id))
