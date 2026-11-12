"""Super admin API (bosqich 5): salon moderatsiyasi va umumiy statistika.

Config darajasida — moderatsiya salons servisi orqali, statistika
bookings servisi orqali bajariladi (import yo'nalishi qoidasi: config
barcha app'lardan yuqorida, bu modul faqat services chaqiradi).
"""

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSuperAdmin
from apps.bookings.services import stats as stats_service
from apps.salons.models import Salon, SalonStatus
from apps.salons.services import moderation


class AdminSalonSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source="owner.full_name", read_only=True)
    region_name = serializers.CharField(source="region.name", read_only=True)

    class Meta:
        model = Salon
        fields = (
            "id",
            "name",
            "owner",
            "owner_name",
            "region_name",
            "status",
            "created_at",
        )
        read_only_fields = fields


class AdminSalonListView(APIView):
    """GET /admin/salons/?status= — barcha salonlar (moderatsiya ro'yxati)."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        qs = Salon.objects.select_related("owner", "region").order_by("-created_at")
        salon_status = request.query_params.get("status")
        if salon_status:
            if salon_status not in SalonStatus.values:
                return Response({"detail": "Noma'lum holat."}, status=status.HTTP_400_BAD_REQUEST)
            qs = qs.filter(status=salon_status)
        return Response(AdminSalonSerializer(qs, many=True).data)


class AdminSalonApproveView(APIView):
    """POST /admin/salons/{id}/approve/ — PENDING → APPROVED."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        salon = moderation.approve_salon(pk)
        return Response(AdminSalonSerializer(salon).data)


class AdminSalonBlockView(APIView):
    """POST /admin/salons/{id}/block/ — → BLOCKED."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, pk: int):
        salon = moderation.block_salon(pk)
        return Response(AdminSalonSerializer(salon).data)


class AdminStatsView(APIView):
    """GET /admin/stats/ — umumiy hisoblar."""

    permission_classes = [IsSuperAdmin]

    def get(self, request):
        return Response(stats_service.global_stats())
