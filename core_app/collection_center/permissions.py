from rest_framework.permissions import BasePermission


class IsCollectionCenter(BasePermission):
    message = "Access restricted to collection centers only."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == "collection_center"
        )