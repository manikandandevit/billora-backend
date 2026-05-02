from rest_framework.permissions import BasePermission


class IsHead(BasePermission):
    """Signed-in user who is a Billora Head (company owner)."""

    message = "Head account required."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return getattr(user, "head_profile", None) is not None


class IsClient(BasePermission):
    """Signed-in user who is a Client under a Head."""

    message = "Client account required."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return getattr(user, "client_profile", None) is not None


class IsBranch(BasePermission):
    """Outlet / SalesPoints login (hotel branch account)."""

    message = "Branch account required."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return getattr(user, "branch_profile", None) is not None


class IsHeadOrClient(BasePermission):
    """Company Head or a Client staff user under that company (manage branches under same Head)."""

    message = "Head or Client account required."

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False
        return getattr(user, "head_profile", None) is not None or getattr(
            user, "client_profile", None
        ) is not None
