from rest_framework.permissions import BasePermission


class IsVendor(BasePermission):
    message = "Access restricted to vendors only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "vendor"
        )