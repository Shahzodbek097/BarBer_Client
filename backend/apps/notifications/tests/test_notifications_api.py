"""Bosqich 5: xabarnoma API testlari (IDOR izolyatsiyasi, o'qilgan holati)."""

import pytest

from apps.accounts.factories import UserFactory
from apps.notifications.factories import NotificationFactory
from apps.notifications.models import NotificationType

pytestmark = pytest.mark.django_db


class TestNotificationList:
    def test_lists_only_own(self, api_client, make_auth_client):
        user = UserFactory()
        own = NotificationFactory(recipient=user)
        NotificationFactory()  # boshqa user'niki

        response = make_auth_client(user).get("/api/v1/notifications/")

        assert response.status_code == 200
        assert [row["id"] for row in response.json()["results"]] == [own.id]

    def test_unread_count(self, api_client, make_auth_client):
        user = UserFactory()
        NotificationFactory(recipient=user)
        NotificationFactory(recipient=user)
        NotificationFactory(recipient=user, is_read=True)

        response = make_auth_client(user).get("/api/v1/notifications/unread-count/")

        assert response.status_code == 200
        assert response.json() == {"unread": 2}

    def test_detail(self, api_client, make_auth_client):
        user = UserFactory()
        notification = NotificationFactory(recipient=user, type=NotificationType.BOOKING_NEW)

        response = make_auth_client(user).get(f"/api/v1/notifications/{notification.id}/")

        assert response.status_code == 200
        assert response.json()["type"] == NotificationType.BOOKING_NEW

    def test_foreign_detail_404(self, api_client, make_auth_client):
        foreign = NotificationFactory()

        response = make_auth_client(UserFactory()).get(f"/api/v1/notifications/{foreign.id}/")

        assert response.status_code == 404


class TestMarkRead:
    def test_read_single(self, api_client, make_auth_client):
        user = UserFactory()
        notification = NotificationFactory(recipient=user)

        response = make_auth_client(user).post(f"/api/v1/notifications/{notification.id}/read/")

        assert response.status_code == 200
        assert response.json()["is_read"] is True
        notification.refresh_from_db()
        assert notification.is_read is True

    def test_read_foreign_404(self, api_client, make_auth_client):
        foreign = NotificationFactory()

        response = make_auth_client(UserFactory()).post(f"/api/v1/notifications/{foreign.id}/read/")

        assert response.status_code == 404

    def test_read_all(self, api_client, make_auth_client):
        user = UserFactory()
        NotificationFactory(recipient=user)
        NotificationFactory(recipient=user)

        response = make_auth_client(user).post("/api/v1/notifications/read-all/")

        assert response.status_code == 200
        assert response.json() == {"updated": 2}
        assert user.notifications.filter(is_read=False).count() == 0
