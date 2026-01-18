from django.contrib import admin
from . import models
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline
from django.db.models import QuerySet

@admin.register(models.AccountGroup)
class AccountGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name", ]    


@admin.action(description="Close current balance of selected accounts")
def close_balance(modeladmin, request, queryset: QuerySet[models.Account]):
    for account in queryset:
        account.close_balance()

@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["display_name", "full_name", "group", "active", "member", "permanent", "current_balance", "credit", "last_balance", ]
    list_filter = ["active", "member", ]
    actions = [close_balance]

admin.site.register(models.AccountBalance)


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["account__display_name", "reason", "type", "normalized_amount", "timestamp", ]
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
    list_display = ["order", "full_name", "display_name", "category", "cost", "member_cost", "group", "visible", ]
    list_filter = ["category", "visible", "group", ]
    ordering = ['order', ]
    

