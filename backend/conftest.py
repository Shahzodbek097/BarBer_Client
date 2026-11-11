"""Umumiy pytest fixture'lar (bosqich 3+ da kengaytiriladi)."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """DRF API klient (auth'siz)."""
    return APIClient()
