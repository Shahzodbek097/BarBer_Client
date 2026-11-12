"""Xabarnoma API viewlari (bosqich 5) — faqat O'Z xabarlari."""

from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "type", "title", "body", "link", "is_read", "created_at")
        read_only_fields = fields


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /notifications/, /notifications/{id}/read/, /read-all/, /unread-count/"""

    serializer_class = NotificationSerializer

    def get_queryset(self):
        """IDOR himoyasi: recipient=request.user."""
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None, *args, **kwargs):
        """POST /notifications/{id}/read/ — bittasini o'qilgan qilish."""
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=("is_read",))
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request, *args, **kwargs):
        """POST /notifications/read-all/ — barchasini o'qilgan qilish."""
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request, *args, **kwargs):
        """GET /notifications/unread-count/ — badge uchun."""
        total = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": total})
