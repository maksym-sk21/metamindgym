from django import forms
from .models import Course, Lesson, AvailableSlot, LessonVideo


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ('title', 'description', 'course_type', 'price', 'stripe_price_id', 'is_active')
        labels = {
            'title': 'Название',
            'description': 'Описание',
            'course_type': 'Тип курса',
            'price': 'Цена',
            'stripe_price_id': 'Stripe Price ID',
            'is_active': 'Активен',
        }


class LessonForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = ('title', 'description', 'order', 'zip_file', 'is_active')
        labels = {
            'title': 'Название урока',
            'description': 'Описание',
            'order': 'Порядок',
            'zip_file': 'ZIP архив (страница Tilda)',
            'is_active': 'Активен',
        }


class LessonVideoForm(forms.ModelForm):
    class Meta:
        model = LessonVideo
        fields = ('title', 'description', 'video_file', 'order')
        labels = {
            'title': 'Название видео',
            'description': 'Описание видео',
            'video_file': 'Видео файл (mp4)',
            'order': 'Порядок',
        }


class SlotForm(forms.ModelForm):
    class Meta:
        model = AvailableSlot
        fields = ('date', 'time')
        labels = {
            'date': 'Дата',
            'time': 'Время',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }
