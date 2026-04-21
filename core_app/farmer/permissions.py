from rest_framework.permissions import BasePermission


class IsFarmer(BasePermission):
    message = "Access restricted to farmers only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "farmer"
        )