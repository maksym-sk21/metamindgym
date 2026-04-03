from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    path('<int:course_id>/', views.course_detail, name='course_detail'),
    path('<int:course_id>/lessons/<int:lesson_id>/', views.lesson_view, name='lesson_view'),
    path('<int:course_id>/lessons/<int:lesson_id>/book/', views.book_meeting, name='book_meeting'),
    path('slots/', views.get_slots, name='get_slots'),
]
