from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, verbose_name='Телефон')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')
    is_site_admin = models.BooleanField(default=False, verbose_name='Администратор сайта')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email