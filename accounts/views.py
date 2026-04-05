import os
import zipfile
import shutil
import threading

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.conf import settings

from .forms import RegisterForm, LoginForm, ProfileForm, CustomPasswordChangeForm
from courses.forms import CourseForm, LessonForm, SlotForm, LessonVideoForm
from courses.models import Course, UserCourse, Lesson, LessonVideo, AvailableSlot, Meeting
from accounts.decorators import site_admin_required

import stripe
import json
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from courses.stripe_helpers import create_checkout_session


def landing(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    return render(request, 'accounts/landing.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            try:
                free_course = Course.objects.get(course_type='free')
                UserCourse.objects.create(user=user, course=free_course)
            except Course.DoesNotExist:
                pass
            login(request, user)
            messages.success(request, 'Добро пожаловать! Бесплатный курс уже доступен.')
            return redirect('accounts:dashboard')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                return redirect('accounts:dashboard')
            else:
                messages.error(request, 'Неверный email или пароль')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('accounts:landing')


@login_required
def dashboard(request):
    accessible = list(UserCourse.objects.filter(user=request.user).values_list('course__course_type', flat=True))
    order_map = {
        'free': 0,
        'paid_1': 1,
        'paid_2': 2,
        'paid_3': 3,
        'paid_4': 4,
    }

    all_courses = sorted(
        Course.objects.filter(is_active=True),
        key=lambda c: order_map.get(c.course_type, 999)
    )
    
    meetings = Meeting.objects.filter(user=request.user).select_related(
        'lesson__course', 'slot'
    ).order_by('-created_at')
    return render(request, 'accounts/dashboard.html', {
        'all_courses': all_courses,
        'accessible': accessible,
        'meetings': meetings,
    })


@login_required
def account_view(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('accounts:account')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/account.html', {'form': form})


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменён')
            return redirect('accounts:account')
    else:
        form = CustomPasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def delete_account_view(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Аккаунт удалён')
        return redirect('accounts:landing')
    return render(request, 'accounts/delete_account.html')


@login_required
@site_admin_required
def admin_panel(request):
    from accounts.models import User
    users = User.objects.prefetch_related('user_courses__course').all().order_by('-date_joined')
    courses = Course.objects.all().order_by('course_type')
    return render(request, 'admin_panel/index.html', {
        'users': users,
        'courses': courses,
    })


@login_required
@site_admin_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Курс создан')
            return redirect('accounts:admin_panel')
    else:
        form = CourseForm()
    return render(request, 'admin_panel/course_form.html', {'form': form, 'title': 'Новый курс'})


@login_required
@site_admin_required
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Курс обновлён')
            return redirect('accounts:admin_panel')
    else:
        form = CourseForm(instance=course)
    return render(request, 'admin_panel/course_form.html', {'form': form, 'title': 'Редактировать курс'})


@login_required
@site_admin_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Курс удалён')
        return redirect('accounts:admin_panel')
    return render(request, 'admin_panel/course_confirm_delete.html', {'course': course})


@login_required
@site_admin_required
def course_upload_zip(request, pk):
    course = get_object_or_404(Course, pk=pk)

    if request.method == 'POST' and request.FILES.get('tilda_zip'):
        zip_file = request.FILES['tilda_zip']

        dest_dir = os.path.join(settings.MEDIA_ROOT, 'courses', course.course_type)

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        os.makedirs(dest_dir)

        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(dest_dir)
        except zipfile.BadZipFile:
            messages.error(request, 'Файл не является корректным ZIP-архивом.')
            return redirect('accounts:admin_panel')

        index_path = _find_index_html(dest_dir)
        if not index_path:
            messages.error(request, 'В архиве не найден index.html.')
            return redirect('accounts:admin_panel')

        rel_path = os.path.relpath(index_path, settings.MEDIA_ROOT)
        course.tilda_path = rel_path.replace('\\', '/')  # Windows-safe
        course.save(update_fields=['tilda_path'])

        messages.success(request, f'Контент курса «{course.title}» успешно загружен.')
        return redirect('accounts:admin_panel')

    return render(request, 'admin_panel/course_upload_zip.html', {'course': course})


def _find_index_html(directory):
    root_index = os.path.join(directory, 'index.html')
    if os.path.exists(root_index):
        return root_index

    for name in os.listdir(directory):
        sub = os.path.join(directory, name)
        if os.path.isdir(sub):
            sub_index = os.path.join(sub, 'index.html')
            if os.path.exists(sub_index):
                return sub_index

    return None


@login_required
@site_admin_required
def lesson_create(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES)
        if form.is_valid():
            lesson = form.save(commit=False)
            lesson.course = course
            lesson.tilda_path = ''
            lesson.save()
            if lesson.zip_file:
                thread = threading.Thread(target=lesson.extract_zip)
                thread.daemon = True
                thread.start()
            messages.success(request, 'Урок добавлен. Страница Tilda обрабатывается — подождите минуту.')
            return redirect('accounts:admin_panel')
    else:
        form = LessonForm()
    return render(request, 'admin_panel/lesson_form.html', {
        'form': form,
        'course': course,
        'lesson': None,
        'videos': [],
        'title': 'Новый урок'
    })


@login_required
@site_admin_required
def lesson_edit(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    videos = lesson.videos.all()
    if request.method == 'POST':
        form = LessonForm(request.POST, request.FILES, instance=lesson)
        if form.is_valid():
            updated_lesson = form.save(commit=False)
            has_new_zip = 'zip_file' in request.FILES
            if has_new_zip:
                updated_lesson.tilda_path = ''
            updated_lesson.save()
            if has_new_zip:
                thread = threading.Thread(target=updated_lesson.extract_zip)
                thread.daemon = True
                thread.start()
                messages.success(request, 'Урок обновлён. Страница Tilda обрабатывается — подождите минуту.')
            else:
                messages.success(request, 'Урок обновлён')
            return redirect('accounts:admin_panel')
    else:
        form = LessonForm(instance=lesson)
    return render(request, 'admin_panel/lesson_form.html', {
        'form': form,
        'course': course,
        'lesson': lesson,
        'videos': videos,
        'title': 'Редактировать урок'
    })


@login_required
@site_admin_required
def lesson_delete(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course)
    if request.method == 'POST':
        lesson.delete()
        messages.success(request, 'Урок удалён')
        return redirect('accounts:admin_panel')
    return render(request, 'admin_panel/lesson_confirm_delete.html', {
        'lesson': lesson,
        'course': course
    })


@login_required
@site_admin_required
def video_add(request, lesson_pk):
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    if request.method == 'POST':
        form = LessonVideoForm(request.POST, request.FILES)
        if form.is_valid():
            video = form.save(commit=False)
            video.lesson = lesson
            video.save()
            messages.success(request, f'Видео «{video.title}» добавлено')
        else:
            messages.error(request, 'Ошибка при загрузке видео')
    return redirect('accounts:lesson_edit', course_id=lesson.course.id, lesson_id=lesson.pk)


@login_required
@site_admin_required
def video_delete(request, pk):
    video = get_object_or_404(LessonVideo, pk=pk)
    lesson = video.lesson
    if request.method == 'POST':
        video.video_file.delete(save=False)
        video.delete()
        messages.success(request, 'Видео удалено')
    return redirect('accounts:lesson_edit', course_id=lesson.course.id, lesson_id=lesson.pk)


@login_required
@site_admin_required
def admin_calendar(request):
    from datetime import date
    slots = AvailableSlot.objects.filter(date__gte=date.today()).order_by('date', 'time')
    form = SlotForm()
    return render(request, 'admin_panel/calendar.html', {
        'slots': slots,
        'form': form,
    })


@login_required
@site_admin_required
def slot_add(request):
    if request.method == 'POST':
        form = SlotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Слот добавлен')
        else:
            messages.error(request, 'Ошибка — возможно такой слот уже существует')
    return redirect('accounts:admin_calendar')


@login_required
@site_admin_required
def slot_delete(request, slot_id):
    slot = get_object_or_404(AvailableSlot, id=slot_id)
    if request.method == 'POST':
        if slot.is_booked:
            messages.error(request, 'Нельзя удалить занятый слот')
        else:
            slot.delete()
            messages.success(request, 'Слот удалён')
    return redirect('accounts:admin_calendar')


@login_required
@site_admin_required
def admin_meetings(request):
    meetings = Meeting.objects.select_related(
        'user', 'lesson__course', 'slot'
    ).order_by('-created_at')
    return render(request, 'admin_panel/meetings.html', {'meetings': meetings})


@login_required
@site_admin_required
def meeting_status(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'confirmed', 'cancelled']:
            meeting.status = new_status
            meeting.save()
            if new_status == 'cancelled' and meeting.slot:
                meeting.slot.is_booked = False
                meeting.slot.save()
            messages.success(request, 'Статус обновлён')
    return redirect('accounts:admin_meetings')


@login_required
@site_admin_required
def meeting_link(request, meeting_id):
    meeting = get_object_or_404(Meeting, id=meeting_id)
    if request.method == 'POST':
        link = request.POST.get('meet_link', '').strip()
        meeting.meet_link = link
        meeting.save()
        messages.success(request, 'Ссылка сохранена')
    return redirect('accounts:admin_meetings')


@login_required
def checkout(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)

    if UserCourse.objects.filter(user=request.user, course=course).exists():
        messages.info(request, 'У тебя уже есть доступ к этому курсу')
        return redirect('accounts:dashboard')

    success_url = request.build_absolute_uri('/checkout/success/?session_id={CHECKOUT_SESSION_ID}')
    cancel_url = request.build_absolute_uri('/checkout/cancel/')

    session = create_checkout_session(request.user, course, success_url, cancel_url)
    return redirect(session.url, permanent=False)


@login_required
def checkout_success(request):
    messages.success(request, 'Оплата прошла успешно! Курс уже доступен в кабинете.')
    return redirect('accounts:dashboard')


@login_required
def checkout_cancel(request):
    messages.error(request, 'Оплата отменена.')
    return redirect('accounts:dashboard')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata'].get('user_id')
        course_id = session['metadata'].get('course_id')

        if user_id and course_id:
            from accounts.models import User
            try:
                user = User.objects.get(id=user_id)
                course = Course.objects.get(id=course_id)
                UserCourse.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={'stripe_payment_intent': session.get('payment_intent', '')}
                )
            except (User.DoesNotExist, Course.DoesNotExist):
                pass

    return HttpResponse(status=200)
