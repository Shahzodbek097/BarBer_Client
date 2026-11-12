"""Katalog API (bosqich 5): viloyatlar, salonlar, sartaroshlar, slotlar.

Bu view'lar `bookings` app'ida — chunki slotlar hisoblashi bookings
qatlamidagi servis(e)lardan foydalanadi va katalog barcha pastdagi
app'larni (core, salons, barbers, services) o'qiy oladi.

Barcha endpointlar ochiq (AllowAny) — faqat APPROVED holatdagi
salon/sartaroshlar ko'rinadi (moderatsiya).
"""

from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.barbers.models import BarberProfile, BarberStatus
from apps.bookings.services import appointments as appt_service
from apps.core.models import District, Region
from apps.salons.models import Salon, SalonStatus
from apps.schedule.services import slots as slot_engine
from apps.services.models import Service, ServiceOwner


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ("id", "name")


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ("id", "region", "name")


class SalonSerializer(serializers.ModelSerializer):
    region_name = serializers.CharField(source="region.name", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)

    class Meta:
        model = Salon
        fields = (
            "id",
            "name",
            "slug",
            "region",
            "region_name",
            "district",
            "district_name",
            "address",
            "phone",
            "description",
            "photos",
            "work_time_start",
            "work_time_end",
            "rating_avg",
            "rating_count",
        )


class BarberSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.full_name", read_only=True)
    salon_name = serializers.CharField(source="salon.name", read_only=True, default=None)
    specialties = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = BarberProfile
        fields = (
            "id",
            "name",
            "salon",
            "salon_name",
            "experience_years",
            "bio",
            "specialties",
            "rating_avg",
            "rating_count",
            "is_active_now",
        )


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Service
        fields = (
            "id",
            "name",
            "category",
            "category_name",
            "duration_min",
            "price",
            "description",
            "owner_type",
        )


class SlotQuerySerializer(serializers.Serializer):
    """GET /catalog/barbers/{id}/slots/?service_id=&day= validatsiyasi."""

    service_id = serializers.IntegerField()
    day = serializers.DateField()


class RegionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /catalog/regions/, /catalog/regions/{id}/districts/"""

    queryset = Region.objects.filter(is_active=True)
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    @action(detail=True, methods=["get"])
    def districts(self, request, pk=None, *args, **kwargs):
        region = self.get_object()
        data = DistrictSerializer(region.districts.filter(is_active=True), many=True).data
        return Response(data)


class SalonViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /catalog/salons/?region=&district=&search="""

    serializer_class = SalonSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = Salon.objects.filter(status=SalonStatus.APPROVED, is_deleted=False).select_related(
            "region", "district"
        )
        region = self.request.query_params.get("region")
        district = self.request.query_params.get("district")
        search = self.request.query_params.get("search")
        if region:
            qs = qs.filter(region_id=region)
        if district:
            qs = qs.filter(district_id=district)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


class BarberViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """GET /catalog/barbers/?salon=&search=&is_active= + services/ + slots/"""

    serializer_class = BarberSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = (
            BarberProfile.objects.filter(status=BarberStatus.APPROVED, is_deleted=False)
            .select_related("user", "salon")
            .prefetch_related("specialties")
        )
        salon = self.request.query_params.get("salon")
        search = self.request.query_params.get("search")
        is_active = self.request.query_params.get("is_active")
        if salon:
            qs = qs.filter(salon_id=salon)
        if search:
            qs = qs.filter(user__full_name__icontains=search)
        if is_active is not None:
            qs = qs.filter(is_active_now=is_active.lower() == "true")
        return qs

    @action(detail=True, methods=["get"])
    def services(self, request, pk=None, *args, **kwargs):
        """Sartaroshning xizmatlari: o'ziniki + saloni xizmatlari."""
        barber = self.get_object()
        qs = Service.objects.filter(is_active=True).filter(
            owner_type=ServiceOwner.BARBER,
            barber=barber,
        ) | Service.objects.filter(
            is_active=True,
            owner_type=ServiceOwner.SALON,
            salon=barber.salon,
        )
        return Response(ServiceSerializer(qs.order_by("name"), many=True).data)

    @action(detail=True, methods=["get"])
    def slots(self, request, pk=None, *args, **kwargs):
        """Bo'sh slotlar: ?service_id=&day= — dvigatel + band navbatlar."""
        barber = self.get_object()
        query = SlotQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        service = Service.objects.filter(
            pk=query.validated_data["service_id"], is_active=True
        ).first()
        if service is None or not _service_belongs_to_barber(service, barber):
            return Response(
                {"detail": "Xizmat ushbu sartaroshga tegishli emas."},
                status=400,
            )

        day = query.validated_data["day"]
        result = slot_engine.available_slots(
            barber, day, service.duration_min, busy=appt_service.busy_intervals(barber, day)
        )
        return Response([{"start": s.start.isoformat(), "end": s.end.isoformat()} for s in result])


def _service_belongs_to_barber(service: Service, barber: BarberProfile) -> bool:
    """Barber xizmati yoki saloni xizmati bo'lishini tekshiradi."""
    if service.owner_type == ServiceOwner.BARBER:
        return service.barber_id == barber.id
    return barber.salon_id is not None and service.salon_id == barber.salon_id
