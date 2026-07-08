import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

if not User.objects.filter(username='admin@spicekitchen.com').exists():
    User.objects.create_superuser('admin@spicekitchen.com', 'admin@spicekitchen.com', 'admin123')
    print("Superuser created")
else:
    print("Superuser already exists")
