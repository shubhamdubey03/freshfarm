# core_payment/admin.py

from django.contrib import admin
from django.utils.html import format_html
from core_payment.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display  = ["id", "order", "amount", "method", "status_badge", "transaction_id", "created_at"]
    list_filter   = ["status", "method"]
    search_fields = ["transaction_id", "order__id"]
    readonly_fields = ["transaction_id", "created_at"]

    def status_badge(self, obj):
        colors = {
            "paid":"#10b981",
            "pending": "#f59e0b",
            "failed": "#ef4444",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color, obj.status.upper()
        )
    status_badge.short_description = "Status"