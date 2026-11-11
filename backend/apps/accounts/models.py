"""Foydalanuvchi va OTP modellari (bosqich 2).

Auth logikasi (OTP yuborish, JWT) bosqich 3-da services/ qatlamida qo'shiladi.
Bu fayl faqat ma'lumot tuzilishi va asosiy manager'larni saqlaydi.
"""

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models


class UserManager(BaseUserManager):
    """Telefon raqam asosida ishlaydigan user manager."""

    use_in_migrations = True

    def _create_user(self, phone, full_name="", password=None, **extra_fields):
        if not phone or not phone.strip():
            raise ValueError("Telefon raqam majburiy.")
        phone = phone.strip()
        user = self.model(phone=phone, full_name=full_name or "", **extra_fields)
        if password:
            user.set_password(password)
        else:
            # OTP-autentifikatsiya: parol bo'lmasa foydalanilmagan parol beriladi
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, phone, full_name="", password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, full_name, password, **extra_fields)

    def create_superuser(self, phone, full_name="", password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", self.model.Role.SUPERADMIN)
        extra_fields.setdefault("is_verified", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser uchun is_staff=True bo'lishi kerak.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser uchun is_superuser=True bo'lishi kerak.")

        return self._create_user(phone, full_name, password, **extra_fields)


class User(AbstractUser):
    """Platforma foydalanuvchisi. Telefon — login identifikatori.

    Rollar izolyatsiyasi (TZ 1.3): har rol alohida interfeys oladi,
    ma'lumotlar QuerySet darajasida filtralanadi (bosqich 3 permissions).
    """

    class Role(models.TextChoices):
        CLIENT = "client", "Mijoz"
        BARBER = "barber", "Sartarosh"
        SALON_ADMIN = "salon_admin", "Salon egasi"
        SUPERADMIN = "superadmin", "Super admin"

    class Lang(models.TextChoices):
        UZ = "uz", "O'zbek"
        RU = "ru", "Rus"
        EN = "en", "Ingliz"

    username = None
    phone = models.CharField("Telefon raqam", max_length=20, unique=True)
    full_name = models.CharField("To'liq ism", max_length=255, blank=True, default="")
    role = models.CharField(
        "Rol", max_length=20, choices=Role.choices, default=Role.CLIENT, db_index=True
    )
    avatar = models.ImageField("Avatar", upload_to="avatars/", null=True, blank=True)
    lang = models.CharField("Interfeys tili", max_length=3, choices=Lang.choices, default=Lang.UZ)
    is_verified = models.BooleanField("OTP bilan tasdiqlangan", default=False)
    is_blocked = models.BooleanField("Bloklangan", default=False)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        return self.full_name or self.phone

    @property
    def is_client(self):
        return self.role == self.Role.CLIENT

    @property
    def is_barber(self):
        return self.role == self.Role.BARBER

    @property
    def is_salon_admin(self):
        return self.role == self.Role.SALON_ADMIN


class OTPPurpose(models.TextChoices):
    REGISTRATION = "registration", "Ro'yxatdan o'tish"
    LOGIN = "login", "Kirish"
    PASSWORD_RESET = "password_reset", "Parolni tiklash"


class OTPCode(models.Model):
    """Telefonga yuborilgan tasdiqlash kodi (xavfsizlik: faqat hash saqlanadi)."""

    phone = models.CharField("Telefon raqam", max_length=20)
    code_hash = models.CharField("Kod hashi (sha256)", max_length=64)
    purpose = models.CharField("Maqsad", max_length=20, choices=OTPPurpose.choices)
    expires_at = models.DateTimeField("Amal qilish muddati")
    attempts = models.PositiveSmallIntegerField("Urinishlar soni", default=0)
    is_used = models.BooleanField("Ishlatilgan", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "OTP kod"
        verbose_name_plural = "OTP kodlar"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("phone", "purpose", "is_used")),
        ]

    def __str__(self):
        return f"{self.phone} ({self.purpose})"
