# core_app/admin.py
# ─────────────────────────────────────────────────────────────────────────────
#  FRESHAPP  —  Custom Admin Site with Reports & Analytics
#  Drop this file in:  core_app/admin.py
#  Then update your project urls.py (see bottom of this file)
# ─────────────────────────────────────────────────────────────────────────────

import csv
from datetime import timedelta

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import (
    Sum, Count, Avg, Q,
    DecimalField, IntegerField,
)
from django.db.models.functions import TruncDate, TruncMonth
from django.http import JsonResponse, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from core_app.models import (
    User, Seller, CollectionCenter,
    CollectionOrder, VendorOrder, Subscription, State, City, Address, OTP
)


# ══════════════════════════════════════════════════════════════════════════════
#  BADGE HELPERS  (shared across all admin files)
# ══════════════════════════════════════════════════════════════════════════════

def _badge(text, color):
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 9px;border-radius:4px;'
        'font-size:11px;font-weight:600;letter-spacing:.03em">{}</span>',
        color, text,
    )

def green_badge(t):  return _badge(t, "#10b981")
def red_badge(t):    return _badge(t, "#ef4444")
def yellow_badge(t): return _badge(t, "#f59e0b")
def blue_badge(t):   return _badge(t, "#3b82f6")
def purple_badge(t): return _badge(t, "#8b5cf6")
def cyan_badge(t):   return _badge(t, "#06b6d4")


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS DATA  —  All queries using YOUR exact model fields
# ══════════════════════════════════════════════════════════════════════════════

def _get_reports_data(days: int) -> dict:
    """
    Single function that builds every chart / KPI from your real DB.
    Called by the JSON API endpoint.
    """
    # Lazy imports to avoid circular import at module level
    from core_order.models import (
        Order, SellerEarning, SellerPayout,
        FarmerSalary, AdminCommission, Delivery,
    )
    from core_product.models import Product, CartItem

    since = timezone.now() - timedelta(days=days)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    total_orders    = Order.objects.filter(created_at__gte=since).count()
    total_revenue   = float(
        Order.objects.filter(
            created_at__gte=since, status="delivered"
        ).aggregate(t=Sum("total_price"))["t"] or 0
    )
    active_sellers  = Seller.objects.filter(is_verified=True).count()
    pending_payouts = float(
        SellerEarning.objects.filter(
            is_settled=False
        ).aggregate(t=Sum("amount"))["t"] or 0
    )
    total_users = User.objects.filter(role="user").count()
    total_farmers = Seller.objects.filter(seller_type="farmer", is_verified=True).count()
    total_vendors = Seller.objects.filter(seller_type="vendor", is_verified=True).count()
    pending_kyc = Seller.objects.filter(is_verified=False).count()

    # commissions earned
    total_commission = float(
        AdminCommission.objects.filter(
            created_at__gte=since
        ).aggregate(t=Sum("commission_amount"))["t"] or 0
    )

    # ── Revenue over time  (daily, TruncDate on created_at) ──────────────────
    revenue_rows = (
        Order.objects
        .filter(created_at__gte=since, status="delivered")
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(revenue=Sum("total_price"))
        .order_by("day")
    )
    revenue_over_time = [
        {"date": r["day"].strftime("%b %d"), "revenue": float(r["revenue"])}
        for r in revenue_rows
    ]

    # ── Orders by status ─────────────────────────────────────────────────────
    status_qs = (
        Order.objects
        .filter(created_at__gte=since)
        .values("status")
        .annotate(count=Count("id"))
    )
    order_status = [
        {"status": r["status"].replace("_", " ").title(), "count": r["count"]}
        for r in status_qs
    ]

    # ── Top 5 sellers by earnings ─────────────────────────────────────────────
    top_sellers = list(
        SellerEarning.objects
        .filter(created_at__gte=since)
        .values("seller__farm_name", "seller__seller_type")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:5]
    )
    top_sellers_data = [
        {
            "name": r["seller__farm_name"] or "—",
            "type": r["seller__seller_type"],
            "revenue": float(r["total"]),
        }
        for r in top_sellers
    ]

    # ── Monthly revenue (last 12 months) ─────────────────────────────────────
    twelve_months_ago = timezone.now() - timedelta(days=365)
    monthly_rows = (
        Order.objects
        .filter(created_at__gte=twelve_months_ago, status="delivered")
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(revenue=Sum("total_price"))
        .order_by("month")
    )
    monthly_revenue = [
        {"month": r["month"].strftime("%b %Y"), "revenue": float(r["revenue"])}
        for r in monthly_rows
    ]

    # ── Orders by flow type (vendor vs farmer) ────────────────────────────────
    flow_qs = (
        Order.objects
        .filter(created_at__gte=since)
        .values("flow_type")
        .annotate(count=Count("id"))
    )
    flow_data = [
        {"flow": r["flow_type"].title(), "count": r["count"]}
        for r in flow_qs
    ]

    # ── Commission trend (monthly) ────────────────────────────────────────────
    commission_monthly = list(
        AdminCommission.objects
        .filter(created_at__gte=twelve_months_ago)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(total=Sum("commission_amount"))
        .order_by("month")
    )
    commission_trend = [
        {"month": r["month"].strftime("%b %Y"), "amount": float(r["total"])}
        for r in commission_monthly
    ]

    # ── Delivery performance ──────────────────────────────────────────────────
    delivery_status_qs = (
        Delivery.objects
        .filter(order__created_at__gte=since)
        .values("status")
        .annotate(count=Count("id"))
    )
    delivery_status = [
        {"status": r["status"].replace("_", " ").title(), "count": r["count"]}
        for r in delivery_status_qs
    ]

    # ── Payment method split ──────────────────────────────────────────────────
    try:
        from core_payment.models import Payment
        payment_qs = (
            Payment.objects
            .filter(created_at__gte=since)
            .values("method")
            .annotate(count=Count("id"), total=Sum("amount"))
        )
        payment_split = [
            {"method": r["method"].upper(), "count": r["count"], "total": float(r["total"])}
            for r in payment_qs
        ]
    except Exception:
        payment_split = []

    # ── User growth (new users per day) ──────────────────────────────────────
    user_growth = list(
        User.objects
        .filter(role="user", date_joined__gte=since)
        .annotate(day=TruncDate("date_joined"))
        .values("day")
        .annotate(count=Count("id"))
        .order_by("day")
    )
    user_growth_data = [
        {"date": r["day"].strftime("%b %d"), "count": r["count"]}
        for r in user_growth
    ]

    return {
        "kpis": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "active_sellers": active_sellers,
            "pending_payouts": pending_payouts,
            "total_users": total_users,
            "total_farmers": total_farmers,
            "total_vendors": total_vendors,
            "pending_kyc": pending_kyc,
            "total_commission": total_commission,
        },
        "revenue_over_time":  revenue_over_time,
        "monthly_revenue":    monthly_revenue,
        "order_status": order_status,
        "top_sellers": top_sellers_data,
        "flow_data": flow_data,
        "commission_trend": commission_trend,
        "delivery_status": delivery_status,
        "payment_split": payment_split,
        "user_growth": user_growth_data,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  REPORTS MIXIN  —  Injects /admin/reports/ into any AdminSite
# ══════════════════════════════════════════════════════════════════════════════

class ReportsMixin:
    def get_urls(self):
        urls = super().get_urls()
        extra = [
            path(
                "reports/",
                self.admin_view(self._reports_page),
                name="freshapp_reports",
            ),
            path(
                "reports/data/",
                self.admin_view(self._reports_data_api),
                name="freshapp_reports_data",
            ),
        ]
        return extra + urls

    def _reports_page(self, request):
        ctx = dict(self.each_context(request), title="Reports & Analytics")
        return TemplateResponse(request, "admin/freshapp_reports.html", ctx)

    def _reports_data_api(self, request):
        days = int(request.GET.get("days", 30))
        data = _get_reports_data(days)

        # ── CSV export ────────────────────────────────────────────────────────
        if request.GET.get("format") == "csv":
            resp = HttpResponse(content_type="text/csv")
            resp["Content-Disposition"] = (
                f'attachment; filename="freshapp_revenue_{days}d.csv"'
            )
            w = csv.writer(resp)
            w.writerow(["Date", "Revenue (₹)"])
            for row in data["revenue_over_time"]:
                w.writerow([row["date"], row["revenue"]])
            return resp

        return JsonResponse(data)


# ══════════════════════════════════════════════════════════════════════════════
#  CUSTOM ADMIN SITE
# ══════════════════════════════════════════════════════════════════════════════

class FreshAppAdminSite(ReportsMixin, admin.AdminSite):
    site_header  = "FreshApp Admin"
    site_title   = "FreshApp Management"
    index_title  = "Dashboard"

    def logout(self, request, extra_context=None):
        from django.contrib.auth import logout as auth_logout
        from django.shortcuts import redirect
        auth_logout(request)
        return redirect('/admin/login/')


freshapp_admin = FreshAppAdminSite(name="freshapp_admin")


# ══════════════════════════════════════════════════════════════════════════════
#  USER ADMIN
# ══════════════════════════════════════════════════════════════════════════════
@admin.register(OTP, site=freshapp_admin)
class OTPAdmin(admin.ModelAdmin):
    list_display  = ["user", "otp", "created_at", "expire_at", "is_expired_badge"]
    list_filter   = ["created_at"]
    search_fields = ["user__phone", "user__username", "otp"]
    ordering      = ["-created_at"]

    def is_expired_badge(self, obj):
        if obj.is_expired():
            return red_badge("Expired")
        return green_badge("Active")
    is_expired_badge.short_description = "Status"


@admin.register(User, site=freshapp_admin)
class UserAdmin(BaseUserAdmin):
    list_display  = ["username", "phone", "role_badge", "is_verified", "created_at"]
    list_filter   = ["role", "is_verified"]
    search_fields = ["username", "phone", "email"]
    ordering      = ["-created_at"]

    fieldsets = BaseUserAdmin.fieldsets + (
        ("FreshApp Fields", {
            "fields": ("role", "phone", "country_code", "profile_image", "is_verified")
        }),
    )

    def role_badge(self, obj):
        color_map = {
            "admin": "#ef4444",
            "farmer":"#10b981",
            "vendor":"#3b82f6",
            "delivery": "#f59e0b",
            "collection_center": "#8b5cf6",
            "user":"#6b7280",
        }
        return _badge(obj.role.upper(), color_map.get(obj.role, "#6b7280"))
    role_badge.short_description = "Role"


# ══════════════════════════════════════════════════════════════════════════════
#  SELLER ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Seller, site=freshapp_admin)
class SellerAdmin(admin.ModelAdmin):
    list_display  = ["farm_name", "user", "seller_type_badge",
                     "farm_location", "verified_badge", "created_at"]
    list_filter   = ["seller_type", "is_verified"]
    search_fields = ["farm_name", "user__username", "user__phone"]
    actions       = ["verify_sellers"]

    def seller_type_badge(self, obj):
        return green_badge("FARMER") if obj.seller_type == "farmer" else blue_badge("VENDOR")
    seller_type_badge.short_description = "Type"

    def verified_badge(self, obj):
        return green_badge("Verified") if obj.is_verified else yellow_badge("Pending KYC")
    verified_badge.short_description = "KYC"

    @admin.action(description="✅ Verify selected sellers (KYC approve)")
    def verify_sellers(self, request, queryset):
        queryset.update(is_verified=True)


# ══════════════════════════════════════════════════════════════════════════════
#  COLLECTION CENTER ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(CollectionCenter, site=freshapp_admin)
class CollectionCenterAdmin(admin.ModelAdmin):
    list_display  = ["center_name", "user", "city", "state", "verified_badge", "created_at"]
    list_filter   = ["is_verified", "state"]
    search_fields = ["center_name", "user__username", "city"]

    def verified_badge(self, obj):
        return green_badge("Active") if obj.is_verified else yellow_badge("Pending")
    verified_badge.short_description = "Status"


# ══════════════════════════════════════════════════════════════════════════════
#  SUBSCRIPTION ADMIN
# ══════════════════════════════════════════════════════════════════════════════

@admin.register(Subscription, site=freshapp_admin)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ["user", "product", "quantity", "start_date", "end_date", "active_badge"]
    list_filter   = ["is_active"]
    search_fields = ["user__username", "user__phone", "product__name"]

    def active_badge(self, obj):
        return green_badge("Active") if obj.is_active else red_badge("Inactive")
    active_badge.short_description = "Status"


# Register remaining simple models
@admin.register(State, site=freshapp_admin)
class StateAdmin(admin.ModelAdmin):
    list_display  = ["name", "state_code", "created_at"]
    search_fields = ["name", "state_code"]


@admin.register(City, site=freshapp_admin)
class CityAdmin(admin.ModelAdmin):
    list_display  = ["name", "state", "pincode", "created_at"]
    list_filter   = ["state"]
    search_fields = ["name", "pincode"]


@admin.register(Address, site=freshapp_admin)
class AddressAdmin(admin.ModelAdmin):
    list_display  = ["user", "city", "state", "pincode", "created_at"]
    list_filter   = ["state", "city"]
    search_fields = ["user__username", "pincode"]


# ══════════════════════════════════════════════════════════════════════════════
#  HOW TO USE IN urls.py  (project-level)
# ══════════════════════════════════════════════════════════════════════════════
#
#  from core_app.admin import freshapp_admin
#
#  # Auto-discover all admin registrations
#  import core_order.admin   # noqa
#  import core_product.admin # noqa
#  import core_payment.admin # noqa
#
#  urlpatterns = [
#      path("admin/", freshapp_admin.urls),
#      ...
#  ]
