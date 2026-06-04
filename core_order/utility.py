# core_order/services.py
import random
import string
import math
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from core_app.models import User
from core_order.models import Delivery

# ─────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────


def generate_otp(length=6):
    return "".join(random.choices(string.digits, k=length))


def haversine_distance(lat1, lon1, lat2, lon2):
    """Returns distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(float(lat1)))
        * math.cos(math.radians(float(lat2)))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────
# 1. SEND OTP
# ─────────────────────────────────────────


def send_otp(user):
    """
    Generates OTP, saves to DB, sends via SMS.
    Returns (otp_instance, success: bool, error: str|None)
    """
    from core_app.models import OTP

    # Expire all previous OTPs for this user
    OTP.objects.filter(user=user).delete()

    otp_code = generate_otp()

    otp_instance = OTP.objects.create(
        user=user,
        otp=otp_code,
    )

    success, error = _send_sms(user.country_code, user.phone, otp_code)

    return otp_instance, success, error


def verify_otp(user, otp_code):
    """
    Verifies OTP for a user.
    Returns (success: bool, error: str|None)
    """
    from core_app.models import OTP

    try:
        otp_instance = OTP.objects.filter(user=user).latest("created_at")
    except OTP.DoesNotExist:
        return False, "No OTP found. Please request a new one."

    if otp_instance.is_expired():
        otp_instance.delete()
        return False, "OTP has expired. Please request a new one."

    if otp_instance.otp != otp_code:
        return False, "Invalid OTP."

    # Valid — clean up and mark user verified
    otp_instance.delete()
    user.is_verified = True
    user.save(update_fields=["is_verified"])

    return True, None


def _send_sms(country_code, phone, otp_code):
    """
    Internal — sends SMS via your provider.
    Swap the body for Twilio / Fast2SMS / MSG91 etc.
    Returns (success: bool, error: str|None)
    """
    try:
        # ── Fast2SMS example ──────────────────────────────
        # import requests
        # response = requests.post(
        #     "https://www.fast2sms.com/dev/bulkV2",
        #     headers={"authorization": settings.FAST2SMS_API_KEY},
        #     data={
        #         "route": "otp",
        #         "variables_values": otp_code,
        #         "numbers": phone,
        #     },
        #     timeout=10,
        # )
        # response.raise_for_status()
        # return True, None

        # ── Twilio example ────────────────────────────────
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_SID, settings.TWILIO_TOKEN)
        # client.messages.create(
        #     body=f"Your OTP is {otp_code}. Valid for 59 seconds.",
        #     from_=settings.TWILIO_FROM,
        #     to=f"{country_code}{phone}",
        # )
        # return True, None

        # ── Dev fallback — just print ─────────────────────
        print(f"[OTP] → {country_code}{phone} : {otp_code}")
        return True, None

    except Exception as e:
        return False, str(e)


# ─────────────────────────────────────────
# 2. AUTO ASSIGN DELIVERY BOY
# ─────────────────────────────────────────


def auto_assign_delivery(order):
    """
    Finds the nearest available delivery boy and creates a Delivery record.
    Called from signal when order.status = 'at_collection_center' (farmer flow)
    or VendorOrder.status = 'ready' (vendor flow).

    Returns (delivery_instance, success: bool, error: str|None)
    """
    # ── Guard: skip if already assigned ──────────────────
    if Delivery.objects.filter(order=order).exists():
        return None, False, "Delivery already assigned for this order."

    # ── Determine pickup point ────────────────────────────
    if order.flow_type == "farmer":
        pickup_center = order.collection_center
        if not pickup_center:
            return None, False, "No collection center linked to this order."
        if not pickup_center.latitude or not pickup_center.longitude:
            return None, False, "Collection center has no coordinates."
        pickup_lat = pickup_center.latitude
        pickup_lon = pickup_center.longitude
        source_type = "collection_center"
        vendor = None

    elif order.flow_type == "vendor":
        try:
            vendor_order = order.vendororder
        except Exception:
            return None, False, "No VendorOrder linked to this order."

        vendor = vendor_order.vendor
        pickup_lat = None
        pickup_lon = None

        # Check Seller model directly (first priority)
        if vendor.latitude and vendor.longitude:
            pickup_lat = vendor.latitude
            pickup_lon = vendor.longitude
        else:
            seller_address = vendor.user.user_address.first()
            if seller_address and seller_address.latitude and seller_address.longitude:
                pickup_lat = seller_address.latitude
                pickup_lon = seller_address.longitude

        if not pickup_lat or not pickup_lon:
            return None, False, "Vendor is missing coordinates (latitude/longitude)."

        source_type = "vendor"
        pickup_center = None

    else:
        return None, False, f"Unknown flow_type: {order.flow_type}"

    # ── Find available delivery boys ──────────────────────
    # "Available" = role is delivery + no active Delivery record right now
    from django.core.cache import cache

    busy_boy_ids = Delivery.objects.filter(
        status__in=["assigned", "accepted", "picked_up"]
    ).values_list("delivery_boy_id", flat=True)

    available_boys_qs = (
        User.objects.filter(role="delivery")
        .exclude(id__in=busy_boy_ids)
        .prefetch_related("user_address")
    )

    available_boys = [
        boy
        for boy in available_boys_qs
        if not cache.get(f"declined_delivery_{order.id}_{boy.id}")
    ]

    if not available_boys:
        return None, False, "No delivery boys available right now."

    # ── Pick nearest using haversine ──────────────────────
    nearest_boy = None
    shortest_distance = float("inf")

    for boy in available_boys:
        address = boy.user_address.first()
        if not address or not address.latitude or not address.longitude:
            continue  # skip boys with no location

        distance = haversine_distance(
            pickup_lat, pickup_lon, address.latitude, address.longitude
        )

        if distance < shortest_distance:
            shortest_distance = distance
            nearest_boy = boy

    if not nearest_boy:
        return None, False, "No delivery boys with valid location found."

    # ── Create Delivery atomically ────────────────────────
    with transaction.atomic():
        otp = generate_otp()

        delivery = Delivery.objects.create(
            order=order,
            source_type=source_type,
            vendor=vendor,
            pickup_center=pickup_center,
            delivery_boy=nearest_boy,
            status="assigned",
            otp=otp,
        )

        # Order status is NOT changed to "out_for_delivery" here anymore.
        # It will be updated only when the delivery boy verifies the OTP and starts the trip.
        pass

    # ── Notify delivery boy ───────────────────────────────
    _notify_delivery_boy(nearest_boy, order, otp, shortest_distance)

    return delivery, True, None


def _notify_delivery_boy(boy, order, otp, distance_km):
    """
    Send push notification or SMS to delivery boy.
    Swap body for FCM / OneSignal / SMS.
    """
    try:
        message = (
            f"New delivery assigned!\n"
            f"Order #{order.id} | OTP: {otp}\n"
            f"Pickup in {distance_km:.1f} km"
        )

        # ── FCM push notification ────────────────────────
        from core_app.utils.fcm import send_notification

        send_notification(
            user=boy,
            title="New Delivery Assigned",
            body=message,
            data={
                "order_id": str(order.id),
                "otp": str(otp),
                "distance": f"{distance_km:.1f}",
            },
        )

        # ── Dev fallback ──────────────────────────────────
        print(f"[NOTIFY] -> {boy.phone} : {message}")

    except Exception as e:
        # Notification failure should never block delivery assignment
        print(f"[NOTIFY ERROR] {e}")
