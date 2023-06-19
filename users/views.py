import os
import requests

from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny

from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from .models import CustomUser
from . import serializers
import traceback

# db 삭제 귀찮을 시 그냥 아래 2줄 활성화 시켜, user를 삭제하세요
# user = CustomUser.objects.all()
# user.delete()


def google_auth(request):
    """로그인 페이지"""
    return render(request, "index.html")


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = serializers.CustomTokenObtainPairSerializer

# class DevUsersDeletedView(APIView):
#     """개발용 User DB 전체 삭제, ##사용시 주의##"""
#     def get(self, request):
#         user = CustomUser.objects.all()
#         user.delete()
#         return Response({"msg":"Users_all_deleted"},status=status.HTTP_200_OK)

class UserActivate(APIView):
    """이메일 인증"""

    def get(self, request, uidb64, email):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = get_object_or_404(CustomUser, pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None
        try:
            if user is not None and user.email:
                user.is_active = True
                user.save()
                return render(request, "conform.html")
            else:
                return Response(status=status.HTTP_408_REQUEST_TIMEOUT)

        except Exception as e:
            print(traceback.format_exc())


class UserSignupView(APIView):
    def post(self, request):
        """회원 가입"""
        try:
            created = request.data.get('email')
            CustomUser.objects.get(email=created)
            return Response({"msg":"already exist eamil account"}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            serializer = serializers.CreateUserSerializer(data=request.data)
            if serializer.is_valid():
                try:
                    with transaction.atomic():
                        user = serializer.save()
                        serializer = serializers.UserSerializer(user)
                        return Response(serializer.data, status=status.HTTP_200_OK)
                except Exception:
                    raise ValueError("회원가입에 실패했습니다.")
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class UserEmailValidationView(APIView):
    def post(self, request, *args, **kwargs):
        """유저 이메일 중복 검사"""
        try:
            created = request.data.get('email')
            CustomUser.objects.get(email=created)
            return Response({"msg":"already exist eamil account"}, status=status.HTTP_400_BAD_REQUEST)
        except:
            return Response({"msg":"not exist eamil account"}, status=status.HTTP_200_OK)
        

class UserDetail(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_object(self, pk):
        """유저 오브젝트 가져오기"""
        return get_object_or_404(CustomUser, pk=pk)

    def get(self, request, pk=None):
        if pk is None:
            """전체유저 조회"""
            users = CustomUser.objects.all()
            serializer = serializers.UserSerializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            """특정 유저 조회"""
            user = self.get_object(pk)
            serializer = serializers.UserDetailSerializer(user) 
            return Response(serializer.data, status=status.HTTP_200_OK)


class Me(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """내 정보 보기"""
        user = request.user
        if user:
            serializer = serializers.UserDetailSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        """내 정보 수정"""
        user = get_object_or_404(CustomUser, id=request.user.id)
        serial = serializers.UpdateUserSerializer(user, data=request.data)
        if serial.is_valid():
            serial.save()
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request):
        """비밀번호 변경"""
        user = request.user
        data = request.data
        serializer = serializers.UserPasswordUpdateSerializer(user, data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    serializer = serializers.UserSerializer(user)
                    return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception:
                raise ValueError("비밀번호 변경에 실패했습니다.")
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """회원 탈퇴"""
        user = get_object_or_404(CustomUser, id=request.user.id)
        user.is_active = False
        user.save()
        return Response(status=status.HTTP_200_OK)


class UserLikes(APIView):
    def post(self, request, pk=None):
        """좋아하는 유저 구독"""
        you = get_object_or_404(CustomUser, id=pk)
        me = request.user
        if me in you.likes.all():
            you.likes.remove(me)
            return Response(status=status.HTTP_200_OK)
        else:
            you.likes.add(me)
            return Response(status=status.HTTP_201_CREATED)


class KaKaoLogin(APIView):
    def post(self, request):
        """카카오 로그인"""
        code = request.data.get("code", None)
        token_url = f"https://kauth.kakao.com/oauth/token"

        # ✅ 자신이 설정한 redirect_uri를 할당
        redirect_uri = ""

        if code is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        response = requests.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": os.environ.get("KAKAO_API_KEY"),
                "redirect_uri": redirect_uri,
                "code": code,
                "client_secret": os.environ.get("KAKAO_CLIENT_SECRET"),
            },
            headers={"Content-type": "application/x-www-form-urlencoded;charset=utf-8"},
        )

        access_token = response.json().get("access_token")
        user_url = "https://kapi.kakao.com/v2/user/me"
        response = requests.get(
            user_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-type": "application/x-www-form-urlencoded;charset=utf-8",
            },
        )
        user_data = response.json()
        kakao_account = user_data.get("kakao_account")
        profile = kakao_account.get("profile")

        if not kakao_account.get("is_email_valid") and not kakao_account.get(
            "is_email_verified"
        ):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        user_email = kakao_account.get("email")

        try:
            user = CustomUser.objects.get(email=user_email)
            refresh_token = serializers.CustomTokenObtainPairSerializer.get_token(user)

            return Response(
                {
                    "refresh": str(refresh_token),
                    "access": str(refresh_token.access_token),
                }
            )

        except CustomUser.DoesNotExist:
            user = CustomUser.objects.create_user(email=user_email)
            user.set_unusable_password()
            user.nickname = profile.get("nickname", f"user#{user.pk}")
            user.avatar = profile.get("thumbnail_image_url", None)
            user.save()

            refresh_token = serializers.CustomTokenObtainPairSerializer.get_token(user)

            return Response(
                {
                    "refresh": str(refresh_token),
                    "access": str(refresh_token.access_token),
                }
            )


class GithubLogin(APIView):
    def post(self, request):
        """깃헙 로그인"""
        code = request.data.get("code", None)
        token_url = "https://github.com/login/oauth/access_token"

        # ✅ 자신이 설정한 redirect_uri를 할당
        redirect_uri = ""

        if code is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        response = requests.post(
            token_url,
            data={
                "client_id": os.environ.get("GH_CLIENT_ID"),
                "client_secret": os.environ.get("GH_CLIENT_SECRET"),
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={
                "Accept": "application/json",
            },
        )

        access_token = response.json().get("access_token")
        user_url = "https://api.github.com/user"
        user_email_url = "https://api.github.com/user/emails"

        response = requests.get(
            user_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        user_data = response.json()
        response = requests.get(
            user_email_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        user_emails = response.json()

        user_email = None
        for email_data in user_emails:
            if email_data.get("primary") and email_data.get("verified"):
                user_email = email_data.get("email")

        try:
            user = CustomUser.objects.get(email=user_email)
            refresh_token = serializers.CustomTokenObtainPairSerializer.get_token(user)

            return Response(
                {
                    "refresh": str(refresh_token),
                    "access": str(refresh_token.access_token),
                }
            )

        except CustomUser.DoesNotExist:
            user = CustomUser.objects.create_user(email=user_email)
            user.nickname = user_data.get("login", f"user#{user.pk}")
            user.avatar = user_data.get("avatar_url", None)
            user.set_unusable_password()
            user.save()

            refresh_token = serializers.CustomTokenObtainPairSerializer.get_token(user)

            return Response(
                {
                    "refresh": str(refresh_token),
                    "access": str(refresh_token.access_token),
                }
            )


class GoogleLogin(APIView):
    def post(self, request):
        pass
