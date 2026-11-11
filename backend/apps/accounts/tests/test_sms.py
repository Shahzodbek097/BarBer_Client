"""Bosqich 3: SMS adapter testlari (console/eskiz)."""

from unittest.mock import Mock, patch

import pytest
from django.test import override_settings

from apps.accounts.services import sms as sms_module
from apps.accounts.services.sms import (
    ConsoleSMSClient,
    EskizSMSClient,
    SMSError,
    get_sms_client,
)

pytestmark = pytest.mark.django_db


class TestSMSFactory:
    def test_default_provider_is_console(self):
        client = get_sms_client()

        assert isinstance(client, ConsoleSMSClient)

    @override_settings(SMS_PROVIDER="eskiz")
    def test_eskiz_provider_selected(self):
        client = get_sms_client()

        assert isinstance(client, EskizSMSClient)

    def test_console_client_sends_to_log(self, caplog):
        ConsoleSMSClient().send("+998901234567", "kod: 12345")

        assert any("[SMS console] +998901234567" in m.message for m in caplog.records)


class TestEskizClient:
    def test_send_success_caches_token(self, settings):
        settings.SMS_ESKIZ_EMAIL = "test@eskiz.uz"
        settings.SMS_ESKIZ_PASSWORD = "parol"

        client = EskizSMSClient()
        login_resp = Mock(status_code=200, json=lambda: {"data": {"token": "tok-1"}})
        send_resp = Mock(status_code=200)

        with patch.object(sms_module.requests, "post") as post_mock:
            post_mock.side_effect = [login_resp, send_resp, send_resp]

            client.send("+998901234567", "kod: 12345")
            client.send("+998901234568", "kod: 54321")  # token keshdan

        assert post_mock.call_count == 3  # 1 auth + 2 send — qayta login yo'q
        auth_call, send_call, send_call2 = post_mock.call_args_list
        assert auth_call.args[0].endswith("/auth/login")
        assert send_call.args[0].endswith("/message/sms/send")
        assert send_call.kwargs["headers"] == {"Authorization": "Bearer tok-1"}
        assert send_call2.kwargs["headers"] == {"Authorization": "Bearer tok-1"}
        assert send_call2.kwargs["json"]["mobile_phone"] == "998901234568"

    def test_auth_failure_raises_sms_error(self):
        client = EskizSMSClient()
        bad_resp = Mock(status_code=401)

        with patch.object(sms_module.requests, "post") as post_mock:
            post_mock.return_value = bad_resp

            with pytest.raises(SMSError):
                client.send("+998901234567", "kod: 12345")

    def test_missing_credentials_raises(self, settings):
        settings.SMS_ESKIZ_EMAIL = ""
        settings.SMS_ESKIZ_PASSWORD = ""

        with pytest.raises(SMSError):
            EskizSMSClient()._auth_token()
