from typing import Any, Optional, Type
from django.db import models, transaction
from django.utils.timezone import now
from .managers import TransactionManager, ProductManager, TransactionQuerySet
from .modelfield import PositiveFixedPrecisionField, FixedPrecisionField
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.utils.formats import get_format
from django.utils.translation import gettext, override as override_language, gettext_lazy as _, pgettext_lazy
from django.conf import settings
from django.contrib.admin import display
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth import get_user_model
# Create your models here.
# TODO : Better terminologiy regarding money:
# TODO : User A has amount k and additionally is allowed to go amount n into debt
# TODO : How to call k
# TODO : How to call n
# TODO : How to call k + n

UserModel: Type[AbstractBaseUser] = get_user_model()

class AccountGroup(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )
    
    def __str__(self):
        return self.name

    class Meta:
        ordering = ['order']
        verbose_name = _('account group')
        verbose_name_plural = _('account groups')

class AccountManager(models.Manager):
    def grouped(self):
        return self.filter(active=True)\
            .order_by(models.F("group__order").asc(nulls_first=True), 'display_name')\
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
                        .annotate(sum=
                            models.Sum('amount', filter= ~models.Q(type__in=Transaction.TransactionType.withdraws()), default=0) \
                            - models.Sum('amount', filter=models.Q(type__in=Transaction.TransactionType.withdraws()), default=0))\
                        .values('sum')),
                    models.Value(0))
            )\
            .select_related('group')

class Account(models.Model):
    class NotEnoughFunds(Exception): pass
    
    objects = AccountManager()

    display_name = models.CharField(verbose_name=_('display name'), max_length=255)
    full_name = models.CharField(verbose_name=_('full name'), max_length=255, default='', blank=True)
    credit = PositiveFixedPrecisionField(verbose_name=_('credit'), decimal_places=2, default=0)
    group = models.ForeignKey(AccountGroup, verbose_name=_('group'), on_delete=models.SET_NULL, null=True, default=None, blank=True)
    
    member = models.BooleanField(verbose_name=_('member'))
    permanent = models.BooleanField(verbose_name=_('permanent'), default=False)

    active = models.BooleanField(verbose_name=_('active'), default=True)
    
    # Forward declaration for type-hinting
    transactions: models.QuerySet["Transaction"]
    balances: models.QuerySet["AccountBalance"]

    class Meta:
        ordering = ['group', 'display_name']
        permissions = [
            ('add_permanent_account', 'Can add permanent accounts'),
            ('change_permanent_account', 'Can change permanent accounts'),
        ]
        indexes = [
            models.Index('active', models.F('group').asc(), 'display_name', name='idx_grouped_accounts'),
            models.Index('active', name='idx_active_account'),
        ]
        verbose_name = _('account')
        verbose_name_plural = _('accounts')

    def __str__(self) -> str:
        return self.display_name
    
    @property
    @display(description=_('Last closing balance'))
    def last_balance(self) -> Optional["AccountBalance"]:
        return self.balances.order_by('-timestamp').first()

    @property
    @display(description=_('Balance'))
    @transaction.atomic
    def current_balance(self) -> int:
        if hasattr(self, '_last_balance'):
            last_balance = self._last_balance
        else:
            last_balance = self.last_balance
            last_balance = last_balance.closing_balance if last_balance is not None else 0
        if hasattr(self, '_summed_transactions'):
            transactions_since = self._summed_transactions
        else:
            transactions_since = self.transactions  \
                .filter(closing_balance=None)       \
                .aggregate(sum=
                    models.Sum('amount', filter= ~models.Q(type__in=Transaction.TransactionType.withdraws()), default=0) \
                    - models.Sum('amount', filter=models.Q(type__in=Transaction.TransactionType.withdraws()), default=0)) \
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
    account = models.ForeignKey(Account, verbose_name=_('account'), on_delete=models.CASCADE, related_name='balances')
    timestamp = models.DateTimeField(verbose_name=_('timestamp'), auto_now_add=True)
    closing_balance = FixedPrecisionField(verbose_name=_('closing balance'), decimal_places=2)
    previous_balance = models.OneToOneField("self", verbose_name=_('previous balance'), on_delete=models.CASCADE, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _('account balance')
        verbose_name_plural = _('account balances')

    def __str__(self) -> str:
        return gettext("{account}: {closing_balance} at {timestamp}").format(account=self.account, closing_balance=self.closing_balance, timestamp=self.timestamp)

config = settings.LEDGER_CONFIG['transaction']
class Transaction(models.Model):
    class AlreadyReverted(Exception): pass
    class TransactionType(models.TextChoices):
        DEPOSIT = 'DEPT', _('Deposit')
        WITHDRAW = 'WDRW', _('Withdraw')
        ORDER = 'ORDR', pgettext_lazy('verb, getting a product', 'Order')
        REVERT_DEPOSIT = 'RVDP', _('Revert-Deposit')
        REVERT_WITHDRAW = 'RVWD', _('Revert-Withdraw')

        @classmethod
        def withdraws(cls) -> set["Transaction.TransactionType"]:
            return {cls.ORDER, cls.WITHDRAW, cls.REVERT_WITHDRAW}

    revert_threshold = timedelta(hours=config['revert-threshold'])
    timejump_threshold = timedelta(hours=config['timejump-threshold'])
    objects: TransactionManager = TransactionQuerySet.as_manager()

    closing_balance = models.ForeignKey(AccountBalance, verbose_name=_('closing balance'), on_delete=models.CASCADE, related_name='transactions', null=True, default=None, blank=True)
    account = models.ForeignKey(Account, verbose_name=_('account'), on_delete=models.CASCADE, related_name='transactions')
    amount = PositiveFixedPrecisionField(verbose_name=pgettext_lazy('money-related', 'amount'), decimal_places=2)
    timestamp = models.DateTimeField(verbose_name=_('timestamp'), auto_now_add=True)
    reason = models.CharField(verbose_name=_('reason'), max_length=255)
    issuer = models.ForeignKey(UserModel, verbose_name=_('issuer'), on_delete=models.SET_NULL, null=True)
    
    type = models.CharField(verbose_name=pgettext_lazy('transaction', 'type'), max_length=4, choices=TransactionType.choices)

    extra = models.JSONField(verbose_name=_('extra'), default=dict, blank=True)
    
    related_transaction: "Transaction" = models.OneToOneField(to="self", verbose_name=_('related transaction'), help_text=_('Used to track and associate canceled transactions'), on_delete=models.CASCADE, null=True, default=None, blank=True)

    idempotency_key: str | None

    class Meta:
        permissions = [
            ('add_deposit_transaction', 'Can make arbitrary deposits'),
            ('add_permanent_deposit_transaction', 'Can make arbitrary deposits for permanent accounts'),
            ('add_withdraw_transaction', 'Can make arbitrary withdrawls'),
            ('add_permanent_withdraw_transaction', 'Can make arbitrary withdrawls for permanent accounts'),
        ]
        indexes = [
            models.Index('closing_balance', models.F('timestamp').desc(), name="idx_recent_transactions"),
            models.Index('closing_balance', name='idx_balance_transaction'),
        ]
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')

    def __init__(self, *args: Any, idempotency_key=None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.idempotency_key = idempotency_key

    def __str__(self) -> str:
        amount_str = str(self.amount)
        wholes, cents = amount_str[:-2], amount_str[-2:]
        return f"{self.account.display_name}: {self.reason} ({wholes:>01},{cents:>02}€)"

    @property
    @display(description=_('Amount'))
    def formatted_amount(self) -> str:
        amount_str = str(self.amount).rjust(self.__class__._meta.get_field('amount').decimal_places + 1, '0')
        wholes, cents = amount_str[:-2], amount_str[-2:]
        decimal_separator = get_format('DECIMAL_SEPARATOR')
        sign = '-' if self.type in self.TransactionType.withdraws() else ''
        return f"{sign}{wholes}{decimal_separator}{cents}"

    @property
    @display(description=_('Signed amount'))
    def normalized_amount(self) -> int:
        return -self.amount if self.type in self.TransactionType.withdraws() else self.amount

    @property
    def can_revert(self) -> bool:
       return self.related_transaction is None
    
    def user_can_revert(self, user: UserModel | None) -> bool:
        if user is None:
            return False
    
        is_stale = now() - self.timestamp >= self.revert_threshold
        has_permissions = user.is_staff or (user == self.issuer and not is_stale)
        return has_permissions

    @transaction.atomic
    def revert(self, issuer: UserModel | None, idempotency_key=None) -> "Transaction":
        if not self.user_can_revert(issuer):
            raise PermissionDenied()
        
        if not self.can_revert:
            raise Transaction.AlreadyReverted()
        
        with override_language(settings.LANGUAGE_CODE):
            revert_prefix = gettext('Canceled')

        revert_type = self.TransactionType.REVERT_DEPOSIT if self.type in self.TransactionType.withdraws() else self.TransactionType.REVERT_WITHDRAW

        revert_transaction = Transaction.objects.create(
            account=self.account,
            amount=self.amount,
            reason=f"{revert_prefix}: {self.reason}",
            issuer=issuer,
            related_transaction=self,
            type=revert_type,
            idempotency_key=idempotency_key
        )
        self.related_transaction = revert_transaction
        self.save()
        return revert_transaction

class ProductGroup(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=255)
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['order']
        verbose_name = _('product group')
        verbose_name_plural = _('product groups')

class Product(models.Model):
    objects = ProductManager()

    name = models.CharField(verbose_name=_('name'), max_length=255)
    cost = PositiveFixedPrecisionField(verbose_name=_('cost'), decimal_places=2)
    member_cost = PositiveFixedPrecisionField(verbose_name=_('member cost'), decimal_places=2, blank=True)
    visible = models.BooleanField(verbose_name=_('visible'), default=True)
    
    group = models.ForeignKey(ProductGroup, verbose_name=_('group'), on_delete=models.SET_NULL, null=True, default=None, blank=True)
    order = models.PositiveIntegerField(
        verbose_name=_('order'),
        default=0,
        blank=False,
        null=False,
        db_index=True
    )

    class Meta:
        ordering = ['group', 'order']
        indexes = [
            models.Index(models.F('group'), 'order', name="idx_grouped_products")
        ]
        verbose_name = _('product')
        verbose_name_plural = _('products')

    def __str__(self) -> str:
        return self.name
    
    def clean(self) -> None:
        if self.member_cost is None:
            self.member_cost = self.cost


# https://stackoverflow.com/questions/29688982/derived-account-balance-vs-stored-account-balance-for-a-simple-bank-account/29713230#29713230
        
