from django.contrib import admin
from . import models
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline, SortableStackedInline, SortableAdminBase

class ProductTabularInline(SortableTabularInline):
    model = models.Product
    readonly_fields = ["order"]
    
@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ["account__name", "reason", "amount"]

@admin.register(models.Product)
class ProductAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["order", "name", "cost", "member_cost", "group"]
    ordering = ['order']

@admin.register(models.Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["name", "active", "member", "is_liquid", "group", "last_balance", "current_balance", "credit"]

@admin.register(models.AccountGroup)
class AccountGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name"]
    
@admin.register(models.ProductGroup)
class ProductGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name"]
    inlines = [ProductTabularInline]

# Register your models here.
admin.site.register(models.AccountBalance)
