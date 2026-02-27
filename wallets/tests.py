from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import Resolver404, resolve
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Expense, ExpenseCategory, ExpenseCycle, InstallmentSerie, Wallet


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


class ExpenseCycleAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='cycle_owner',
            email='cycle_owner@example.com',
            password='StrongPass123!',
            first_name='Cycle',
            last_name='Owner',
            email_verified=True,
        )
        self.other_user = User.objects.create_user(
            username='cycle_other',
            email='cycle_other@example.com',
            password='StrongPass123!',
            first_name='Cycle',
            last_name='Other',
            email_verified=True,
        )
        self.wallet = Wallet.objects.create(
            user=self.user,
            name='Main Wallet',
            limit=Decimal('5000.00'),
            cycle_limit_default=Decimal('3000.00'),
            cycle_starts=25,
            cycle_ends=9,
        )
        self.client.force_authenticate(user=self.user)

    def resolve_by_date(self, wallet_id, value):
        return self.client.post(
            '/api/v1/wallets/cycle/resolve/',
            {'wallet': str(wallet_id), 'date': value},
            format='json',
        )

    def create_cycle(self, wallet, month='2026-02-01', start_date='2026-02-25', end_date='2026-03-09'):
        return ExpenseCycle.objects.create(
            wallet=wallet,
            month=month,
            limit=Decimal('3000.00'),
            start_date=start_date,
            end_date=end_date,
        )

    def test_resolve_creates_and_then_returns_existing_cycle(self):
        first = self.resolve_by_date(self.wallet.id, '2026-02-26')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(first.data['created'])
        cycle_id = first.data['cycle']['id']

        second = self.resolve_by_date(self.wallet.id, '2026-03-02')
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertFalse(second.data['created'])
        self.assertEqual(second.data['cycle']['id'], cycle_id)

    def test_cross_month_cycle_end_date(self):
        response = self.resolve_by_date(self.wallet.id, '2026-02-26')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['cycle']['start_date'], '2026-02-25')
        self.assertEqual(response.data['cycle']['end_date'], '2026-03-09')
        self.assertEqual(response.data['cycle']['month'], '2026-02-01')

    def test_only_limit_can_be_updated(self):
        cycle = ExpenseCycle.objects.create(
            wallet=self.wallet,
            month='2026-02-01',
            limit=Decimal('3000.00'),
            start_date='2026-02-25',
            end_date='2026-03-09',
        )

        invalid_update = self.client.patch(
            f'/api/v1/wallets/cycle/{cycle.id}/',
            {'start_date': '2026-02-24'},
            format='json',
        )
        self.assertEqual(invalid_update.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only the 'limit' field can be updated.", str(invalid_update.data))

        valid_update = self.client.patch(
            f'/api/v1/wallets/cycle/{cycle.id}/',
            {'limit': '1500.00'},
            format='json',
        )
        self.assertEqual(valid_update.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_update.data['limit'], '1500.00')

    def test_ownership_for_resolve_retrieve_update(self):
        other_wallet = Wallet.objects.create(
            user=self.other_user,
            name='Other Wallet',
            limit=Decimal('3000.00'),
            cycle_limit_default=Decimal('1200.00'),
            cycle_starts=1,
            cycle_ends=30,
        )

        forbidden_resolve = self.resolve_by_date(other_wallet.id, '2026-02-10')
        self.assertEqual(forbidden_resolve.status_code, status.HTTP_404_NOT_FOUND)

        other_cycle = ExpenseCycle.objects.create(
            wallet=other_wallet,
            month='2026-02-01',
            limit=Decimal('1200.00'),
            start_date='2026-02-01',
            end_date='2026-02-28',
        )

        retrieve = self.client.get(f'/api/v1/wallets/cycle/{other_cycle.id}/')
        self.assertEqual(retrieve.status_code, status.HTTP_404_NOT_FOUND)

        update = self.client.patch(
            f'/api/v1/wallets/cycle/{other_cycle.id}/',
            {'limit': '1000.00'},
            format='json',
        )
        self.assertEqual(update.status_code, status.HTTP_404_NOT_FOUND)

    def test_unique_constraint_wallet_month(self):
        self.create_cycle(wallet=self.wallet)

        with self.assertRaises(IntegrityError):
            self.create_cycle(
                wallet=self.wallet,
                month='2026-02-01',
            )

    def test_list_requires_wallet_query_param(self):
        self.create_cycle(wallet=self.wallet)

        response = self.client.get('/api/v1/wallets/cycle/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The 'wallet' query parameter is required.", str(response.data['wallet']))

    def test_list_cycles_by_wallet_only(self):
        other_wallet_same_user = Wallet.objects.create(
            user=self.user,
            name='Second Wallet',
            limit=Decimal('4500.00'),
            cycle_limit_default=Decimal('2200.00'),
            cycle_starts=5,
            cycle_ends=20,
        )
        target_cycle = self.create_cycle(wallet=self.wallet, month='2026-02-01')
        self.create_cycle(
            wallet=other_wallet_same_user,
            month='2026-03-01',
            start_date='2026-03-05',
            end_date='2026-03-20',
        )

        response = self.client.get(f'/api/v1/wallets/cycle/?wallet={self.wallet.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(target_cycle.id))

    def test_list_cycles_returns_404_for_other_user_wallet(self):
        other_wallet = Wallet.objects.create(
            user=self.other_user,
            name='Other Wallet List',
            limit=Decimal('3000.00'),
            cycle_limit_default=Decimal('1500.00'),
            cycle_starts=1,
            cycle_ends=30,
        )

        response = self.client.get(f'/api/v1/wallets/cycle/?wallet={other_wallet.id}')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_cycle_includes_expenses_but_list_does_not(self):
        cycle = self.create_cycle(wallet=self.wallet)
        category = ExpenseCategory.objects.create(
            user=self.user,
            name='Food',
            icon='mdi:food',
            color='#FF6B00',
        )
        expense = Expense.objects.create(
            expense_cycle=cycle,
            expense_category=category,
            description='Groceries',
            amount=Decimal('150.00'),
            type=Expense.TYPE_SINGLE,
            date='2026-02-26',
        )

        retrieve_response = self.client.get(f'/api/v1/wallets/cycle/{cycle.id}/')
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertIn('expenses', retrieve_response.data)
        self.assertEqual(len(retrieve_response.data['expenses']), 1)
        self.assertEqual(retrieve_response.data['expenses'][0]['id'], str(expense.id))

        list_response = self.client.get(f'/api/v1/wallets/cycle/?wallet={self.wallet.id}')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)
        self.assertNotIn('expenses', list_response.data[0])


class ExpenseAndInstallmentRulesAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='expense_owner',
            email='expense_owner@example.com',
            password='StrongPass123!',
            first_name='Expense',
            last_name='Owner',
            email_verified=True,
        )
        self.client.force_authenticate(user=self.user)
        self.wallet = Wallet.objects.create(
            user=self.user,
            name='Wallet Rules',
            limit=Decimal('10000.00'),
            cycle_limit_default=Decimal('3000.00'),
            cycle_starts=1,
            cycle_ends=30,
        )
        self.category_a = ExpenseCategory.objects.create(
            user=self.user,
            name='Categoria A',
            icon='mdi:alpha-a-box',
            color='#111111',
        )
        self.category_b = ExpenseCategory.objects.create(
            user=self.user,
            name='Categoria B',
            icon='mdi:alpha-b-box',
            color='#222222',
        )
        self.cycle_feb = ExpenseCycle.objects.create(
            wallet=self.wallet,
            month='2026-02-01',
            limit=Decimal('3000.00'),
            start_date='2026-02-01',
            end_date='2026-02-28',
        )
        self.cycle_mar = ExpenseCycle.objects.create(
            wallet=self.wallet,
            month='2026-03-01',
            limit=Decimal('3000.00'),
            start_date='2026-03-01',
            end_date='2026-03-30',
        )
        self.cycle_apr = ExpenseCycle.objects.create(
            wallet=self.wallet,
            month='2026-04-01',
            limit=Decimal('3000.00'),
            start_date='2026-04-01',
            end_date='2026-04-30',
        )

    def test_create_single_expense(self):
        response = self.client.post(
            '/api/v1/wallets/expenses/',
            {
                'expense_cycle': str(self.cycle_feb.id),
                'expense_category': str(self.category_a.id),
                'description': 'Mercado',
                'amount': '150.00',
                'type': 'single_expense',
                'date': '2026-02-10',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Expense.objects.count(), 1)
        expense = Expense.objects.first()
        self.assertEqual(expense.type, Expense.TYPE_SINGLE)
        self.assertEqual(expense.amount, Decimal('150.00'))

    def test_list_expenses_requires_cycle_query_param(self):
        response = self.client.get('/api/v1/wallets/expenses/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The 'expense_cycle' query parameter is required.", str(response.data['expense_cycle']))

    def test_create_recurring_expense(self):
        response = self.client.post(
            '/api/v1/wallets/expenses/',
            {
                'expense_cycle': str(self.cycle_feb.id),
                'expense_category': str(self.category_a.id),
                'description': 'Academia',
                'amount': '99.90',
                'type': 'recurring_expense',
                'date': '2026-02-05',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        recurring = Expense.objects.filter(type=Expense.TYPE_RECURRING)
        self.assertEqual(recurring.count(), 3)
        self.assertTrue(recurring.filter(expense_cycle=self.cycle_feb, recurring_root__isnull=True).exists())
        self.assertTrue(recurring.filter(expense_cycle=self.cycle_mar).exists())
        self.assertTrue(recurring.filter(expense_cycle=self.cycle_apr).exists())

    def test_list_expenses_filters_by_cycle(self):
        feb_expense = Expense.objects.create(
            expense_cycle=self.cycle_feb,
            expense_category=self.category_a,
            description='Mercado Fevereiro',
            amount=Decimal('49.90'),
            type=Expense.TYPE_SINGLE,
            date='2026-02-03',
        )
        mar_expense = Expense.objects.create(
            expense_cycle=self.cycle_mar,
            expense_category=self.category_a,
            description='Mercado Marco',
            amount=Decimal('59.90'),
            type=Expense.TYPE_SINGLE,
            date='2026-03-03',
        )

        feb_response = self.client.get(f'/api/v1/wallets/expenses/?expense_cycle={self.cycle_feb.id}')
        self.assertEqual(feb_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(feb_response.data), 1)
        self.assertEqual(feb_response.data[0]['id'], str(feb_expense.id))

        mar_response = self.client.get(f'/api/v1/wallets/expenses/?expense_cycle={self.cycle_mar.id}')
        self.assertEqual(mar_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mar_response.data), 1)
        self.assertEqual(mar_response.data[0]['id'], str(mar_expense.id))

    def test_expense_detail_endpoint_is_not_available(self):
        expense = Expense.objects.create(
            expense_cycle=self.cycle_feb,
            expense_category=self.category_a,
            description='Mercado',
            amount=Decimal('150.00'),
            type=Expense.TYPE_SINGLE,
            date='2026-02-10',
        )

        with self.assertRaises(Resolver404):
            resolve(f'/api/v1/wallets/expenses/{expense.id}/')

    def test_create_installment_serie_generates_expenses(self):
        response = self.client.post(
            '/api/v1/wallets/installment-series/',
            {
                'wallet': str(self.wallet.id),
                'expense_category': str(self.category_a.id),
                'description': 'Notebook',
                'total_amount': '1000.00',
                'installments_count': 4,
                'start_date': '2026-02-10',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        serie = InstallmentSerie.objects.get(id=response.data['id'])
        generated = Expense.objects.filter(installment_serie=serie, type=Expense.TYPE_INSTALLMENT).order_by('date')
        self.assertEqual(generated.count(), 4)
        self.assertEqual(sum((expense.amount for expense in generated), Decimal('0.00')), Decimal('1000.00'))
        self.assertEqual(generated.first().date.isoformat(), '2026-02-10')
        self.assertEqual(generated.last().date.isoformat(), '2026-05-10')

    def test_edit_installment_serie_updates_generated_expenses(self):
        serie = InstallmentSerie.objects.create(
            wallet=self.wallet,
            expense_category=self.category_a,
            description='Curso',
            total_amount=Decimal('300.00'),
            installments_count=3,
            start_date='2026-02-08',
        )
        Expense.objects.create(
            expense_cycle=self.cycle_feb,
            expense_category=self.category_a,
            installment_serie=serie,
            description='Curso',
            amount=Decimal('100.00'),
            type=Expense.TYPE_INSTALLMENT,
            date='2026-02-08',
        )

        response = self.client.put(
            f'/api/v1/wallets/installment-series/{serie.id}/',
            {
                'wallet': str(self.wallet.id),
                'expense_category': str(self.category_a.id),
                'description': 'Curso atualizado',
                'total_amount': '600.00',
                'installments_count': 2,
                'start_date': '2026-02-08',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        serie.refresh_from_db()
        generated = Expense.objects.filter(installment_serie=serie).order_by('date')
        self.assertEqual(generated.count(), 2)
        self.assertEqual(sum((expense.amount for expense in generated), Decimal('0.00')), Decimal('600.00'))
        self.assertTrue(all(expense.description == 'Curso atualizado' for expense in generated))

    def test_installment_series_allows_only_post_put_delete(self):
        serie = InstallmentSerie.objects.create(
            wallet=self.wallet,
            expense_category=self.category_a,
            description='Curso',
            total_amount=Decimal('300.00'),
            installments_count=3,
            start_date='2026-02-08',
        )

        list_response = self.client.get('/api/v1/wallets/installment-series/')
        self.assertEqual(list_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        retrieve_response = self.client.get(f'/api/v1/wallets/installment-series/{serie.id}/')
        self.assertEqual(retrieve_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        patch_response = self.client.patch(
            f'/api/v1/wallets/installment-series/{serie.id}/',
            {'description': 'Nao deve atualizar por patch'},
            format='json',
        )
        self.assertEqual(patch_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
