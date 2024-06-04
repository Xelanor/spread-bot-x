import json
from django.contrib.auth import get_user_model, authenticate
from rest_framework import generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.settings import api_settings
from rest_framework.response import Response
from rest_framework import serializers

from rest_framework_simplejwt.views import TokenObtainPairView

from user.serializers import (
    UserSerializer,
    AuthTokenSerializer,
    MyTokenObtainPairSerializer,
)


class CreateUserView(generics.CreateAPIView):
    """Create a new user in the system"""

    serializer_class = UserSerializer


class LoginUserView(generics.CreateAPIView):
    """Create a new user in the system"""

    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid(raise_exception=False):
            serializer.save()

        user = authenticate(
            username=request.data["email"], password=request.data["password"]
        )
        if user:
            token = str(MyTokenObtainPairSerializer.get_token(user).access_token)
            return Response({"token": token})
        else:
            msg = "Hatalı Şifre"
            raise serializers.ValidationError(msg, code="authentication")


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""

    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
