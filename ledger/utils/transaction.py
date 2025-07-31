from typing import Literal
from django.utils.translation import gettext as _, pgettext
from ..models import Transaction, Account, Product, UserModel

from django.core.exceptions import PermissionDenied

from . import server_language

def order_product(account: Account, product: Product, issuer: UserModel, amount=1, invert_member_status=False, extra_data={}) -> Transaction:
    if not isinstance(account, Account):
        raise TypeError(f'expected `account` to be Account, is {type(account)}')
    if not isinstance(product, Product):
        raise TypeError(f'expected `product` to be Product, is {type(account)}')
    
    if not isinstance(amount, int):
        raise TypeError(f'expected `amount` to be int, is {type(amount)}')
    if amount < 1:
        raise ValueError(f"amount has to be >= 1, is {amount}")
    
    member_status = account.member != invert_member_status
    price = product.member_cost if member_status else product.cost
    
    price *= amount

    if account.current_budget < price:
        raise Account.NotEnoughFunds()
    
    with server_language():
        reason = product.name
        if amount > 1:
            reason = _("{amount}x {product}").format(amount=amount, product=reason)
        if invert_member_status:
            if account.member:
                # Translators: Used as transaction reason if a member buys something on behalf of a non-member
                reason = _("For extern: {reason}").format(reason=reason)
            else:
                # Translators: Used as transaction reason if a non-member buys something on behalf of a member
                reason = _("For intern: {reason}").format(reason=reason)
    
    return Transaction.objects.create(
        account=account,
        amount=price,
        reason=reason,
        issuer=issuer,
        type=Transaction.TransactionType.ORDER,
        extra={
            'product': product.pk,
            'amount': amount,
        },
        **extra_data
    )

def custom_transaction(account: Account, amount: int, action: Literal['deposit', 'withdraw'], issuer: UserModel, reason="", extra_data={}) -> Transaction:
    if not isinstance(account, Account):
        raise TypeError(f'expected `account` to be Account, is {type(account)}')
    if action not in ('deposit', 'withdraw'):
        raise ValueError(f"expected `action` to be one of ('deposit', 'withdraw'), is {action}")
    
    if not isinstance(amount, int):
        raise TypeError(f'expected `amount` to be int, is {type(amount)}')
    if amount < 1:
        raise ValueError(f"amount has to be >= 1, is {amount}")
    
    PERMISSION = {
    #   (action, permanent): permission_name
        ('deposit', False): 'ledger.add_deposit_transaction',
        ('withdraw', False): 'ledger.add_withdraw_transaction',
        ('deposit', True): 'ledger.add_permanent_deposit_transaction',
        ('withdraw', True): 'ledger.add_permanent_withdraw_transaction',
    }
    if not issuer.has_perm(PERMISSION[(action, account.permanent)]):
        raise PermissionDenied()
    
    if not reason:
        with server_language():
            if action == 'deposit':
                reason = pgettext('Default transaction reason', 'Deposit')
            else:
                reason = pgettext('Default transaction reason', 'Withdraw')

    if action == 'withdraw' and account.current_budget < amount:
        raise Account.NotEnoughFunds()
    
    return Transaction.objects.create(
        account=account,
        amount=amount,
        reason=reason,
        issuer=issuer,
        type=Transaction.TransactionType.DEPOSIT if action == 'deposit' else Transaction.TransactionType.WITHDRAW,
        **extra_data
    )
    
def transaction_event(instance: Transaction) -> dict:
    data = {
        "id": instance.pk,
        "account": instance.account.pk,
        "account_name": instance.account.display_name,
        "balance": instance.account.current_balance,
        "amount": instance.normalized_amount,
        "reason": instance.reason,
    }
    # Reversal transaction
    if instance.related_transaction is not None:
        data["related"] = instance.related_transaction.pk
    
    # Associate transaction with request
    if instance.idempotency_key is not None:
        data["idempotency_key"] = instance.idempotency_key
                
    return data
            

