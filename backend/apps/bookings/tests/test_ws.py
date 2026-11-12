"""Bosqich 5: WebSocket push testlari (InMemoryChannelLayer).

- JWT (?token=) auth: yaroqsiz / mos kelmagan token — ulanish yopiladi
- yangi navbat → sartarosh WS'ga push
- holat o'zgarishi → mijoz WS'ga push

Eslatma: consumer alohida event loopda ishlaydi — ORM/token chaqiruvlari
`asyncio.run`dan OLDIN (sync) bajariladi, coroutine ichidagi DB ishlari
faqat `database_sync_to_async` orqali; `transaction=True` talab qilinadi.
"""

import asyncio

import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.factories import UserFactory
from apps.barbers.factories import BarberProfileFactory
from apps.bookings.factories import AppointmentFactory
from apps.bookings.services import appointments as appt_service
from config.asgi import application

pytestmark = pytest.mark.django_db(transaction=True)

# Test kommunikatori Origin yubormaydi — brauzer esa doim yuboradi.
# OriginValidator ALLOWED_HOSTS bo'yicha tekshiradi (testserver ro'yxatda).
_WS_HEADERS = [(b"origin", b"http://testserver")]


def _access_token(user) -> str:
    return str(RefreshToken.for_user(user).access_token)


def test_client_connects_with_valid_token():
    client_user = UserFactory()
    url = f"/ws/client/{client_user.id}/?token={_access_token(client_user)}"

    async def scenario():
        communicator = WebsocketCommunicator(application, url, headers=_WS_HEADERS)
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    asyncio.run(scenario())


def test_barber_connects_with_valid_token():
    barber = BarberProfileFactory()
    url = f"/ws/barber/{barber.user_id}/?token={_access_token(barber.user)}"

    async def scenario():
        communicator = WebsocketCommunicator(application, url, headers=_WS_HEADERS)
        connected, _ = await communicator.connect()
        assert connected is True
        await communicator.disconnect()

    asyncio.run(scenario())


def test_invalid_token_closed():
    async def scenario():
        communicator = WebsocketCommunicator(application, "/ws/barber/1/?token=not-a-jwt")
        connected, _ = await communicator.connect()
        assert connected is False

    asyncio.run(scenario())


def test_missing_token_closed():
    async def scenario():
        communicator = WebsocketCommunicator(application, "/ws/client/1/")
        connected, _ = await communicator.connect()
        assert connected is False

    asyncio.run(scenario())


def test_token_user_id_mismatch_closed():
    """Token boshqa user'ga tegishli: {user_id} mos kelmasa yopiladi (IDOR)."""
    user = UserFactory()
    url = f"/ws/client/{user.id + 100000}/?token={_access_token(user)}"

    async def scenario():
        communicator = WebsocketCommunicator(application, url)
        connected, _ = await communicator.connect()
        assert connected is False

    asyncio.run(scenario())


def test_barber_receives_new_booking_push():
    barber = BarberProfileFactory()
    url = f"/ws/barber/{barber.user_id}/?token={_access_token(barber.user)}"

    async def scenario():
        communicator = WebsocketCommunicator(application, url, headers=_WS_HEADERS)
        connected, _ = await communicator.connect()
        assert connected is True

        # yangi navbat yaratiladi → signal sartaroshga push qiladi
        await database_sync_to_async(AppointmentFactory)(barber=barber)

        message = await asyncio.wait_for(communicator.receive_json_from(), timeout=5)
        assert message["type"] == "booking_new"
        assert "navbat" in message["title"].lower()

        await communicator.disconnect()

    asyncio.run(scenario())


def test_client_receives_confirm_push():
    appt = AppointmentFactory()
    barber_user = appt.barber.user
    client = appt.client
    url = f"/ws/client/{client.id}/?token={_access_token(client)}"

    async def scenario():
        communicator = WebsocketCommunicator(application, url, headers=_WS_HEADERS)
        connected, _ = await communicator.connect()
        assert connected is True

        # sartarosh tasdiqlaydi → signal mijozga push qiladi
        await database_sync_to_async(appt_service.confirm)(appt, by=barber_user)

        message = await asyncio.wait_for(communicator.receive_json_from(), timeout=5)
        assert message["type"] == "booking_confirmed"

        await communicator.disconnect()

    asyncio.run(scenario())
