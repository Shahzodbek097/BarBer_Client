"""Bosqich 3: rol izolyatsiya matritsasi testlari (4 rol x permission)."""

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.factories import UserFactory
from apps.accounts.models import User
from apps.accounts.permissions import (
    IsBarber,
    IsClient,
    IsNotBlocked,
    IsSalonAdmin,
    IsStaffRole,
    IsSuperAdmin,
)

pytestmark = pytest.mark.django_db

ROLE_PERMISSIONS = [
    (IsClient, User.Role.CLIENT),
    (IsBarber, User.Role.BARBER),
    (IsSalonAdmin, User.Role.SALON_ADMIN),
    (IsSuperAdmin, User.Role.SUPERADMIN),
]
ALL_ROLES = [User.Role.CLIENT, User.Role.BARBER, User.Role.SALON_ADMIN, User.Role.SUPERADMIN]


def _request_for(user):
    factory = APIRequestFactory()
    request = factory.get("/")
    request.user = user
    return request


class TestRoleMatrix:
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_each_role_permitted_only_for_own_class(self, role):
        """Har rol faqat o'z permission klassidan o'tadi."""
        user = UserFactory(role=role)
        request = _request_for(user)

        results = {cls.__name__: cls().has_permission(request, None) for cls, _ in ROLE_PERMISSIONS}
        own_class = {c.__name__ for c, r in ROLE_PERMISSIONS if r == role}

        for name, allowed in results.items():
            if name in own_class:
                assert allowed, f"{role} o'z klassidan ({name}) o'tmadi"
            else:
                assert not allowed, f"{role} chet klassdan ({name}) o'tib ketti"

    def test_staff_role_covers_three_roles(self):
        for role in (User.Role.BARBER, User.Role.SALON_ADMIN, User.Role.SUPERADMIN):
            request = _request_for(UserFactory(role=role))
            assert IsStaffRole().has_permission(request, None)

        request = _request_for(UserFactory(role=User.Role.CLIENT))
        assert not IsStaffRole().has_permission(request, None)


class TestIsNotBlocked:
    @pytest.mark.parametrize("role", ALL_ROLES)
    def test_active_roles_pass(self, role):
        request = _request_for(UserFactory(role=role))

        assert IsNotBlocked().has_permission(request, None)

    def test_blocked_user_denied(self):
        request = _request_for(UserFactory(is_blocked=True))

        assert not IsNotBlocked().has_permission(request, None)

    def test_inactive_user_denied(self):
        request = _request_for(UserFactory(is_active=False))

        assert not IsNotBlocked().has_permission(request, None)

    def test_anonymous_passes_this_class(self):
        """Auth talabi IsAuthenticated'da — bu klass faqat blokni tekshiradi."""
        request = _request_for(None)

        assert IsNotBlocked().has_permission(request, None)
