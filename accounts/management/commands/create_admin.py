from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os


class Command(BaseCommand):
    help = 'Create superuser if not exists'

    def handle(self, *args, **options):
        User = get_user_model()

        email = "wery5859@gmail.com"
        password = "metaadminmind3224"
        username = "admin"

        if not email or not password:
            self.stdout.write(self.style.ERROR('No admin credentials provided'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING('Admin already exists'))
            return

        User.objects.create_superuser(
            email=email,
            password=password,
            username=username
        )

        self.stdout.write(self.style.SUCCESS('Superuser created successfully'))
