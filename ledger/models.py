from typing import Any, Optional
from django.db import models, transaction
from django.contrib.auth.models import User
from .managers import TransactionManager, ProductManager
from .modelfield import PositiveFixedPrecisionField, FixedPrecisionField
from datetime import timedelta, datetime
from django.core.exceptions import PermissionDenied
# Create your models here.
# TODO : Better terminologiy regarding money:
# TODO : User A has amount k and additionally is allowed to go amount n into debt
# TODO : How to call k
# TODO : How to call n
# TODO : How to call k + n

class AccountGroup(models.Model):
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        db_index=True
    )
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']

class AccountManager(models.Manager):
    def grouped(self):
        return self.filter(active=True)\
            .order_by(models.F("group__order").asc(nulls_first=True), 'name')\
            .annotate(
                _last_balance=models.functions.Coalesce(models.Subquery(
                    AccountBalance.objects\
                        .filter(account=models.OuterRef('pk'))\
                        .order_by('-timestamp')\
                        .values_list('closing_balance', flat=True)[:1]),
                    models.Value(0)),
                _summed_transactions=models.functions.Coalesce(models.Subquery(
                    Transaction.objects\
                        .filter(closing_balance=None, account=models.OuterRef('pk'))\
                        .values('account__pk')\
                        .annotate(sum=models.Sum('amount', default=0))\
                        .values('sum')),
                    models.Value(0))
            )\
            .select_related('group')

class Account(models.Model):
    class NotEnoughFunds(Exception): pass
    
    objects = AccountManager()

    name = models.CharField(max_length=255)
    credit = PositiveFixedPrecisionField(decimal_places=2)
    member = models.BooleanField()
    active = models.BooleanField(default=True)
    
    permanent = models.BooleanField(default=False)

    group = models.ForeignKey(AccountGroup, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    
    # Forward declaration for type-hinting
    transactions: models.QuerySet["Transaction"]
    balances: models.QuerySet["AccountBalance"]

    class Meta:
        ordering = ['group', 'name']
        permissions = [
            ('add_permanent_account', 'Can add permanent accounts'),
            ('change_permanent_account', 'Can change permanent accounts'),
        ]
        indexes = [
            models.Index('active', models.F('group').asc(nulls_first=True), 'name', name='idx_grouped_accounts'),
            models.Index('active', name='idx_active_account'),
        ]

    def __str__(self) -> str:
        return self.name
    
    @property
    def last_balance(self) -> Optional["AccountBalance"]:
        return self.balances.order_by('-timestamp').first()

    @property
    @transaction.atomic
    def current_balance(self) -> int:
        if hasattr(self, '_last_balance'):
            last_balance = self._last_balance
            print(f'Hit cached last_balance: {self._last_balance}')
        else:
            last_balance = self.last_balance
            last_balance = last_balance.closing_balance if last_balance is not None else 0
        if hasattr(self, '_summed_transactions'):
            transactions_since = self._summed_transactions
            print(f'Hit cached summed_transactions: {self._summed_transactions}')
        else:
            transactions_since = self.transactions  \
                .filter(closing_balance=None)       \
                .aggregate(sum=models.Sum('amount', default=0)) \
                ['sum']

        return last_balance + transactions_since
    
    @property
    def current_budget(self) -> int:
        return self.current_balance + self.credit

    @property
    def is_liquid(self) -> bool:
        return self.current_budget > 0
    
    @transaction.atomic
    def close_balance(self):
        # TODO : New closing balance only if things changed
        # got_transactions = self.transactions.filter(closing_balance=None).exists()
        closing_balance = AccountBalance.objects.create(account=self, closing_balance=self.current_balance)
        self.transactions.filter(closing_balance=None).update(closing_balance=closing_balance)

class AccountBalance(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='balances')
    timestamp = models.DateTimeField(auto_now_add=True)
    closing_balance = FixedPrecisionField(decimal_places=2)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"{self.account} at {self.timestamp}"

class Transaction(models.Model):
    class AlreadyReverted(Exception): pass

    objects = TransactionManager(
        timejump_threshold=timedelta(hours=6),
        revert_threshold=timedelta(hours=12))

    closing_balance = models.ForeignKey(AccountBalance, on_delete=models.CASCADE, related_name='transactions', null=True, default=None, blank=True)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name='transactions')
    amount = FixedPrecisionField(decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255)
    issuer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    related_transaction: "Transaction" = models.OneToOneField(to="self", on_delete=models.CASCADE, null=True, default=None, blank=True)

    idempotency_key: str | None

    class Meta:
        permissions = [
            ('add_custom_transaction', 'Can make arbitrary deposits and withdrawls'),
            ('add_permanent_custom_transaction', 'Can make arbitrary deposits and withdrawls for permanent accounts'),
        ]
        indexes = [
            models.Index('closing_balance', models.F('timestamp').desc(), name="idx_recent_transactions"),
            models.Index('closing_balance', name='idx_balance_transaction'),
        ]

    def __init__(self, *args: Any, idempotency_key=None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.idempotency_key = idempotency_key

    def __str__(self) -> str:
        return f"Transaction {self.account.name}"
    
    @property
    def can_revert(self) -> bool:
        return self.related_transaction == None
    
    def user_can_revert(self, user: User | None) -> bool:
        has_permissions = user.is_staff or (user == self.issuer and datetime.now() - self.timestamp < self.objects.revert_threshold)
        return has_permissions

    @transaction.atomic
    def revert(self, issuer: User | None):
        if not self.can_revert:
            return Transaction.AlreadyReverted()
        
        if not self.user_can_revert(issuer):
            return PermissionDenied()        
        
        revert_transaction = Transaction.objects.create(
            account=self.account,
            amount=-self.amount,
            reason=f"Storno: {self.reason}",
            issuer=issuer,
            related_transaction=self
        )
        self.related_transaction = revert_transaction
        self.save()

class ProductGroup(models.Model):
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order']

class Product(models.Model):
    objects = ProductManager()

    name = models.CharField(max_length=255)
    cost = PositiveFixedPrecisionField(decimal_places=2)
    member_cost = PositiveFixedPrecisionField(decimal_places=2, blank=True)
    
    group = models.ForeignKey(ProductGroup, on_delete=models.SET_NULL, null=True, default=None, blank=True)
    order = models.PositiveIntegerField(
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    class Meta:
        ordering = ['group', 'order']
        indexes = [
            models.Index(models.F('group').asc(nulls_first=True), 'order', name="idx_grouped_products")
        ]

    def __str__(self) -> str:
        return self.name
    
    def clean(self) -> None:
        if self.member_cost is None:
            self.member_cost = self.cost


# https://stackoverflow.com/questions/29688982/derived-account-balance-vs-stored-account-balance-for-a-simple-bank-account/29713230#29713230
