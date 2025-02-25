from typing import Any, Dict, Literal
from http import HTTPStatus
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import PermissionRequiredMixin, LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, HttpResponseForbidden, JsonResponse
from django.forms.fields import IntegerField
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView, CreateView, TemplateView

from .decorators import idempotent, json_body, require_POST_fields, one_of, satisfies, chain
from .eventstream import send_event, EventstreamResponse
from .mixins import EnableFieldsMixin, ExtraFormMixin, ContextQuerysetMixin
from .models import Account, Transaction, Product


class AccountList(LoginRequiredMixin, ListView):
	queryset = Account.objects.grouped()
	context_object_name = 'accounts'

class AccountDetail(LoginRequiredMixin, ExtraFormMixin, EnableFieldsMixin, UpdateView):
	model = Account
	object: Account # Type Annotation for IDE
	template_name_suffix = '_detail'
	context_object_name = 'account'
	fields = ['name', 'credit', 'group', 'member', 'permanent']
	extra_form_kwargs = {
		'label_suffix': '',
	}
	
	def get_success_url(self) -> str:
		return reverse('account_detail', args=[self.object.pk])

	def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
		return super().get_context_data(**kwargs) | {
			'transactions': Transaction.objects.recent(account=self.object, user=self.request.user),
			'accounts': Account.objects.grouped(),
			'allow_custom_transaction': self.can_do_custom_transaction(),
		}
	
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
		
	def can_do_custom_transaction(self) -> bool:
		account_is_permanent = self.object.permanent
		user_can_custom_temporary = self.request.user.has_perm('ledger.add_custom_transaction')
		user_can_custom_permanent = self.request.user.has_perm('ledger.add_permanent_custom_transaction')
		return user_can_custom_permanent if account_is_permanent else user_can_custom_temporary

	def get_form(self, form_class = None):
		form = super().get_form(form_class)
		form.fields['balance'] = IntegerField(required=False, disabled=True, initial=self.object.current_balance)
		form.order_fields(['name', 'balance', 'credit', 'group', 'member', 'permanent'])

		return form

class AccountCreate(PermissionRequiredMixin, ExtraFormMixin, EnableFieldsMixin, CreateView):
	model = Account
	object: Account # Type Annotation for IDE
	template_name_suffix = '_create'
	fields = ['name', 'credit', 'group', 'member', 'permanent']
	initial = {
		'member': False,
		'credit': 0,
	}
	extra_form_kwargs = {
		'label_suffix': '',
	}

	def has_permission(self) -> bool:
		return self.request.user.has_perm('ledger.add_account') or self.request.user.has_perm('ledger.add_permanent_account')

	def get_initial(self) -> Dict[str, Any]:
		return super().get_initial() | {
			'permanent': self.request.user.has_perm('ledger.add_permanent_account') and not self.request.user.has_perm('ledger.add_account')
		}
	
	def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
		return super().get_context_data(**kwargs) | {
			'accounts': Account.objects.grouped(),
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

class IndexView(LoginRequiredMixin, TemplateView):
	template_name = "ledger/main.html"

	def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
		return super().get_context_data(**kwargs) | {
			"accounts": Account.objects.grouped(),
			"products": Product.objects.grouped(),
			"transactions": Transaction.objects.recent()
		}

def test(request: HttpRequest):
	return render(request, "ledger/test.html", {
		"accounts": Account.objects.grouped(),
		"products": Product.objects.grouped(),
		"transactions": Transaction.objects.recent(),
	})

@require_POST
@permission_required(["ledger.add_transaction"], raise_exception=True)
@idempotent
#@require_POST_fields([("account", int), ("product", int), ("amount?", int)])
@json_body(patterns=[
	("account", int),
	("product", int),
	("amount?", chain(int, satisfies(lambda x: x > 0)))])
def product_transaction(request: HttpRequest, account: int, product: int, amount: int = 1):
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
		
		return JsonResponse({"transaction_id": new_transaction.pk})
	except (Account.DoesNotExist, Product.DoesNotExist):
		return HttpResponseNotFound("Invalid account or product")
	except Account.NotEnoughFunds:
		return HttpResponseForbidden("Not enough budget")


@require_POST
@idempotent
#@require_POST_fields([("account", int), ("amount", int)])
@json_body(patterns=[
	("account", int),
	("amount", chain(int, satisfies(lambda x: x > 0))),
	("type", "custom_type", one_of('withdraw', 'deposit'))])
def custom_transaction(request: HttpRequest, account: int, amount: int, custom_type: Literal['withdraw', 'deposit']):
	try:		
		account: Account = Account.objects.get(pk=account, active=True)

		required_permission = "ledger.add_permanent_custom_transaction" if account.permanent else "ledger.add_custom_transaction"		
		if not request.user.has_perm(required_permission):
			raise PermissionDenied()
		
		amount_str = str(amount).rjust(3, '0')
		wholes, cents = amount_str[:-2], amount_str[-2:]
		reason = f"{custom_type.capitalize()}: {wholes},{cents}€"
		if custom_type == 'withdraw':
			amount = -amount

		new_transaction = Transaction.objects.create(
			account=account,
			amount=amount,
			reason=reason,
			issuer=request.user,
			idempotency_key=request.idempotency_key)
		
		return JsonResponse({"transaction_id": new_transaction.pk})
	except Account.DoesNotExist:
		return HttpResponseNotFound("Invalid account")
	
@require_POST
@permission_required(["ledger.add_transaction"], raise_exception=True)
@idempotent
@json_body(patterns=[("transaction", int)])
def revert_transaction(request: HttpRequest, transaction: int):
	try:
		transaction: Transaction = Transaction.objects.get(pk=transaction)
		transaction.revert(issuer=request.user)
		return HttpResponse(status=HTTPStatus.NO_CONTENT)
	except Transaction.DoesNotExist:
		return HttpResponseNotFound("Invalid transaction")
	except Transaction.AlreadyReverted:
		return HttpResponse('Already reverted', status=HTTPStatus.CONFLICT)

@login_required
def transaction_event(request: HttpRequest):
	return EventstreamResponse(channel='transaction')


def send(request: HttpRequest):
	counter = request.GET.get('counter', 0)
	send_event('counter', None, {'server': 'hello', 'counter': counter})
	return HttpResponse('ok')

@login_required
def event(request):
	return EventstreamResponse('counter')
