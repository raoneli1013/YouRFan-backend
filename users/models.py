from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None):
        user = self.create_user(
            email,
            password=password,
        )
        user.is_admin = True
        user.is_active = True
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class CustomUser(AbstractUser):
    class UserTypeChoices(models.TextChoices):
        KAKAO = (
            "kakao",
            "카카오",
        )
        GITHUB = (
            "github",
            "깃허브",
        )
        GOOGLE = (
            "google",
            "구글",
        )
        NORMAL = (
            "normal",
            "일반",
        )

    username = models.CharField(max_length=255)
    email = models.EmailField(
        max_length=255,
        unique=True,
    )
    nickname = models.CharField(
        "닉네임",
        max_length=255,
        null=True,
    )
    avatar = models.URLField(blank=True)
    user_type = models.CharField(
        max_length=15,
        choices=UserTypeChoices.choices,
        default="NORMAL",
    )

    is_writer = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name_plural = "회원들"

    def activate(self):
        self.is_active = True
        self.save()
        return self
