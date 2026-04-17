from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from .models import User


PHONE_CODES = [
    ('+1',   '🇺🇸 +1'),
    ('+34',  '🇪🇸 +34'),
    ('+52',  '🇲🇽 +52'),
    ('+380', '🇺🇦 +380'),
    ('+44',  '🇬🇧 +44'),
    ('+49',  '🇩🇪 +49'),
    ('+33',  '🇫🇷 +33'),
    ('+55',  '🇧🇷 +55'),
    ('+54',  '🇦🇷 +54'),
    ('+57',  '🇨🇴 +57'),
]


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label='Email')
    username = forms.CharField(label='Имя пользователя')
    phone_code = forms.ChoiceField(
        label='Код страны',
        choices=PHONE_CODES,
        initial='+380',
    )
    phone = forms.CharField(
        label='Телефон',
        max_length=15,
        widget=forms.TextInput(attrs={'placeholder': '991234567'}),
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'phone_code', 'phone', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        code = self.cleaned_data.get('phone_code', '')
        number = self.cleaned_data.get('phone', '')
        user.phone = f"{code}{number}"
        if commit:
            user.save()
        return user


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

