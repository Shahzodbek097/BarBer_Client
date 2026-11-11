"""Rol asosida ruxsatlar va bloklangan user to'sig'i (bosqich 3).

Izolyatsiya matritsasi (TZ 1.3): har rol o'z ma'lumotlarini ko'radi —
o'ziga xos endpointlarda rol klassi qo'llanadi (bosqich 5 API'da).
"""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsNotBlocked(BasePermission):
    """Autentifikatsiyalangan, lekin bloklangan user har qanday so'rovdan o'tmaydi."""

    message = "Hisobingiz bloklangan."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return True  # auth talabi boshqa klassda (IsAuthenticated)
        return user.is_active and not user.is_blocked


class RolePermission(BasePermission):
    """Birlamchi rol klassi — allowed_roles bilan konfiguratsiya qilinadi."""

    message = "Sizga bu amal uchun ruxsat berilmagan."
    allowed_roles: tuple[str, ...] = ()

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return bool(user is not None and user.is_authenticated and user.role in self.allowed_roles)


class IsClient(RolePermission):
    allowed_roles = (User.Role.CLIENT,)


class IsBarber(RolePermission):
    allowed_roles = (User.Role.BARBER,)


class IsSalonAdmin(RolePermission):
    allowed_roles = (User.Role.SALON_ADMIN,)


class IsSuperAdmin(RolePermission):
    allowed_roles = (User.Role.SUPERADMIN,)


class IsStaffRole(RolePermission):
    """Ichki kabinet rollari: sartarosh + salon egasi + super admin."""

    allowed_roles = (User.Role.BARBER, User.Role.SALON_ADMIN, User.Role.SUPERADMIN)
