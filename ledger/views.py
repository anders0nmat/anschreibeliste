from typing import Any, Dict, Literal
from http import HTTPStatus
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, HttpResponseForbidden, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView, CreateView, TemplateView, View

from time import time_ns
from json import loads

from .decorators import idempotent, json_body
from .eventstream import send_event, EventstreamResponse, StreamEvent
from .mixins import EnableFieldsMixin
from .models import Account, Transaction, Product
from .forms import AccountForm, TransactionForm, ProductTransactionForm, RevertTransactionForm


def api_object() -> dict[str, Any]:
    return {
        'deposit': reverse('api_deposit'),
        'withdraw': reverse('api_withdraw'),
        'order': reverse('api_order'),
        'revert': reverse('api_revert'),
        'events': reverse('api_events'),
    }

class AccountList(ListView):
    queryset = Account.objects.grouped()

class AccountDetail(EnableFieldsMixin, UpdateView):
    model = Account
    form_class = AccountForm
    object: Account # Type Annotation for IDE
    template_name_suffix = '_detail'
    
    def get_success_url(self) -> str:
        return reverse('account_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        custom_transaction_permission = 'ledger.add_permanent_custom_transaction' if self.object.permanent else 'ledger.add_custom_transaction'

        kwargs |= {
            'account_list': Account.objects.grouped(),
            'transactions': Transaction.objects.recent(account=self.object, user=self.request.user),
            'allow_custom_transaction': self.request.user.has_perm(custom_transaction_permission),
            'deposit_form': TransactionForm(initial={'account': self.object, 'action': 'deposit'}),
            'withdraw_form': TransactionForm(initial={'account': self.object, 'action': 'withdraw'}),
            'api': api_object(),
        }
        return super().get_context_data(**kwargs)
    
    def get_disabled_fields(self) -> list[str] | Literal['__all__']:
        account_is_permanent = self.object.permanent
        user_can_edit_temporary = self.request.user.has_perm('ledger.change_account')
        user_can_edit_permanent = self.request.user.has_perm('ledger.change_permanent_account')

        if user_can_edit_permanent:
            return []
        elif account_is_permanent and user_can_edit_permanent:
            return ['permanent']
        elif not account_is_permanent and user_can_edit_temporary:
            return ['member', 'permanent']
        else:
            return '__all__'

class AccountCreate(PermissionRequiredMixin, EnableFieldsMixin, CreateView):
    model = Account
    object: Account # Type Annotation for IDE
    form_class = AccountForm
    template_name_suffix = '_create'
    initial = {
        'member': False,
        'credit': 0,
    }

    def has_permission(self) -> bool:
        return self.request.user.has_perm('ledger.add_account') or self.request.user.has_perm('ledger.add_permanent_account')

    def get_initial(self) -> Dict[str, Any]:
        return super().get_initial() | {
            'permanent': self.request.user.has_perm('ledger.add_permanent_account') and not self.request.user.has_perm('ledger.add_account')
        }
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            'account_list': Account.objects.grouped(),
        }

    def get_success_url(self) -> str:
        return reverse('account_detail', args=[self.object.pk])

    def get_disabled_fields(self) -> list[str]:
        user_can_add = self.request.user.has_perm('ledger.add_account')
        user_can_add_permanent = self.request.user.has_perm('ledger.add_permanent_account')

        if user_can_add and user_can_add_permanent:
            return []
        elif user_can_add_permanent:
            return ['permanent']
        else:
            return ['member', 'permanent']

class IndexView(TemplateView):
    template_name = "ledger/main.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            "account_list": Account.objects.grouped(),
            "product_list": Product.objects.grouped(),
            "transaction_list": Transaction.objects.recent(user=self.request.user),
            'api': api_object(),
        }


def test(request: HttpRequest):
    return render(request, "ledger/test.html", {
        "accounts": Account.objects.grouped(),
        "products": Product.objects.grouped(),
        "transactions": Transaction.objects.recent(),
    })

@require_POST
@permission_required(["ledger.add_transaction"], raise_exception=True)
@idempotent(required=True, post_field='idempotency_key')
def yyproduct_transaction(request: HttpRequest):
    try:
        if request.content_type == 'application/json':
            data = loads(request.body)
        else:
            data = request.POST

        form = ProductTransactionForm(data)
        if not form.is_valid():
            raise ValidationError('')

        account: Account = form.cleaned_data['account']
        product: Product = form.cleaned_data['product']
        amount: int = form.cleaned_data['amount']

        price = product.cost
        if account.member:
            price = product.member_cost

        price *= amount

        if account.current_budget < price:
            raise Account.NotEnoughFunds()
        
        reason = product.name
        if amount > 1:
            reason = f'{amount}x {reason}'

        new_transaction: Transaction = Transaction.objects.create(
            account=account,
            amount=-price,
            reason=reason,
            issuer=request.user,
            idempotency_key=request.idempotency_key)
        
        if request.accepts('text/html'):
            return HttpResponseRedirect(reverse('main'))
        else:
            return JsonResponse({'transaction_id': new_transaction.pk})
    except (Account.DoesNotExist, Product.DoesNotExist):
        return HttpResponseNotFound("Invalid account or product")
    except Account.NotEnoughFunds:
        return HttpResponseForbidden("Not enough budget")
    except ValidationError as e:
        return HttpResponseBadRequest(f'Invalid http form: {form.errors}')


@idempotent(required=True, post_field='idempotency-key')
def _product_transaction(request: HttpRequest, form: ProductTransactionForm) -> Transaction | None:
    if form.is_valid():
        try:
            account: Account = form.cleaned_data['account']
            product: Product = form.cleaned_data['product']
            amount: int = form.cleaned_data['amount']

            price = product.member_cost if account.member else product.cost
            price *= amount

            if account.current_budget < price:
                raise ValidationError('The account has not enough money', code='out_of_money')
            
            reason = product.name
            if amount > 1:
                reason = f'{amount}x {reason}'

            return Transaction.objects.create(
                account=account,
                amount=-price,
                reason=reason,
                issuer=request.user,
                idempotency_key=request.idempotency_key)
        except ValidationError as error:
            form.add_error(None, error)
    return None

@idempotent(required=True, post_field='idempotency-key')
def _custom_transaction(request: HttpRequest, form: TransactionForm, action: Literal['deposit', 'withdraw']) -> Transaction | None:
    if form.is_valid():
        try:
            account: Account = form.cleaned_data['account']
            amount: int = form.cleaned_data['amount']
            reason: str = form.cleaned_data['reason']

            required_permission = 'ledger.add_permanent_custom_transaction' if account.permanent else 'ledger.add_custom_transaction'
            if not request.user.has_perm(required_permission):
                raise ValidationError('Not authorized to withdraw from this account', code='user_permission')
            
            if not reason:
                amount_str = str(amount)
                wholes, cents = amount_str[:-2], amount_str[-2:]
                reason = f"{action.capitalize()}: {wholes},{cents}€"

            if action == 'withdraw':
                amount = -amount
                if account.current_budget + amount < 0:
                    raise ValidationError('The account has not enough money', code='out_of_money')

            return Transaction.objects.create(
                account=account,
                amount=amount,
                reason=reason,
                issuer=request.user,
                idempotency_key=request.idempotency_key)
        except ValidationError as error:
            form.add_error(None, error)

@idempotent(required=True, post_field='idempotency-key')
def _revert_transaction(request: HttpRequest, form: RevertTransactionForm) -> Transaction | None:
    if form.is_valid():
        transaction: Transaction = form.cleaned_data['transaction']
        try:
            return transaction.revert(issuer=request.user, idempotency_key=request.idempotency_key)
        except Transaction.AlreadyReverted:
            form.add_error(None, ValidationError('Transaction already reverted', code='already_reverted'))
        except PermissionDenied:
            form.add_error(None, ValidationError('Not authorized to revert this transaction', code='user_permission'))        
    return None


@require_POST
@permission_required('ledger.add_transaction', raise_exception=True)
def product_transaction(request: HttpRequest):
    form = ProductTransactionForm(request.POST)

    if _product_transaction(request, form):
        return HttpResponseRedirect(reverse('main'))

    return HttpResponseBadRequest(form.errors.as_ul())

@require_POST
@permission_required('ledger.add_transaction', raise_exception=True)
def product_transaction_ajax(request: HttpRequest):
    try:
        data = loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
    
    form = ProductTransactionForm(data)

    new_transaction = _product_transaction(request, form)
    if new_transaction:
        return JsonResponse({"transaction_id": new_transaction.pk})

    return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)

@require_POST
def custom_transaction(request: HttpRequest, action: Literal['deposit', 'withdraw']):
    form = TransactionForm(request.POST)
    new_transaction = _custom_transaction(request, form, action)
    if new_transaction:
        return HttpResponseRedirect(reverse('account_detail', kwargs={"pk": new_transaction.account.pk}))
        
    return HttpResponseBadRequest(form.errors.as_ul())

@require_POST
def custom_transaction_ajax(request: HttpRequest, action: Literal['deposit', 'withdraw']):
    try:
        data = loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
    
    form = TransactionForm(data)

    new_transaction = _custom_transaction(request, form, action)
    if new_transaction:
        return JsonResponse({"transaction_id": new_transaction.pk})

    return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)

@require_POST
def revert_transaction(request: HttpRequest):
    form = RevertTransactionForm(request.POST)
    if _revert_transaction(request, form):
        return HttpResponseRedirect(reverse('main'))
    return HttpResponseBadRequest(form.errors.as_ul())

@require_POST
def revert_transaction_ajax(request: HttpRequest):
    try:
        data = loads(request.body)
    except:
        return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
    
    form = RevertTransactionForm(data)
    new_transaction = _revert_transaction(request, form)
    if new_transaction:
        return JsonResponse({"transaction_id": new_transaction.pk})

    return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)


@require_POST
@idempotent(required=True, post_field='idempotency_key')
def yycustom_transaction(request: HttpRequest):
    try:		
        if request.content_type == 'application/json':
            data = loads(request.body)
        else:
            data = request.POST

        form = TransactionForm(data)
        if not form.is_valid():
            raise ValidationError('')

        action = form.cleaned_data['action']
        account = form.cleaned_data['account']
        amount = form.cleaned_data['amount']
        reason = form.cleaned_data['reason']
        
        required_permission = "ledger.add_permanent_custom_transaction" if account.permanent else "ledger.add_custom_transaction"		
        if not request.user.has_perm(required_permission):
            raise PermissionDenied()
        
        if not reason:
            amount_str = str(amount)
            wholes, cents = amount_str[:-2], amount_str[-2:]
            reason = f"{action.capitalize()}: {wholes},{cents}€"

        if action == 'withdraw':
            amount = -amount

        if amount + account.current_budget < 0:
            raise Account.NotEnoughFunds()

        new_transaction = Transaction.objects.create(
            account=account,
            amount=amount,
            reason=reason,
            issuer=request.user,
            idempotency_key=request.idempotency_key)
        
        if request.accepts('text/html'):
            return HttpResponseRedirect(reverse('account_detail', args=[account.pk]))
        else:
            return JsonResponse({'transaction_id': new_transaction.pk})
    except ValidationError:
        return HttpResponseBadRequest("Invalid form submission: " + form.errors.as_text())
    except Account.DoesNotExist:
        return HttpResponseNotFound("Invalid account")
    except Account.NotEnoughFunds:
        return HttpResponseForbidden("Not enough budget")
    
@require_POST
@idempotent(post_field='idempotency_key')
def test_custom_transaction(request: HttpRequest, account: int, action: Literal['withdraw', 'deposit']):
    try:		
        account: Account = Account.objects.get(pk=account, active=True)

        required_permission = "ledger.add_permanent_custom_transaction" if account.permanent else "ledger.add_custom_transaction"		
        if not request.user.has_perm(required_permission):
            raise PermissionDenied()
        
        form = AccountTransactionForm(request.POST)
        if not form.is_valid():
            raise ValidationError('')
        
        amount = form.cleaned_data['amount']
        reason = form.cleaned_data['reason']
        if not reason:
            amount_str = str(amount)
            wholes, cents = amount_str[:-2], amount_str[-2:]
            reason = f"{action.capitalize()}: {wholes},{cents}€"

        if action == 'withdraw':
            amount = -amount

        if amount + account.current_budget < 0:
            raise Account.NotEnoughFunds()

        new_transaction = Transaction.objects.create(
            account=account,
            amount=amount,
            reason=reason,
            issuer=request.user,
            idempotency_key=request.idempotency_key)
        
        #return JsonResponse({"transaction_id": new_transaction.pk})
        return HttpResponseRedirect(reverse('test_detail', args=[account.pk]))
    except Account.DoesNotExist:
        return HttpResponseNotFound("Invalid account")
    except Account.NotEnoughFunds:
        return HttpResponseForbidden("Not enough budget")

@require_POST
@permission_required(["ledger.add_transaction"], raise_exception=True)
@idempotent
def test_product_transaction(request: HttpRequest, account: int, product: int, amount: int = 1):
    try:
        account: Account = Account.objects.get(pk=account, active=True)
        product: Product = Product.objects.get(pk=product)

        price = product.cost
        if account.member:
            price = product.member_cost

        price *= amount

        if account.current_budget < price:
            raise Account.NotEnoughFunds()
        
        reason = product.name
        if amount > 1:
            reason = f'{amount}x {reason}'

        new_transaction = Transaction.objects.create(
            account=account,
            amount=-price,
            reason=reason,
            issuer=request.user,
            idempotency_key=request.idempotency_key)
        
        return HttpResponseRedirect(reverse('main'))
    except (Account.DoesNotExist, Product.DoesNotExist):
        return HttpResponseNotFound("Invalid account or product")
    except Account.NotEnoughFunds:
        return HttpResponseForbidden("Not enough budget")

@require_POST
@permission_required(["ledger.add_transaction"], raise_exception=True)
@idempotent
@json_body(patterns=[("transaction", int)])
def yyrevert_transaction(request: HttpRequest, transaction: int):
    try:
        transaction: Transaction = Transaction.objects.get(pk=transaction)
        transaction.revert(issuer=request.user)
        return HttpResponse(status=HTTPStatus.NO_CONTENT)
    except Transaction.DoesNotExist:
        return HttpResponseNotFound("Invalid transaction")
    except Transaction.AlreadyReverted:
        return HttpResponse('Already reverted', status=HTTPStatus.CONFLICT)

def transaction_events(request: HttpRequest):
    initial_event = None

    latest_client_transaction_id = request.GET.get('last_transaction', None)
    if latest_client_transaction_id:
        try:
            latest_client_transaction_id = int(latest_client_transaction_id)
            latest_transaction: Transaction = Transaction.objects.latest('timestamp')
            if latest_client_transaction_id != latest_transaction.pk:
                # client has not the latest transactions
                # -> command client to reload page
                initial_event = StreamEvent(event='reload')
        except (ValueError, Transaction.DoesNotExist):
            pass

    return EventstreamResponse(channel='transaction', initial_event=initial_event)


def send(request: HttpRequest):
    counter = request.GET.get('counter', 0)
    send_event('counter', None, {'server': 'hello', 'counter': counter})
    return HttpResponse('ok')

def event(request):
    return EventstreamResponse('counter')
