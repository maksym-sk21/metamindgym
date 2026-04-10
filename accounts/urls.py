from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('account/', views.account_view, name='account'),
    path('account/change-password/', views.change_password_view, name='change_password'),
    path('account/delete/', views.delete_account_view, name='delete_account'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/courses/create/', views.course_create, name='course_create'),
    path('admin-panel/courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('admin-panel/courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('admin-panel/courses/<int:pk>/upload-zip/', views.course_upload_zip, name='course_upload_zip'),
    path('admin-panel/courses/<int:course_id>/lessons/create/', views.lesson_create, name='lesson_create'),
    path('admin-panel/courses/<int:course_id>/lessons/<int:lesson_id>/edit/', views.lesson_edit, name='lesson_edit'),
    path('admin-panel/courses/<int:course_id>/lessons/<int:lesson_id>/delete/', views.lesson_delete, name='lesson_delete'),
    path('admin-panel/lessons/<int:lesson_pk>/videos/add/', views.video_add, name='video_add'),
    path('admin-panel/videos/<int:pk>/delete/', views.video_delete, name='video_delete'),
    path('admin-panel/lessons/<int:lesson_pk>/videos/presign/', views.video_presign, name='video_presign'),
    path('admin-panel/lessons/<int:lesson_pk>/videos/confirm/', views.video_confirm, name='video_confirm'),
    path('admin-panel/calendar/', views.admin_calendar, name='admin_calendar'),
    path('admin-panel/calendar/slots/add/', views.slot_add, name='slot_add'),
    path('admin-panel/calendar/slots/bulk-add/', views.slot_bulk_add, name='slot_bulk_add'),
    path('admin-panel/calendar/slots/week-add/', views.slot_week_add, name='slot_week_add'),
    path('admin-panel/calendar/slots/<int:slot_id>/delete/', views.slot_delete, name='slot_delete'),
    path('admin-panel/meetings/', views.admin_meetings, name='admin_meetings'),
    path('admin-panel/meetings/<int:meeting_id>/status/', views.meeting_status, name='meeting_status'),
    path('admin-panel/meetings/<int:meeting_id>/link/', views.meeting_link, name='meeting_link'),
    path('checkout/<int:course_id>/', views.checkout, name='checkout'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/cancel/', views.checkout_cancel, name='checkout_cancel'),
    path('stripe/webhook/', views.stripe_webhook, name='stripe_webhook'),
]
