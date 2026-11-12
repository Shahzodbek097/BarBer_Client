"""Sharh API (bosqich 5)."""

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsClient
from apps.reviews.models import Review
from apps.reviews.services import reviews as review_service


class ReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    service_name = serializers.CharField(
        source="appointment.service.name", read_only=True, default=""
    )

    class Meta:
        model = Review
        fields = (
            "id",
            "rating",
            "comment",
            "barber_reply",
            "client_name",
            "service_name",
            "created_at",
        )


class ReviewCreateSerializer(serializers.Serializer):
    appointment = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ReviewCreateView(APIView):
    """POST /reviews/ — mijoz bajarilgan navbatga sharh yozadi."""

    permission_classes = [IsClient]

    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = review_service.create_review(
            request.user,
            appointment_id=serializer.validated_data["appointment"],
            rating=serializer.validated_data["rating"],
            comment=serializer.validated_data["comment"],
        )
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class BarberReviewsView(APIView):
    """GET /reviews/barber/{barber_id}/ — sartarosh sharhlari (ochiq)."""

    permission_classes = [AllowAny]

    def get(self, request, barber_id: int):
        from apps.barbers.models import BarberProfile

        barber = get_object_or_404(BarberProfile, pk=barber_id, is_deleted=False)
        qs = review_service.barber_reviews(barber.pk)
        return Response(ReviewSerializer(qs, many=True).data)
