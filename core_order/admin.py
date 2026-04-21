# core_order/admin.py
# ─────────────────────────────────────────────────────────────────────────────
#  Register all order-related models with freshapp_admin
#  This file replaces your existing core_order/admin.py
# ─────────────────────────────────────────────────────────────────────────────

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from core_app.admin import freshapp_admin, _badge, green_badge, red_badge, yellow_badge, blue_badge
from core_order.models import (
    Order, OrderItem, OrderStatusHistory,
    Delivery, SellerEarning, SellerPayout,
    FarmerOrderBatch, FarmerOrder,
    FarmerSalary, AdminCommission,
)


# ══════════════════════════════════════════════════════════════════════════════
#  INLINES
# ══════════════════════════════════════════════════════════════════════════════

class OrderItemInline(admin.TabularInline):
    model         = OrderItem
    extra         = 0
    readonly_fields = ["variant", "seller", "price", "quantity"]
    can_delete    = False


class OrderStatusHistoryInline(admin.TabularInline):
    model         = OrderStatusHistory
    extra         = 0
    readonly_fields = ["status", "updated_by", "updated_at"]
    can_delete    = False


# ══════════════════════════════════════════════════════════════════════════════
#  ORDER
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Order, site=freshapp_admin)
class OrderAdmin(admin.ModelAdmin):

    list_display = [
        "id", "user", "flow_badge", "order_type",
        "status_badge", "payment_badge", "total_price", "delivery_date", "created_at"
    ]
    list_filter  = ["status", "flow_type", "order_type", "payment_status"]
    search_fields   = ["user__username", "user__phone", "id"]
    readonly_fields = ["created_at", "total_price"]
    ordering        = ["-created_at"]
    inlines         = [OrderItemInline, OrderStatusHistoryInline]
    date_hierarchy  = "created_at"

    STATUS_COLORS = {
        "placed":               "#f59e0b",
        "farmer_assigned":      "#8b5cf6",
        "sent_to_collection":   "#3b82f6",
        "at_collection_center": "#06b6d4",
        "out_for_delivery":     "#f97316",
        "delivered":            "#10b981",
        "cancelled":            "#ef4444",
    }

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, "#6b7280")
        return _badge(obj.status.replace("_", " ").upper(), color)
    status_badge.short_description = "Status"

    def payment_badge(self, obj):
        return {"paid": green_badge, "failed": red_badge}.get(
            obj.payment_status, yellow_badge
        )(obj.payment_status.upper())
    payment_badge.short_description = "Payment"

    def flow_badge(self, obj):
        return blue_badge("VENDOR") if obj.flow_type == "vendor" else green_badge("FARMER")
    flow_badge.short_description = "Flow"


# ══════════════════════════════════════════════════════════════════════════════
#  DELIVERY
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Delivery, site=freshapp_admin)
class DeliveryAdmin(admin.ModelAdmin):
    list_display    = ["id", "order", "delivery_boy", "source_type",
                       "status_badge", "pickup_time", "delivery_time"]
    list_filter     = ["status", "source_type"]
    search_fields   = ["order__id", "delivery_boy__username", "delivery_boy__phone"]
    readonly_fields = ["otp"]

    def status_badge(self, obj):
        colors = {
            "assigned":  "#f59e0b",
            "picked_up": "#3b82f6",
            "delivered": "#10b981",
            "failed":    "#ef4444",
        }
        return _badge(obj.status.upper(), colors.get(obj.status, "#6b7280"))
    status_badge.short_description = "Status"


# ══════════════════════════════════════════════════════════════════════════════
#  SELLER EARNINGS
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(SellerEarning, site=freshapp_admin)
class SellerEarningAdmin(admin.ModelAdmin):
    list_display  = ["seller", "order", "order_item", "amount", "settled_badge", "created_at"]
    list_filter   = ["is_settled", "seller__seller_type"]
    search_fields = ["seller__farm_name", "order__id"]
    actions       = ["mark_settled"]
    date_hierarchy = "created_at"

    def settled_badge(self, obj):
        return green_badge("Settled") if obj.is_settled else yellow_badge("Pending")
    settled_badge.short_description = "Settlement"

    @admin.action(description="✅ Mark selected earnings as settled")
    def mark_settled(self, request, queryset):
        queryset.update(is_settled=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SELLER PAYOUTS
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(SellerPayout, site=freshapp_admin)
class SellerPayoutAdmin(admin.ModelAdmin):
    list_display  = ["seller", "total_amount", "start_date", "end_date", "paid_badge", "paid_at"]
    list_filter   = ["is_paid"]
    search_fields = ["seller__farm_name"]
    actions       = ["mark_paid"]

    def paid_badge(self, obj):
        return green_badge("Paid") if obj.is_paid else yellow_badge("Unpaid")
    paid_badge.short_description = "Status"

    @admin.action(description="✅ Mark selected payouts as paid")
    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True, paid_at=timezone.now())


# ══════════════════════════════════════════════════════════════════════════════
#  FARMER SALARY
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(FarmerSalary, site=freshapp_admin)
class FarmerSalaryAdmin(admin.ModelAdmin):
    list_display  = ["farmer", "month", "amount", "paid_badge", "paid_at", "note", "created_at"]
    list_filter   = ["is_paid"]
    search_fields = ["farmer__farm_name"]
    actions       = ["mark_paid"]

    def paid_badge(self, obj):
        return green_badge("Paid") if obj.is_paid else yellow_badge("Unpaid")
    paid_badge.short_description = "Status"

    @admin.action(description="✅ Mark selected salaries as paid")
    def mark_paid(self, request, queryset):
        queryset.update(is_paid=True, paid_at=timezone.now())


# ══════════════════════════════════════════════════════════════════════════════
#  ADMIN COMMISSION
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(AdminCommission, site=freshapp_admin)
class AdminCommissionAdmin(admin.ModelAdmin):
    list_display  = [
        "order", "vendor", "order_total",
        "commission_rate_pct", "commission_amount",
        "settled_badge", "created_at"
    ]
    list_filter   = ["is_settled"]
    search_fields = ["vendor__farm_name", "order__id"]
    readonly_fields = ["commission_amount", "created_at"]
    actions       = ["mark_settled"]
    date_hierarchy = "created_at"

    def commission_rate_pct(self, obj):
        return f"{obj.commission_rate}%"
    commission_rate_pct.short_description = "Rate"

    def settled_badge(self, obj):
        return green_badge("Settled") if obj.is_settled else yellow_badge("Pending")
    settled_badge.short_description = "Status"

    @admin.action(description="✅ Mark selected commissions as settled")
    def mark_settled(self, request, queryset):
        queryset.update(is_settled=True, settled_at=timezone.now())


# ══════════════════════════════════════════════════════════════════════════════
#  FARMER BATCH & FARMER ORDER
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(FarmerOrderBatch, site=freshapp_admin)
class FarmerOrderBatchAdmin(admin.ModelAdmin):
    list_display = ["id", "date", "cutoff_time", "closed_badge", "created_at"]
    list_filter  = ["is_closed"]
    actions      = ["close_batches"]

    def closed_badge(self, obj):
        return red_badge("Closed") if obj.is_closed else green_badge("Open")
    closed_badge.short_description = "Batch Status"

    @admin.action(description="🔒 Close selected batches")
    def close_batches(self, request, queryset):
        queryset.update(is_closed=True)


@admin.register(FarmerOrder, site=freshapp_admin)
class FarmerOrderAdmin(admin.ModelAdmin):
    list_display  = ["id", "farmer", "batch", "order_item", "quantity"]
    search_fields = ["farmer__farm_name"]
    list_filter   = ["batch"]
