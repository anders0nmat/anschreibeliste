from django.test import TestCase, Client, AsyncClient

from django.core.exceptions import PermissionDenied
from django.forms import Form, NumberInput
from django.contrib.auth.models import User

from django.utils.timezone import now
from datetime import datetime, timedelta
from django.forms.models import modelform_factory
from django.utils.formats import get_format

from .models import Transaction, Account, Product
from .eventstream import send_event
from .formfield import FixedPrecisionField

from django.urls import reverse
from asgiref.sync import sync_to_async
import re


# Create your tests here.

class TransactionModelTest(TestCase):
    def setUp(self) -> None:
        self.user1: User = User.objects.create_user(username='test1', password='1234')
        self.user2: User = User.objects.create_user(username='test2', password='1234')

        self.staffUser: User = User.objects.create_user(username='test_staff', password='1234', is_staff=True)
        self.acc1: Account = Account.objects.create(display_name='acc1', credit=20_00, member=False)

        self.default_transaction = {
            'account': self.acc1,
            'amount': 50,
            'type': Transaction.TransactionType.ORDER,
            'reason': 'buy .50€',
        }

    def get_test_transactions(self) -> tuple[Transaction, Transaction, Transaction, Transaction]:
        fresh_transaction: Transaction = Transaction.objects.create(
            **self.default_transaction,
            issuer=self.user1
        )
        
        reverted_transaction: Transaction = Transaction.objects.create(
            **self.default_transaction,    
            issuer=self.user1
        )
        rt2: Transaction = Transaction.objects.create(
            **self.default_transaction,
            related_transaction=reverted_transaction,    
            issuer=self.user1
        )
        reverted_transaction.related_transaction = rt2
        reverted_transaction.save()

        foreign_transaction: Transaction = Transaction.objects.create(
            **self.default_transaction,
            issuer=self.user2
        )

        stale_transaction: Transaction = Transaction.objects.create(
            **self.default_transaction,    
            issuer=self.user1
        )
        stale_transaction.timestamp = now() - Transaction.revert_threshold - timedelta(seconds=2)
        
        return (fresh_transaction, stale_transaction, foreign_transaction, reverted_transaction)

    def test_revertNoUser(self):
        """
        Test revert of transaction with no user (user=None)
        No User is not allowed to do anything
        """
        for transaction in self.get_test_transactions():
            with self.assertRaises(PermissionDenied):
                transaction.revert(issuer=None)

    def test_revertUser(self):
        """
        Test revert of transaction with regular user (user=test1)
        """
        fresh, stale, foreign, reverted = self.get_test_transactions()

        fresh_reverted: Transaction = fresh.revert(issuer=self.user1)
        self.assertIsInstance(fresh_reverted, Transaction)
        self.assertIs(fresh_reverted.related_transaction, fresh)
        self.assertIs(fresh.related_transaction, fresh_reverted)

        with self.assertRaises(PermissionDenied):
            stale.revert(issuer=self.user1)
        with self.assertRaises(PermissionDenied):
            foreign.revert(issuer=self.user1)
        with self.assertRaises(Transaction.AlreadyReverted):
            reverted.revert(issuer=self.user1)
        
    def test_revertStaff(self):
        """
        Test revert of transaction with staff user(user=test_staff)
        """
        fresh, stale, foreign, reverted = self.get_test_transactions()

        fresh_reverted = fresh.revert(issuer=self.staffUser)
        self.assertIsInstance(fresh_reverted, Transaction)
        self.assertIs(fresh_reverted.related_transaction, fresh)
        self.assertIs(fresh.related_transaction, fresh_reverted)


        stale_reverted = stale.revert(issuer=self.staffUser)
        self.assertIsInstance(stale_reverted, Transaction)
        self.assertIs(stale_reverted.related_transaction, stale)
        self.assertIs(stale.related_transaction, stale_reverted)

        foreign_reverted = foreign.revert(issuer=self.staffUser)
        self.assertIsInstance(foreign_reverted, Transaction)
        self.assertIs(foreign_reverted.related_transaction, foreign)
        self.assertIs(foreign.related_transaction, foreign_reverted)

        with self.assertRaises(Transaction.AlreadyReverted):
            reverted.revert(issuer=self.staffUser)

    def test_revertIdempotencyKey(self):
        """
        Verify that passed data is indeed part of the created transaction
        """
        fresh_transaction: Transaction = Transaction.objects.create(
            **self.default_transaction,
            issuer=self.user1
        )
        
        reverted_transaction = fresh_transaction.revert(issuer=self.user1, idempotency_key=51)
        self.assertIsInstance(reverted_transaction, Transaction)
        self.assertIs(reverted_transaction.related_transaction, fresh_transaction)
        self.assertIs(fresh_transaction.related_transaction, reverted_transaction)

        self.assertEqual(reverted_transaction.idempotency_key, 51)

class ProductFormTest(TestCase):
    def test_createProduct(self):
        product_form = modelform_factory(Product, fields='__all__')

        form_data = {
            'full_name': 'Bierchen',
            'cost': '2',
            'member_cost': '1',
            'order': 0,
            'category': 'ATCL',
        }

        form = product_form(form_data)
        self.assertEqual(form.is_valid(), True)
        instance: Product = form.save()

        self.assertEqual(instance.member_cost, 100)

    def test_noMemberCost(self):
        product_form = modelform_factory(Product, fields='__all__')

        form_data = {
            'full_name': 'Bierchen',
            'cost': '2',
            'order': 0,
            'category': 'ATCL',
        }

        form = product_form(form_data)
        self.assertEqual(form.is_valid(), True)
        instance: Product = form.save()

        self.assertEqual(instance.member_cost, 200)

    def test_noneMemberCost(self):
        product_form = modelform_factory(Product, fields='__all__')
        
        form_data = {
            'full_name': 'Bierchen',
            'cost': '2',
            'member_cost': None,
            'order': 0,
            'category': 'ATCL',
        }

        form = product_form(form_data)
        
        self.assertEqual(form.is_valid(), True)
        instance: Product = form.save()

        self.assertEqual(instance.member_cost, 200)

    def test_invalidMemberCost(self):
        product_form = modelform_factory(Product, fields='__all__')

        form_data = {
            'full_name': 'Bierchen',
            'cost': '2',
            'member_cost': 'not_a_number',
            'order': 0,
            'category': 'ATCL',
        }

        form = product_form(form_data)
        self.assertEqual(form.is_valid(), False)

class TransactionEventTest(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(username='test')
        self.acc1: Account = Account.objects.create(display_name='acc1', credit=20_00, member=False)

        self.transactions = self.get_transactions()

    def get_transactions(self, count=5) -> list[Transaction]:
        kwargs = {
            'account': self.acc1,
            'amount': 50,
            'type': Transaction.TransactionType.ORDER,
            'reason': 'buy .50€',
            'issuer': None,
        }

        return [Transaction.objects.create(**kwargs) for _ in range(count)]

    async def test_connect_no_past(self):
        """
        Test that SSE clients DON'T reload if we dont know about their transaction past
        (query_param last_transaction missing)
        """

        client = AsyncClient()
        await client.aforce_login(self.user)
        response = await client.get(reverse('ledger:api:events'), follow=True, )

        await sync_to_async(send_event)(channel='transaction', event='dummy')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.streaming)

        events = []
        async for event in response.streaming_content:
            events.append(event)
            await sync_to_async(send_event)(channel='transaction', event='dummy')   
            if len(events) >= 2:
                break

        self.assertIn(b'event: open\n', events[0])
        self.assertNotIn(b'event: reload\n', events[1])
    
    async def test_connect_latest(self):
        """
        Test that SSE clients DON'T reload if they already have the latest transaction
        (query_param last_transaction == self.transactions[-1].pk)
        """
        client = AsyncClient()
        await client.aforce_login(self.user)
        response = await client.get(reverse('ledger:api:events'), follow=True, query_params={
            'last_transaction': self.transactions[-1].pk
        })


        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.streaming, True)

        events = []
        async for event in response.streaming_content:
            events.append(event)
            await sync_to_async(send_event)(channel='transaction', event='dummy')
            if len(events) >= 2:
                break

        self.assertIn(b'event: open\n', events[0])
        self.assertNotIn(b'event: reload\n', events[1])

    async def test_connect_not_latest(self):
        """
        Test that SSE clients DO reload if they don't have the latest transaction
        (query_param last_transaction != self.transactions[-1].pk)
        """
        client = AsyncClient()
        await client.aforce_login(self.user)
        response = await client.get(reverse('ledger:api:events'), follow=True, query_params={
            'last_transaction': self.transactions[-2].pk
        })

        await sync_to_async(send_event)(channel='transaction', event='dummy')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.streaming, True)

        events = []
        async for event in response.streaming_content:
            events.append(event)
            await sync_to_async(send_event)(channel='transaction', event='dummy')
            if len(events) >= 2:
                break
            
        self.assertIn(b'event: open\n', events[0])
        self.assertIn(b'event: reload\n', events[1])

    async def test_connect_invalid_latest(self):
        """
        Test that SSE clients DON'T reload if they sent an invalid latest transaction
        (query_param last_transaction not an int)
        """
        client = AsyncClient()
        await client.aforce_login(self.user)
        response = await client.get(reverse('ledger:api:events'), follow=True, query_params={
            'last_transaction': 'not_a_number'
        })

        await sync_to_async(send_event)(channel='transaction', event='dummy')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.streaming, True)

        events = []
        async for event in response.streaming_content:
            events.append(event)
            await sync_to_async(send_event)(channel='transaction', event='dummy')
            if len(events) >= 2:
                break
            
        self.assertIn(b'event: open\n', events[0])
        self.assertNotIn(b'event: reload\n', events[1])  

    async def test_connect_not_latest(self):
        """
        Test that SSE clients DO reload if they have a nonexisting (e.g. future) latest transaction
        (query_param last_transaction != self.transactions[-1].pk)
        """
        client = AsyncClient()
        await client.aforce_login(self.user)
        response = await client.get(reverse('ledger:api:events'), follow=True, query_params={
            'last_transaction': self.transactions[-1].pk + 3
        })

        await sync_to_async(send_event)(channel='transaction', event='dummy')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.streaming, True)

        events = []
        async for event in response.streaming_content:
            events.append(event)
            await sync_to_async(send_event)(channel='transaction', event='dummy')
            if len(events) >= 2:
                break
            
        self.assertIn(b'event: open\n', events[0])
        self.assertIn(b'event: reload\n', events[1])

class ApiViewTest(TestCase):
    """
    Test following URLs:
    - transaction/deposit/
    - transaction/withdraw/
    - transaction/order/
    - transaction/revert/
    - api/transaction/deposit/
    - api/transaction/withdraw/
    - api/transaction/order/
    - api/transaction/revert/
    for correct behavior under the following:
    - user not logged in
    - user missing permissions
    - user has permissions
    - superuser/staff
    - invalid data (form)
    - invalid data (nonexistent model instances)
    - revert logic
    - negative amounts
    - fraction amounts
    - amounts over budget
    - products out of budget
    - products within budget
    - products within budget for member
    - member ordering
    - withdraw within budget
    - withdraw out of budget
    - no reason provided
    """

class FormFieldTest(TestCase):
    class TestForm(Form):
        decimal = FixedPrecisionField(decimal_places=2)
    class TestForm2(Form):
        decimal = FixedPrecisionField(decimal_places=2, widget=NumberInput)

    def test_validPOST(self):
        values = [
            ('1', 100),
            ('0', 0),
            ('99999', 9999900),
            ('1.00', 100),
            ('1.01', 101),
            ('0.01', 1),
            ('0.00', 0),
            ('1,00', 100),
            ('1,0', 100),
            (',1', 10),
            ('.7', 70),
            ('-1', -100),
            ('-1.3', -130),
            ('-0.50', -50),
            ('-12,79', -1279),
        ]
        for (value, expected) in values:
            data = {'decimal': value}
            form = self.TestForm(data)
            self.assertTrue(form.is_valid(), f'Invalid for {value=}')
            self.assertEqual(form.cleaned_data['decimal'], expected, f'{form.cleaned_data["decimal"]=} not equal to {expected=} for {value=}')

    def test_validJSON(self):
        values = [
            (10, 1000),
            (10.00, 1000),
            (10.01, 1001),
            (-9.41, -941),
            (-12, -1200),
        ]
        for (value, expected) in values:
            data = {'decimal': value}
            form = self.TestForm(data)
            self.assertTrue(form.is_valid(), f'Invalid for {value=}')
            self.assertEqual(form.cleaned_data['decimal'], expected, f'{form.cleaned_data["decimal"]=} not equal to {expected=} for {value=}')

    def test_displayDecimalInput(self):
        SEP = get_format('DECIMAL_SEPARATOR')

        values: list[tuple[str, int]] = [
            ('1.00', 100),
            ('0.00', 0),
            ('99999.00', 9999900),
            ('1.00', 100),
            ('1.01', 101),
            ('0.01', 1),
            ('0.00', 0),
            ('1.00', 100),
            ('1.00', 100),
            ('0.10', 10),
            ('0.70', 70),
            ('-1.00', -100),
            ('-1.30', -130),
            ('-0.50', -50),
            ('-12.79', -1279),
        ]
        for (expected, value) in values:
            data = {'decimal': value}
            form = self.TestForm(initial=data)

            html = form.as_p()
            html_value = re.search(r'value="(.+?)"', str(html))
            self.assertIsNotNone(html_value, f"for {value=}")

            expected = expected.replace('.', SEP)
            html_value = html_value[1]
            self.assertEqual(expected, html_value, f"for {value=}")

    def test_displayNumericInput(self):
        values: list[tuple[str, int]] = [
            ('1', 100),
            ('0', 0),
            ('99999', 9999900),
            ('1.01', 101),
            ('0.01', 1),
            ('0', 0),
            ('0.10', 10),
            ('0.70', 70),
            ('-1', -100),
            ('-1.30', -130),
            ('-0.50', -50),
            ('-12.79', -1279),
        ]
        for (expected, value) in values:
            data = {'decimal': value}
            form = self.TestForm2(initial=data, )

            html = form.as_p()
            html_value = re.search(r'value="(.+?)"', str(html))
            self.assertIsNotNone(html_value, f"for {value=}")

            html_value = html_value[1]
            self.assertEqual(expected, html_value, f"for {value=}")
        
