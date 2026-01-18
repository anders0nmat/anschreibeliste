from typing import Any, Dict, Literal, Callable, TypeVar
from http import HTTPStatus
from io import BytesIO, TextIOWrapper
import csv
from datetime import timedelta
from importlib.util import find_spec as module_exists
from django import http
from django.core.exceptions import PermissionDenied, ValidationError, BadRequest, ImproperlyConfigured
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseBadRequest, FileResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import ListView, UpdateView, CreateView, TemplateView
from json import loads, dumps
from django.utils.timezone import now
from django.utils.translation import gettext as _, pgettext

from .conf import settings
from .decorators import idempotent
from .eventstream import EventstreamResponse, StreamEvent
from .mixins import EnableFieldsMixin
from .models import Account, Transaction, Product
from .forms import TransactionForm, ProductTransactionForm, RevertTransactionForm, CreateAccountForm, RestrictedCreateAccountForm, EditAccountForm, TransactionListFilter
from .utils.banking import EPCCode
from .utils import server_language
from .utils.transaction import order_product, custom_transaction as custom_transaction_api, transaction_event

def js_config() -> dict[str, Any]:
    transaction_timeout: timedelta = settings.TRANSACTION_TIMEOUT
    submit_overlay: timedelta = settings.SUBMIT_OVERLAY
    return {
        'transaction': {
            'deposit': reverse('ledger:api:deposit'),
            'withdraw': reverse('ledger:api:withdraw'),
            'order': reverse('ledger:api:order'),
            'revert': reverse('ledger:api:revert'),
            'events': reverse('ledger:api:events'),
            'ping': reverse('ledger:api:ping'),
        },
        'transaction_timeout': transaction_timeout.total_seconds() * 1_000,
        'submit_overlay': submit_overlay.total_seconds() * 1_000,
    }

class AccountList(ListView):
    queryset = Account.objects.grouped()

class AccountDetail(EnableFieldsMixin, UpdateView):
    queryset = Account.objects.filter(active=True)
    object: Account # Type Annotation for IDE
    form_class = EditAccountForm
    template_name_suffix = '_detail'
    
    def get_form_kwargs(self) -> Dict[str, Any]:
        return super().get_form_kwargs() | { 'label_suffix': '' }

    def get_success_url(self) -> str:
        if not self.object.active:
            return reverse('ledger:account_list')
        return reverse('ledger:account_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        PERMS = {
        #   (action, permanent)
            ('deposit', False): 'ledger.add_deposit_transaction',
            ('withdraw', False): 'ledger.add_withdraw_transaction',
            ('deposit', True): 'ledger.add_permanent_deposit_transaction',
            ('withdraw', True): 'ledger.add_permanent_withdraw_transaction',
        }

        kwargs |= {
            'account_list': Account.objects.grouped(),
            'transactions': Transaction.objects\
                .filter(closing_balance=None, account=self.object)\
                .order_by('-timestamp')\
                .annotate_timejump()\
                .annotate_revertible(user=self.request.user)\
                .select_related('account'),
            'js_config': js_config(),
            'banking_details': EPCCode.from_config(self.object.full_name or '[Name]'),
        }

        if self.request.user.has_perm(PERMS[('deposit', self.object.permanent)]):
            kwargs |= {
                'deposit_form': TransactionForm(initial={'account': self.object, 'action': 'deposit'}, label_suffix=""),
            }
        if self.request.user.has_perm(PERMS[('withdraw', self.object.permanent)]):
            kwargs |= {
                'withdraw_form': TransactionForm(initial={'account': self.object, 'action': 'withdraw'}, label_suffix=""),
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

class AccountCreate(PermissionRequiredMixin, CreateView):
    model = Account
    object: Account # Type Annotation for IDE
    template_name_suffix = '_create'

    def has_permission(self) -> bool:
        return self.request.user.has_perm('ledger.add_account') or self.request.user.has_perm('ledger.add_permanent_account')
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            'account_list': Account.objects.grouped(),
            'js_config': js_config(),
        }

    def get_success_url(self) -> str:
        return reverse('ledger:account_detail', args=[self.object.pk])

    def get_form_kwargs(self) -> Dict[str, Any]:
        return super().get_form_kwargs() | { 'label_suffix': '' }

    def get_form_class(self) -> type:
        HAS_PERM_FORMS = {
            True: CreateAccountForm,
            False: RestrictedCreateAccountForm,
        }
        return HAS_PERM_FORMS[self.request.user.has_perm('ledger.add_permanent_account')]

    def form_valid(self, form: Any) -> HttpResponse:
        response = super().form_valid(form)
        starting_balance = form.cleaned_data['balance']
        if starting_balance:
            with server_language():
                # Translators: Used for account creation with initial balance
                deposit_reason = _('Initial Deposit')
            Transaction.objects.create(
                account=self.object,
                amount=starting_balance,
                reason=deposit_reason,
                type=Transaction.TransactionType.DEPOSIT,
                issuer=self.request.user)
        return response

class TransactionList(ListView):
    queryset = Transaction.objects.filter(closing_balance=None)
    output_format = 'html'

    def get_queryset(self) -> QuerySet[Any]:
        queryset = super().get_queryset().order_by('-timestamp')

        # Filter Queryset according to GET params
        account_filter = self.get_filter('account', convert=int)
        if account_filter:
            queryset = queryset.filter(account__in=account_filter)

        type_filter = self.get_filter('type', convert=str.upper)
        if type_filter:
            queryset = queryset.filter(type__in=type_filter)

        start_date_filter = self.request.GET.get('start', '')
        if start_date_filter:
            queryset = queryset.filter(timestamp__date__gte=start_date_filter)

        end_date_filter = self.request.GET.get('end', '')
        if end_date_filter:
            queryset = queryset.filter(timestamp__date__lte=end_date_filter)

        return queryset
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            'filters': TransactionListFilter(self.request.GET, label_suffix=''),
        }
    
    T = TypeVar('T')
    def get_filter(self, query_name: str, convert: Callable[[str], T] = lambda x: x) -> list[T]:
        def convert_skip_exception(value):
            try:
                return convert(value)
            except:
                return None
            
        values = self.request.GET.getlist(query_name)
        values = (convert_skip_exception(value) for param in values for value in param.split(',') if value)
        return [value for value in values if value]
    
    def transactions_to_list(self, transactions: QuerySet[Transaction]) -> tuple[list[str], list[list[str]]]:
        headers = [
            _('Account'),
            _('Reason'),
            _('Date'),
            _('Time'),
            pgettext('transaction', 'Type'),
            pgettext('money-related', 'Amount'),
        ]
        values = []
        for transaction in transactions:
            values.append([
                transaction.account.display_name,
                transaction.reason,
                f"{transaction.timestamp:%Y-%m-%d}",
                f"{transaction.timestamp:%H:%M}",
                transaction.get_type_display(),
                str(transaction.fp_amount),
            ])
        return (headers, values)

    def render_to_csv(self, file: BytesIO, transactions: QuerySet[Transaction]):
        f = TextIOWrapper(file)
        try:
            writer = csv.writer(f)
            header, values = self.transactions_to_list(transactions)
            writer.writerow(header)
            writer.writerows(values)
        finally:
            f.detach()

    def render_to_xlsx(self, file: BytesIO, transactions: QuerySet[Transaction]):
        from openpyxl import Workbook
        from openpyxl.worksheet.worksheet import Worksheet
        wb = Workbook()
        ws: Worksheet = wb.active
        
        header, values = self.transactions_to_list(transactions)
        ws.append(header)
        for value in values:
            ws.append(value)
        wb.save(file)

    def render_to_response(self, context: Dict[str, Any], **response_kwargs: Any) -> HttpResponse:
        if self.output_format == 'html':
            return super().render_to_response(context, **response_kwargs)
        
        if self.output_format == 'csv':
            b = BytesIO()
            self.render_to_csv(b, context['object_list'])
            b.seek(0)
            return FileResponse(b, filename=f"Transaction List.csv", as_attachment=True)

        if self.output_format == 'xlsx':
            if not module_exists('openpyxl'):
                raise ImproperlyConfigured('Output Format "xlsx" requires "openpyxl" to be installed')
            b = BytesIO()
            self.render_to_xlsx(b, context['object_list'])
            b.seek(0)
            return FileResponse(b, filename=f"Transaction List.xlsx", as_attachment=True)
            

        return ImproperlyConfigured("No output format given")

class IndexView(TemplateView):
    template_name = "ledger/main.html"

    product_category = Product.ProductCategory.ARTICLE

    def get_transactions(self) -> list[Transaction]:
        """
        Return all transactions newer than `old_threshold`.
        If there are fewer than `min_results`, fill with transactions older than that
        """
        min_results = settings.TRANSACTION_HISTORY_MIN_ENTRIES
        old_threshold = now() - settings.TRANSACTION_HISTORY_OLD_THRESHOLD
        queryset = Transaction.objects\
            .filter(closing_balance=None)\
            .order_by('-timestamp')\
            .annotate_timejump()\
            .annotate_revertible(user=self.request.user)\
            .select_related('account')

        transactions = []
        for t in queryset:
            t: Transaction
            if len(transactions) < min_results:
                transactions.append(t)
            elif t.timestamp > old_threshold:
                transactions.append(t)
            else:
                break
        return transactions 

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        return super().get_context_data(**kwargs) | {
            "account_list": Account.objects.grouped(),
            "product_list": Product.objects.grouped().filter(category=self.product_category),
            "transaction_list": self.get_transactions(),
            'js_config': js_config(),
        }

def test(request: HttpRequest):
    return render(request, "ledger/test.html", {
        "accounts": Account.objects.grouped(),
        "products": Product.objects.grouped(),
        "transactions": Transaction.objects\
                .filter(closing_balance=None)\
                .order_by('-timestamp')\
                .annotate_timejump()\
                .annotate_revertible(user=request.user)\
                .select_related('account'),
        'js_config': js_config(),
    })

def test_event(request: HttpRequest):
    print(f"Registering for events")
    return EventstreamResponse('test')

from .eventstream import send_event
def send_test_event(request: HttpRequest):
    send_event('test', data=request.GET.get('message', 'Default Message'))
    return HttpResponse()

@require_POST
@permission_required('ledger.add_transaction', raise_exception=True)
@idempotent(required=True, post_field='idempotency-key')
def product_transaction(request: HttpRequest):
    is_json = request.content_type == 'application/json'
    if is_json:
        try:
            form = ProductTransactionForm(loads(request.body))
        except:
            return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
    else:
        form = ProductTransactionForm(request.POST)

    if form.is_valid():
        try:
            transaction = order_product(
                account=form.cleaned_data['account'],
                product=form.cleaned_data['product'],
                issuer=request.user,
                amount=form.cleaned_data['amount'],
                invert_member_status=form.cleaned_data['invert_member'],
                extra_data={'idempotency_key': request.idempotency_key})
            if is_json:
                return JsonResponse({"transaction_id": transaction.pk})
            else:
                return HttpResponseRedirect(reverse('ledger:main'))
        except (Account.NotEnoughFunds, ):
            form.add_error(None, ValidationError(_('The account has not enough money'), code='out_of_money'))

    if is_json:
        return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)
    else:
        return HttpResponseBadRequest(form.errors.as_ul())

@require_POST
@idempotent(required=True, post_field='idempotency-key')
def custom_transaction(request: HttpRequest, action: Literal['deposit', 'withdraw']):
    is_json = request.content_type == 'application/json'
    if is_json:
        try:
            form = TransactionForm(loads(request.body))
        except:
            return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
    else:
        form = TransactionForm(request.POST)
    if form.is_valid():
        try:
            transaction = custom_transaction_api(
                account=form.cleaned_data['account'],
                action=action,
                amount=form.cleaned_data['amount'],
                issuer=request.user,
                reason=form.cleaned_data['reason'],
                extra_data={'idempotency_key': request.idempotency_key}
            )
            if is_json:
                return JsonResponse({"transaction_id": transaction.pk})
            else:
                return HttpResponseRedirect(reverse('ledger:account_detail', kwargs={"pk": transaction.account.pk}))
        except PermissionDenied:
            form.add_error(ValidationError(_('Not authorized to perform this transaction for this account'), code='user_permission'))        
        except Account.NotEnoughFunds:
            form.add_error(ValidationError(_('The account has not enough money'), code='out_of_money'))
    if is_json:
        return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)
    else:
        return HttpResponseBadRequest(form.errors.as_ul())

@require_POST
@idempotent(required=True, post_field='idempotency-key')
def revert_transaction(request: HttpRequest, pk: int = None):
    is_json = request.content_type == 'application/json'
    if is_json:
        try:
            form = RevertTransactionForm(loads(request.body))
        except:
            return JsonResponse({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)   
    else:
        form = RevertTransactionForm(request.POST)

    if form.is_valid():
        try:
            transaction = form.cleaned_data['transaction'].revert(
                issuer=request.user,
                idempotency_key=request.idempotency_key)
            if is_json:
                return JsonResponse({"transaction_id": transaction.pk})   
            else:
                return HttpResponseRedirect(reverse('ledger:account_detail', args=[pk]) if pk else reverse('ledger:main'))    
        except Transaction.AlreadyReverted:
            form.add_error(None, ValidationError(_('Transaction already reverted'), code='already_reverted'))
        except PermissionDenied:
            form.add_error(None, ValidationError(_('Not authorized to revert this transaction'), code='user_permission'))
    
    if is_json:
        return JsonResponse(form.errors.as_json(), safe=False, status=HTTPStatus.BAD_REQUEST)
    else:
        return HttpResponseBadRequest(form.errors.as_ul())

def transaction_events(request: HttpRequest):
    initial_event = None

    latest_client_transaction_id = request.headers.get('Last-Event-ID', None) or request.GET.get('last_transaction', None)
    if latest_client_transaction_id:
        try:
            latest_client_transaction_id = int(latest_client_transaction_id)
            last_client_transaction: Transaction = Transaction.objects.get(pk=latest_client_transaction_id)
            missing_transactions: list[Transaction] = Transaction.objects.order_by('-timestamp').filter(timestamp__gt=last_client_transaction.timestamp)
            initial_event = [StreamEvent('create', dumps(transaction_event(transaction)), id=transaction.pk) for transaction in missing_transactions]
        except (ValueError, Transaction.DoesNotExist):
            pass

    return EventstreamResponse(channel='transaction', identifier=f"{request.META['REMOTE_ADDR']}:{request.META['REMOTE_PORT']}", initial_event=initial_event)

def transaction_ping(request: HttpRequest):
    nonce = request.GET.get('nonce')
    if not nonce:
        return HttpResponseBadRequest()
    
    send_event('transaction', 'ping', nonce)
    return HttpResponse('ok')

