"""Bosqich 6: veb sahifalar smoke testlari (TemplateView 200 qaytaradi)."""

import pytest

PAGES = [
    "/",
    "/auth/",
    "/c/",
    "/barber/",
    "/barber/profile/",
    "/barber/1/",
    "/salon/",
    "/salon/1/",
    "/panel/",
    "/notifications/",
]


@pytest.mark.parametrize("url", PAGES)
def test_page_returns_200_with_skeleton(client, url):
    response = client.get(url)

    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "data-page" in body  # base.html skeleti
    assert "/static/web/css/app.css" in body
    assert "BarBer" in body


def test_index_contains_catalog_skeleton(client):
    response = client.get("/")

    assert 'id="salon-grid"' in response.content.decode("utf-8")


def test_barber_page_contains_booking_skeleton(client):
    body = client.get("/barber/1/").content.decode("utf-8")

    assert 'id="slot-panel"' in body
    assert 'id="book-btn"' in body


def test_page_script_tag_present(client):
    """Har sahifa o'z JS modulini ulaydi (web/js/pages/...)."""
    body = client.get("/c/").content.decode("utf-8")

    assert "web/js/pages/client.js" in body
