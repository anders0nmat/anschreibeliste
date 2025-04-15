from django.contrib import admin
from . import models
from adminsortable2.admin import SortableAdminMixin, SortableTabularInline

@admin.register(models.AccountGroup)
class AccountGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name"]    

admin.site.register(models.Account, 
    list_display=["name", "group", "active", "member", "current_balance", "credit", "last_balance", ])
admin.site.register(models.AccountBalance)
admin.site.register(models.Transaction,
    list_display=["account__name", "reason", "amount", "timestamp"],
    ordering=["-timestamp"])

class ProductTabularInline(SortableTabularInline):
    model = models.Product
    ordering = ['order']
    
@admin.register(models.ProductGroup)
class ProductGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["name"]
    inlines = [ProductTabularInline]    

@admin.register(models.Product)
class ProductAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ["order", "name", "cost", "member_cost", "group", "visible"]
    ordering = ['order']


