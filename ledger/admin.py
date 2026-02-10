from django.contrib import admin
from . import models
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline
from django.contrib import messages
from django import forms
from django.utils.translation import gettext_lazy as _
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

    @admin.display(description=_('Credit'))
    def custom_credit(self, obj: models.Account):
        return fpint(obj.credit)
    
    @admin.display(description=_('Balance'))
    def custom_balance(self, obj: models.Account):
        return fpint(obj.current_balance)

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

admin.site.register(models.AccountBalance)


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["account__display_name", "reason", "type", "fp_amount", "timestamp", ]
    list_filter = ["account", "type", ]
    ordering = ["-timestamp", ]
    

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
    

