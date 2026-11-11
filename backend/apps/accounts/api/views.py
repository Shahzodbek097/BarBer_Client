"""Auth API viewlari — logika yo'q, faqat services chaqiradi (plan qoidasi).

Oqim (OTP -> JWT):
1. POST register   {phone, full_name, role} -> SMS kod (ro'yxatdan o'tish)
2. POST login      {phone}                 -> SMS kod (kirish)
3. POST verify-otp {phone, purpose, code}  -> access + refresh + user
4. POST refresh    {refresh}               -> yangi juftlik (rotation + blacklist)
5. POST logout     {refresh}               -> refresh blacklist'ga
6. GET  me                                 -> joriy user (Bearer)
"""

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.api.serializers import (
    MeUpdateSerializer,
    RegisterSerializer,
    RequestOTPSerializer,
    UserSerializer,
    VerifyOTPSerializer,
)
from apps.accounts.models import User
from apps.accounts.services import auth as auth_service
from apps.accounts.services import otp as otp_service


def _debug_code(data: dict, code: str | None) -> dict:
    """Dev qulayligi: faqat DEBUG + console provayderda kod javobga qo'shiladi."""
    if code and settings.DEBUG and settings.SMS_PROVIDER == "console":
        return {**data, "debug_code": code}
    return data


class RegisterView(APIView):
    """POST /api/v1/auth/register/"""

    permission_classes = [AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, code = auth_service.register_user(
            phone=serializer.validated_data["phone"],
            full_name=serializer.validated_data["full_name"],
            role=serializer.validated_data["role"],
        )
        data = {
            "detail": "Tasdiqlash kodi SMS orqali yuborildi.",
            "phone": user.phone,
        }
        return Response(_debug_code(data, code), status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/v1/auth/login/ — OTP yuboradi (tokenlar verify-otp'dan keyin)."""

    permission_classes = [AllowAny]
    throttle_scope = "otp"

    def post(self, request):
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = auth_service.send_login_otp(serializer.validated_data["phone"])
        data = {"detail": "Kirish kodi SMS orqali yuborildi."}
        return Response(_debug_code(data, code))


class VerifyOTPView(APIView):
    """POST /api/v1/auth/verify-otp/ — kod o'tsa JWT juftligi qaytaradi."""

    permission_classes = [AllowAny]
    throttle_scope = "otp_verify"

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = otp_service.verify_otp(
            phone=serializer.validated_data["phone"],
            purpose=serializer.validated_data["purpose"],
            code=serializer.validated_data["code"],
        )
        tokens = auth_service.issue_tokens(user)
        return Response(
            {
                "access": tokens["access"],
                "refresh": tokens["refresh"],
                "user": UserSerializer(user).data,
            }
        )


class RefreshView(TokenRefreshView):
    """POST /api/v1/auth/refresh/ — rotation; bloklangan user yangilay olmaydi."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        raw_token = request.data.get("refresh", "")
        try:
            token = RefreshToken(raw_token)
        except TokenError:
            token = None  # yaroqsiz token — super() o'z xatosini qaytaradi

        if token is not None:
            user = User.objects.filter(id=token.payload.get("user_id")).first()
            if user is None:
                return Response(
                    {"detail": "Foydalanuvchi topilmadi."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if user.is_blocked or not user.is_active:
                return Response(
                    {"detail": "Hisobingiz bloklangan."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — refresh token blacklist'ga tushadi."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        raw_token = request.data.get("refresh", "")
        try:
            token = RefreshToken(raw_token)
        except TokenError:
            return Response(
                {"detail": "Refresh token yaroqsiz."}, status=status.HTTP_400_BAD_REQUEST
            )

        if token.payload.get("user_id") != str(request.user.id):
            return Response(
                {"detail": "Token sizga tegishli emas."}, status=status.HTTP_403_FORBIDDEN
            )

        token.blacklist()
        return Response({"detail": "Chiqish bajarildi."})


class MeView(APIView):
    """GET/PATCH /api/v1/auth/me/ — joriy user profili."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)
