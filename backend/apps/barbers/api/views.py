"""Sartarosh kabineti API viewlari (bosqich 5).

Barchasi `IsBarber` — izolyatsiya: faqat O'Z profil/jadval/xizmatlari
(`get_object_or_404(..., barber__user=request.user)` + service tekshiruvi).
"""

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsBarber
from apps.barbers.api.serializers import (
    BarberProfileSerializer,
    BarberServiceSerializer,
    BarberServiceWriteSerializer,
    BreakCreateSerializer,
    DayOffCreateSerializer,
    DayOffSerializer,
    ProfileCreateSerializer,
    ProfileUpdateSerializer,
    ScheduleBreakSerializer,
    StatusToggleSerializer,
    WeekSchedulePutSerializer,
)
from apps.barbers.services import cabinet
from apps.schedule.models import DayOff, ScheduleBreak
from apps.services.models import Service


class BarberProfileView(APIView):
    """GET/POST/PATCH /barber/profile/ — sartarosh profili (onboarding)."""

    permission_classes = [IsBarber]

    def get(self, request):
        profile = cabinet.get_profile(request.user)
        if profile is None:
            raise NotFound("Sartarosh profili topilmadi.")
        return Response(BarberProfileSerializer(profile).data)

    def post(self, request):
        serializer = ProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = cabinet.create_profile(
            request.user,
            bio=serializer.validated_data["bio"],
            experience_years=serializer.validated_data["experience_years"],
        )
        return Response(BarberProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if "specialties" in data:
            from apps.services.models import ServiceCategory

            data["specialties"] = ServiceCategory.objects.filter(pk__in=data["specialties"])
        profile = cabinet.update_profile(request.user, data=data)
        return Response(BarberProfileSerializer(profile).data)


class BarberServiceViewSet(viewsets.ModelViewSet):
    """CRUD /barber/services/ — sartaroshning O'Z xizmatlari."""

    serializer_class = BarberServiceSerializer
    permission_classes = [IsBarber]

    def get_queryset(self):
        profile = cabinet.get_profile(self.request.user)
        if profile is None:
            return Service.objects.none()
        return Service.objects.filter(owner_type="barber", barber=profile).order_by("name")

    def get_object(self):
        return get_object_or_404(self.get_queryset(), pk=self.kwargs["pk"])

    def create(self, request, *args, **kwargs):
        serializer = BarberServiceWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = cabinet.create_service(request.user, data=serializer.validated_data)
        return Response(BarberServiceSerializer(service).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        service = self.get_object()
        serializer = BarberServiceWriteSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(service, field, value)
        service.save()
        return Response(BarberServiceSerializer(service).data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete: navbatlar PROTECT — xizmat nofaol qilinadi."""
        service = self.get_object()
        service.is_active = False
        service.save(update_fields=("is_active",))
        return Response(status=status.HTTP_204_NO_CONTENT)


class WeekScheduleView(APIView):
    """GET/PUT /barber/schedule/ — haftalik jadval."""

    permission_classes = [IsBarber]

    def get(self, request):
        return Response(
            WeekSchedulePutSerializer({"schedule": cabinet.week_schedule(request.user)}).data
        )

    def put(self, request):
        serializer = WeekSchedulePutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cabinet.replace_week_schedule(request.user, rows=serializer.validated_data["schedule"])
        return Response(
            WeekSchedulePutSerializer({"schedule": cabinet.week_schedule(request.user)}).data
        )


class BreakViewSet(viewsets.GenericViewSet):
    """GET/POST/DELETE /barber/schedule/breaks/ — tanaffuslar."""

    permission_classes = [IsBarber]

    def get_queryset(self):
        return ScheduleBreak.objects.filter(schedule__barber__user=self.request.user)

    def list(self, request, *args, **kwargs):
        data = ScheduleBreakSerializer(
            self.get_queryset().order_by("schedule__weekday", "start_time"), many=True
        ).data
        return Response(data)

    def create(self, request, *args, **kwargs):
        serializer = BreakCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        break_obj = cabinet.add_break(
            request.user,
            weekday=serializer.validated_data["weekday"],
            start_time=serializer.validated_data["start_time"],
            end_time=serializer.validated_data["end_time"],
        )
        return Response(ScheduleBreakSerializer(break_obj).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, *args, **kwargs):
        cabinet.remove_break(request.user, break_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DayOffViewSet(viewsets.GenericViewSet):
    """GET/POST/DELETE /barber/day-offs/ — dam olish kunlari."""

    permission_classes = [IsBarber]

    def get_queryset(self):
        return DayOff.objects.filter(barber__user=self.request.user).order_by("date")

    def list(self, request, *args, **kwargs):
        return Response(DayOffSerializer(self.get_queryset(), many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = DayOffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day_off = cabinet.add_day_off(
            request.user,
            day=serializer.validated_data["date"],
            reason=serializer.validated_data["reason"],
        )
        return Response(DayOffSerializer(day_off).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None, *args, **kwargs):
        cabinet.remove_day_off(request.user, day_off_id=pk)
        return Response(status=status.HTTP_204_NO_CONTENT)


class BarberStatusView(APIView):
    """POST /barber/status/ — Faol/Nofaol tugmasi."""

    permission_classes = [IsBarber]

    def post(self, request):
        serializer = StatusToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = cabinet.set_active_now(
            request.user, is_active=serializer.validated_data["is_active"]
        )
        return Response({"is_active_now": profile.is_active_now})
