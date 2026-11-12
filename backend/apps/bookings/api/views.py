"""Navbat API viewlari (bosqich 5) — logika yo'q, faqat services chaqiradi.

Ruxsatlar (plan §5):
- mijoz: create, my, cancel, reschedule
- sartarosh: incoming, confirm, reject, propose, complete, no-show, manual
- retrieve: faqat ishtirokchilar (mijoz yoki sartarosh) — IDOR himoyasi
  service qatlamidagi egalik tekshiruvi bilan birga (ikki qatlam).
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import User
from apps.accounts.permissions import IsBarber, IsClient
from apps.bookings.api.serializers import (
    AppointmentSerializer,
    BookingCreateSerializer,
    BookingFilterSerializer,
    ManualBookingSerializer,
    ProposeSerializer,
    RejectSerializer,
    RescheduleSerializer,
)
from apps.bookings.models import Appointment
from apps.bookings.services import appointments as appt_service


class BookingViewSet(viewsets.GenericViewSet):
    """`/api/v1/bookings/` — navbat oqimi (OTP'li user'lar uchun)."""

    queryset = Appointment.objects.select_related("client", "barber__user", "service", "salon")
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ("create", "my"):
            permission_classes = [IsClient]
        elif self.action in (
            "incoming",
            "manual",
            "confirm",
            "reject",
            "propose",
            "complete",
            "no_show",
        ):
            permission_classes = [IsBarber]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def _get_participant_appointment(self) -> Appointment:
        """retrieve/cancel/reschedule: faqat ishtirokchi navbatini ko'radi."""
        user = self.request.user
        qs = self.get_queryset().filter(Q(client=user) | Q(barber__user=user))
        return get_object_or_404(qs, pk=self.kwargs["pk"])

    def retrieve(self, request, *args, **kwargs):
        """GET /bookings/{id}/ — faqat ishtirokchi."""
        appointment = self._get_participant_appointment()
        return Response(AppointmentSerializer(appointment).data)

    # --- mijoz ---

    def create(self, request, *args, **kwargs):
        """POST /bookings/ — yangi navbat (mijoz)."""
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = appt_service.create_appointment(
            client=request.user,
            barber=serializer.validated_data["barber"],
            service=serializer.validated_data["service"],
            day=serializer.validated_data["date"],
            start_time=serializer.validated_data["start_time"],
            note=serializer.validated_data["note"],
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request, *args, **kwargs):
        """GET /bookings/my/ — mijozning navbatlari (?status=)."""
        flt = BookingFilterSerializer(data=request.query_params)
        flt.is_valid(raise_exception=True)
        qs = appt_service.list_client_appointments(
            request.user, status=flt.validated_data.get("status") or ""
        )
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(AppointmentSerializer(page, many=True).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/cancel/ — mijoz yoki sartarosh."""
        appointment = self._get_participant_appointment()
        appt_service.cancel(appointment, by=request.user)
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"])
    def reschedule(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/reschedule/ — mijoz vaqtni o'zgartiradi."""
        serializer = RescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self._get_participant_appointment()
        appt_service.reschedule(
            appointment,
            by=request.user,
            day=serializer.validated_data["date"],
            start_time=serializer.validated_data["start_time"],
        )
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    # --- sartarosh ---

    @action(detail=False, methods=["get"])
    def incoming(self, request, *args, **kwargs):
        """GET /bookings/incoming/ — sartarosh navbatlari (?status=&day=)."""
        flt = BookingFilterSerializer(data=request.query_params)
        flt.is_valid(raise_exception=True)
        qs = appt_service.list_barber_appointments(
            request.user,
            status=flt.validated_data.get("status") or "",
            day=flt.validated_data.get("day"),
        )
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(AppointmentSerializer(page, many=True).data)

    @action(detail=False, methods=["post"], url_path="manual")
    def manual(self, request, *args, **kwargs):
        """POST /bookings/manual/ — orxonadagi mijozga qo'lda navbat."""
        serializer = ManualBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        barber = getattr(request.user, "barber_profile", None)
        if barber is None:
            return Response(
                {"detail": "Sartarosh profili topilmadi."}, status=status.HTTP_400_BAD_REQUEST
            )
        appointment = appt_service.create_appointment(
            client=User.objects.get(phone=serializer.validated_data["client_phone"]),
            barber=barber,
            service=serializer.validated_data["service"],
            day=serializer.validated_data["date"],
            start_time=serializer.validated_data["start_time"],
            note=serializer.validated_data["note"],
            source="manual",
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/confirm/ — sartarosh tasdiqlaydi."""
        appointment = self._get_participant_appointment()
        appt_service.confirm(appointment, by=request.user)
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/reject/ — sartarosh rad etadi."""
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self._get_participant_appointment()
        appt_service.reject(appointment, by=request.user, reply=serializer.validated_data["reply"])
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"])
    def propose(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/propose/ — boshqa vaqt taklif qiladi."""
        serializer = ProposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appointment = self._get_participant_appointment()
        appt_service.propose_new_time(
            appointment,
            by=request.user,
            day=serializer.validated_data["date"],
            start_time=serializer.validated_data["start_time"],
        )
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/complete/ — xizmat bajarildi."""
        appointment = self._get_participant_appointment()
        appt_service.complete(appointment, by=request.user)
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)

    @action(detail=True, methods=["post"], url_path="no-show")
    def no_show(self, request, pk=None, *args, **kwargs):
        """POST /bookings/{id}/no-show/ — mijoz kelmadi."""
        appointment = self._get_participant_appointment()
        appt_service.mark_no_show(appointment, by=request.user)
        appointment.refresh_from_db()
        return Response(AppointmentSerializer(appointment).data)
