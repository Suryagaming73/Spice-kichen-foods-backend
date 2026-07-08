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
import datetime

from .models import UserProfile, Category, FoodItem, Order, Review, HotelSetting, ContactMessage
from .serializers import (
    UserSerializer, RegisterSerializer, CategorySerializer,
    FoodItemSerializer, OrderSerializer, ReviewSerializer, HotelSettingSerializer,
    ContactMessageSerializer
)
from django.core.mail import send_mail
from django.conf import settings
from django.core.files.storage import default_storage

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

    @action(detail=False, methods=['post'], permission_classes=[IsAdminUserOrReadOnly])
    def send_offer(self, request):
        subject = request.data.get('subject')
        message = request.data.get('message')
        if not subject or not message:
            return Response({'error': 'Subject and message are required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        users = User.objects.exclude(email='')
        recipient_list = [user.email for user in users]

        # Handle image upload
        image = request.FILES.get('image')
        image_html = ""
        if image:
            # Save the image using default storage
            file_name = default_storage.save(f'offers/{image.name}', image)
            file_url = request.build_absolute_uri(default_storage.url(file_name))
            image_html = f'<div style="text-align: center; margin-bottom: 20px;"><img src="{file_url}" alt="Offer Image" style="max-width: 100%; border-radius: 8px;"></div>'

        html_message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="background-color: #1a1a1a; padding: 30px; text-align: center; border-bottom: 4px solid #ff6b35;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td align="center" style="padding-bottom: 15px;">
                            <span style="font-size: 32px; font-weight: 800; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; letter-spacing: -0.5px; display: inline-block; vertical-align: middle;">
                                <span style="font-size: 36px; margin-right: 8px;">👨‍🍳</span><span style="color: #fff;">Spice</span><span style="color: #ff6b35;">KITCHEN</span>
                            </span>
                        </td>
                    </tr>
                </table>
                <p style="color: #ff6b35; margin: 0; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;">Special Offer! 🌶️</p>
            </div>
            <div style="padding: 30px; color: #333; line-height: 1.6;">
                {image_html}
                <h2 style="color: #1a1a1a; margin-top: 0;">{subject}</h2>
                <div style="font-size: 16px;">
                    {message.replace(chr(10), '<br>')}
                </div>
                <div style="text-align: center; margin-top: 30px;">
                    <a href="https://spice-kichen-restaurant.vercel.app/" style="display: inline-block; background-color: #ff6b35; color: #fff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-weight: bold; font-size: 16px;">Claim Offer Now</a>
                </div>
            </div>
            <div style="background-color: #f1f5f9; padding: 15px; text-align: center; color: #64748b; font-size: 12px;">
                <p style="margin: 0;">&copy; {datetime.datetime.now().year if 'datetime' in globals() else 2024} Spice Kitchen. All rights reserved.</p>
                <p style="margin: 5px 0 0 0;">You are receiving this email because you registered on our platform.</p>
            </div>
        </div>
        """

        try:
            plain_message = f"Special Offer from Spice Kitchen!\n\n{subject}\n\n{message}\n\nClaim Offer Now at: https://spice-kichen-restaurant.vercel.app/"
            send_mail(
                subject=f"Spice Kitchen: {subject}",
                message=plain_message,
                from_email=f"Spice Kitchen <{settings.EMAIL_HOST_USER}>",
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            return Response({'message': f'Offer sent to {len(recipient_list)} users.'}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Failed to send offer email: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Send welcome email
            try:
                raw_password = request.data.get('password')
                html_message = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background-color: #fff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <div style="background-color: #1a1a1a; padding: 30px; text-align: center; border-bottom: 4px solid #ff6b35;">
                        <table width="100%" cellpadding="0" cellspacing="0" border="0">
                            <tr>
                                <td align="center" style="padding-bottom: 15px;">
                                    <span style="font-size: 32px; font-weight: 800; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; letter-spacing: -0.5px; display: inline-block; vertical-align: middle;">
                                        <span style="font-size: 36px; margin-right: 8px;">👨‍🍳</span><span style="color: #fff;">Spice</span><span style="color: #ff6b35;">KITCHEN</span>
                                    </span>
                                </td>
                            </tr>
                        </table>
                        <p style="color: #ff6b35; margin: 0; font-weight: bold; letter-spacing: 1px; text-transform: uppercase;">Welcome to our family! 🌶️</p>
                    </div>
                    <div style="padding: 30px; color: #333;">
                        <p style="font-size: 16px;">Hi {user.first_name},</p>
                        <p style="font-size: 16px;">Thank you for registering. Your account has been successfully created. You can now order authentic Indian cuisine directly to your doorstep.</p>
                        <div style="background-color: #f8f9fa; border-left: 4px solid #ff6b35; padding: 15px; margin: 20px 0;">
                            <p style="margin: 0 0 10px 0;"><strong>Your Login Credentials:</strong></p>
                            <p style="margin: 0 0 5px 0;">Email: <strong>{user.email}</strong></p>
                            <p style="margin: 0;">Password: <strong>{raw_password}</strong></p>
                        </div>
                        <p style="font-size: 16px;">For your security, you can change your password at any time.</p>
                        <a href="https://spice-kichen-restaurant.vercel.app/auth" style="display: inline-block; background-color: #ff6b35; color: #fff; text-decoration: none; padding: 12px 25px; border-radius: 6px; font-weight: bold; margin-top: 15px;">Order Now</a>
                    </div>
                    <div style="background-color: #f1f5f9; padding: 15px; text-align: center; color: #64748b; font-size: 12px;">
                        <p style="margin: 0;">&copy; {datetime.datetime.now().year if 'datetime' in globals() else 2024} Spice Kitchen. All rights reserved.</p>
                    </div>
                </div>
                """
                plain_message = f"Hi {user.first_name},\n\nWelcome to Spice Kitchen! Your account has been successfully created.\n\nYour Login Credentials:\nEmail: {user.email}\nPassword: {raw_password}\n\nOrder Now: https://spice-kichen-restaurant.vercel.app/auth"
                send_mail(
                    subject='Welcome to Spice Kitchen!',
                    message=plain_message,
                    from_email=f"Spice Kitchen <{settings.EMAIL_HOST_USER}>",
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=True,
                )
            except Exception as e:
                logger.error(f"Failed to send welcome email: {e}")

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

class ContactMessageViewSet(viewsets.ModelViewSet):
    queryset = ContactMessage.objects.all().order_by('-created_at')
    serializer_class = ContactMessageSerializer
    permission_classes = [permissions.AllowAny] # Allow anyone to submit a contact message

