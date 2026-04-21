from rest_framework.permissions import BasePermission


class IsDeliveryBoy(BasePermission):
    message = "Access restricted to delivery boys only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "delivery"
        )