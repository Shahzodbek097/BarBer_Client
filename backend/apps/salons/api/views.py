"""Salon egasi API viewlari (bosqich 5): profil va o'z sartaroshlari."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsSalonAdmin
from apps.salons.api.serializers import (
    SalonBarberSerializer,
    SalonProfileSerializer,
    SalonUpdateSerializer,
)
from apps.salons.services import profile as salon_service


class SalonProfileView(APIView):
    """GET/PATCH /salon/profile/ — salon egasining o'z profili."""

    permission_classes = [IsSalonAdmin]

    def get(self, request):
        salon = salon_service.get_own_salon(request.user)
        if salon is None:
            return Response(
                {"detail": "Salon profili topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(SalonProfileSerializer(salon).data)

    def patch(self, request):
        serializer = SalonUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        salon = salon_service.update_salon(request.user, data=serializer.validated_data)
        return Response(SalonProfileSerializer(salon).data)


class SalonBarbersView(APIView):
    """GET /salon/barbers/ — o'z salonidagi sartaroshlar."""

    permission_classes = [IsSalonAdmin]

    def get(self, request):
        salon = salon_service.get_own_salon(request.user)
        if salon is None:
            return Response(
                {"detail": "Salon profili topilmadi."}, status=status.HTTP_404_NOT_FOUND
            )
        barbers = salon.barbers.select_related("user").prefetch_related("specialties")
        return Response(SalonBarberSerializer(barbers, many=True).data)
