from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
import requests
from rest_framework_simplejwt.tokens import RefreshToken
import logging
import os

from .models import UserProfile, Category, FoodItem, Order, Review, HotelSetting
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    FoodItemSerializer, OrderSerializer, ReviewSerializer, HotelSettingSerializer
)

logger = logging.getLogger(__name__)
class IsAdminUserOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'admin'

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def upload_avatar(self, request):
        profile = request.user.profile
        if 'avatar' in request.FILES:
            profile.avatar_url = request.FILES['avatar']
            profile.save()
            return Response({'avatar_url': profile.avatar_url.url}, status=status.HTTP_200_OK)
        return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all().order_by('sort_order')
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUserOrReadOnly]

class FoodItemViewSet(viewsets.ModelViewSet):
    queryset = FoodItem.objects.all().order_by('-rating')
    serializer_class = FoodItemSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'admin':
            return Order.objects.all().order_by('-created_at')
        return Order.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class HotelSettingViewSet(viewsets.ModelViewSet):
    queryset = HotelSetting.objects.all()
    serializer_class = HotelSettingSerializer
    permission_classes = [IsAdminUserOrReadOnly]

class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Token is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify the access token by fetching user info from Google
            response = requests.get(
                'https://www.googleapis.com/oauth2/v3/userinfo',
                headers={'Authorization': f'Bearer {token}'}
            )

            if response.status_code != 200:
                logger.error(f"Google UserInfo Error: {response.text}")
                return Response({'error': 'Invalid or expired Google token'}, status=status.HTTP_400_BAD_REQUEST)

            idinfo = response.json()
            email = idinfo.get('email')
            if not email:
                return Response({'error': 'Google token did not contain an email'}, status=status.HTTP_400_BAD_REQUEST)

            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name
                }
            )

            refresh = RefreshToken.for_user(user)

            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Google Token Verification Error: {e}")
            return Response({'error': 'Error verifying token'}, status=status.HTTP_400_BAD_REQUEST)
