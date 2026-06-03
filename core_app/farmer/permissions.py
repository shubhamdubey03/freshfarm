from rest_framework.permissions import BasePermission


class IsFarmer(BasePermission):
    message = "Access restricted to farmers and vendors."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in ["farmer", "vendor"]
        )