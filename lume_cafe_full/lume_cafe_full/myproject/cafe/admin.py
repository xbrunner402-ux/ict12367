from django.contrib import admin
from cafe.models import *

class SOItemInline(admin.TabularInline):
    model = SaleOrderItem; extra = 0

class POItemInline(admin.TabularInline):
    model = PurchaseOrderItem; extra = 0

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code','name','phone','points']; search_fields = ['name','code','phone']

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code','name','phone']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code','name','category','sale_price','cost_price','stock_qty','is_available']
    list_filter = ['category','is_available']; list_editable = ['is_available']

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['code','name','unit','stock_qty','min_stock','cost_per_unit']

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['ingredient','move_type','quantity','created_at']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['code','name','role','salary','status']; list_editable = ['status']

@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = ['so_number','date','customer','order_type','total','status']
    list_editable = ['status']; inlines = [SOItemInline]

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['po_number','date','supplier','total','status']
    list_editable = ['status']; inlines = [POItemInline]
