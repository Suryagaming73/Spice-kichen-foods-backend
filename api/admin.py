from django.contrib import admin
from .models import UserProfile, Category, FoodItem, Order, Review, HotelSetting, ContactMessage

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(Category)
admin.site.register(FoodItem)
admin.site.register(Order)
admin.site.register(Review)
admin.site.register(HotelSetting)
admin.site.register(ContactMessage)
