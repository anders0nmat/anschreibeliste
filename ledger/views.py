from typing import Any, Dict, Literal
from http import HTTPStatus
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpRequest, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView, CreateView, TemplateView
from json import loads
from django.utils.translation import gettext as _, override as override_language
from django.conf import settings

from .decorators import idempotent
from .eventstream import EventstreamResponse, StreamEvent
from .mixins import EnableFieldsMixin
from .models import Account, Transaction, Product
from .forms import AccountForm, TransactionForm, ProductTransactionForm, RevertTransactionForm
from . import config


def js_config() -> dict[str, Any]:
    return {
        'transaction': {
            'deposit': reverse('api_deposit'),
            'withdraw': reverse('api_withdraw'),
            'order': reverse('api_order'),
            'revert': reverse('api_revert'),
            'events': reverse('api_events'),
        },
        'transaction_timeout': config.TRANSACTION_TIMEOUT,
        'submit_overlay': config.SUBMIT_OVERLAY,
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
            'js_config': js_config(),
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
            'js_config': js_config(),
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
            'js_config': js_config(),
        }


def test(request: HttpRequest):
    return render(request, "ledger/test.html", {
        "accounts": Account.objects.grouped(),
        "products": Product.objects.grouped(),
        "transactions": Transaction.objects.recent(),
        'js_config': js_config(),
    })


@idempotent(required=True, post_field='idempotency-key')
def _product_transaction(request: HttpRequest, form: ProductTransactionForm) -> Transaction | None:
    if form.is_valid():
        try:
            account: Account = form.cleaned_data['account']
            product: Product = form.cleaned_data['product']
            amount: int = form.cleaned_data['amount']
            invert_member: bool = form.cleaned_data['invert_member']

            price = product.member_cost if account.member != invert_member else product.cost
            price *= amount

            if account.current_budget < price:
                raise ValidationError(_('The account has not enough money'), code='out_of_money')
            
            reason = product.name
            if amount > 1:
                reason = f'{amount}x {reason}'
            if invert_member:
                with override_language(settings.LANGUAGE_CODE):
                    # Translators: Used as a prefix for transaction reason if a member buys something on behalf of a non-member
                    for_extern = _('For extern')
                    # Translators: Used as a prefix for transaction reason if a non-member buys something on behalf of a member
                    for_intern = _('For intern')
                reason = f'{for_extern if account.member else for_intern}: {reason}'

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
                raise ValidationError(_('Not authorized to withdraw from this account'), code='user_permission')
            
            if not reason:
                amount_str = str(amount)
                wholes, cents = amount_str[:-2], amount_str[-2:]
                with override_language(settings.LANGUAGE_CODE):
                    deposit_reason = _('Deposit')
                    withdraw_reason = _('Withdraw')
                reason = f"{deposit_reason if action == 'deposit' else withdraw_reason}: {wholes},{cents}€"

            if action == 'withdraw':
                amount = -amount
                if account.current_budget + amount < 0:
                    raise ValidationError(_('The account has not enough money'), code='out_of_money')

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
            form.add_error(None, ValidationError(_('Transaction already reverted'), code='already_reverted'))
        except PermissionDenied:
            form.add_error(None, ValidationError(_('Not authorized to revert this transaction'), code='user_permission'))        
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

