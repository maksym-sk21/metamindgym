from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Email')
    username = forms.CharField(label='Имя пользователя')

    class Meta:
        model = User
        fields = ('email', 'username', 'password1', 'password2')


class LoginForm(forms.Form):
    email = forms.EmailField(label='Email')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'phone', 'avatar')
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Телефон',
            'avatar': 'Фото профиля',
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(label='Текущий пароль', widget=forms.PasswordInput)
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput)
    new_password2 = forms.CharField(label='Повторите новый пароль', widget=forms.PasswordInput)

