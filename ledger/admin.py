from django.contrib import admin
from . import models
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline
from django.contrib import messages
from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django_admin_action_forms import AdminActionForm, AdminActionFormsMixin, action_with_form

from .utils import fpint

@admin.register(models.AccountGroup)
class AccountGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name", ]

class CloseBalanceForm(AdminActionForm):
    cutoff_date = forms.SplitDateTimeField(label=_('Cutoff date'), help_text=_('Only transactions before this timestamp will be included in the balance'))

@admin.register(models.Account)
class AccountAdmin(AdminActionFormsMixin, admin.ModelAdmin):
    list_display = ["display_name", "full_name", "group", "active", "member", "permanent", "custom_balance", "custom_credit", "last_balance", ]
    list_filter = ["active", "member", ]

    readonly_fields = ['custom_balance', 'last_closing_balance']

    class Media:
        css = {'all': ['ledger/admin.css']}

    @admin.display(description=_('Credit'))
    def custom_credit(self, obj: models.Account):
        return format_html('{}€', fpint(obj.credit))
    
    @admin.display(description=_('Balance'))
    def custom_balance(self, obj: models.Account):
        return format_html('{}€', fpint(obj.current_balance))
    
    @admin.display(description=_('Last closing balance'))
    def last_closing_balance(self, obj: models.Account):
        if obj.last_balance:
            return format_html('<a href="{}">{}</a>', reverse('admin:ledger_accountbalance_change', args=[obj.last_balance.pk]), obj.last_balance)
        return '-'

    @action_with_form(
        CloseBalanceForm,
        description=_('Close balance for selected accounts')
    )
    def close_balance(self, request, queryset, data):
        cutoff_date = data["cutoff_date"]
        account: models.Account
        for account in queryset:
            account.close_balance(cutoff_date)

        self.message_user(request, f'Closed balance to {queryset.count()} users with cutoff date {cutoff_date}', level=messages.SUCCESS)

    actions = [close_balance]

class ReadOnlyAdmin(admin.ModelAdmin):
    readonly_fields = []
    exclude = []

    def get_readonly_fields(self, request, obj=None):
        excludes = set(self.exclude)
        return [field.name for field in obj._meta.fields if field.name not in excludes] + \
               [field.name for field in obj._meta.many_to_many if field.name not in excludes] + \
               list(self.readonly_fields)


    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
class ReadOnlyTabularInline(admin.TabularInline):
    extra = 0
    can_delete = False
    editable_fields = []
    readonly_fields = []
    exclude = []

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + \
               [field.name for field in self.model._meta.fields
                if field.name not in self.editable_fields and
                   field.name not in self.exclude]

    def has_add_permission(self, request, obj):
        return False

class TransactionListInline(ReadOnlyTabularInline):
    model = models.Transaction
    exclude = ['related_transaction', 'extra', 'account', 'amount']
    readonly_fields = ['custom_amount']

    
    @admin.display(description=_('Amount'))
    def custom_amount(self, obj: models.Transaction):
        return format_html('{}€', fpint(obj.amount, obj.type in models.Transaction.TransactionType.withdraws()))

@admin.register(models.AccountBalance)
class AccountBalanceAdmin(ReadOnlyAdmin):
    readonly_fields = ['custom_closing_balance']
    inlines = [TransactionListInline]
    exclude = ['id', 'closing_balance']

    class Media:
        css = {'all': ['ledger/admin-accountbalance.css']}

    
    @admin.display(description=_('Closing Balance'))
    def custom_closing_balance(self, obj: models.Account):
        return format_html('{}€', fpint(obj.closing_balance))


@admin.register(models.Transaction)
class TransactionAdmin(ReadOnlyAdmin):
    list_display = ["account__display_name", "reason", "type", "fp_amount", "timestamp", ]
    list_filter = ["account", "type", ]
    ordering = ["-timestamp", ]
    exclude = [ 'amount' ]
    
    readonly_fields = [ 'custom_amount' ]


    @admin.display(description=_('Amount'))
    def custom_amount(self, obj: models.Transaction):
        return format_html('{}€', fpint(obj.amount, obj.type in models.Transaction.TransactionType.withdraws()))
    

class ProductTabularInline(SortableTabularInline):
    model = models.Product
    ordering = ['order', ]
    
@admin.register(models.ProductGroup)
class ProductGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name", ]
    inlines = [ProductTabularInline]

@admin.register(models.Product)
class ProductAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["order", "full_name", "display_name", "category", "display_cost", "display_member_cost", "group", "visible", ]
    list_filter = ["category", "visible", "group", ]
    ordering = ['order', ]

    @admin.display(description=_('Cost'))
    def display_cost(self, obj: models.Product) -> str:
        return fpint(obj.cost)
    
    @admin.display(description=_('Member cost'))
    def display_member_cost(self, obj: models.Product) -> str:
        return fpint(obj.member_cost)
    

