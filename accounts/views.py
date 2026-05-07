import os
import zipfile
import shutil
import threading
from datetime import datetime, timedelta

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

import uuid
import json
import boto3
from botocore.config import Config
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
import logging

logger = logging.getLogger(__name__)

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
            messages.success(request, '¡Bienvenido! El curso gratuito ya está disponible.')
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
                messages.error(request, 'Correo electrónico o contraseña incorrectos')
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
            messages.success(request, 'Perfil actualizado')
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
            messages.success(request, 'Contraseña actualizada correctamente')
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
        messages.success(request, 'Cuenta eliminada')
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


def _get_r2_client():
    """boto3-клиент для Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT_URL,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        config=Config(signature_version='s3v4'),
        region_name='auto',
    )


@login_required
@site_admin_required
@require_GET
def video_presign(request, lesson_pk):
    lesson = get_object_or_404(Lesson, pk=lesson_pk)
    filename = request.GET.get('filename', 'video.mp4')
    content_type = request.GET.get('content_type', 'video/mp4')

    ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'mp4'
    key = f'lesson_videos/{lesson.pk}/{uuid.uuid4().hex}.{ext}'

    client = _get_r2_client()
    presigned_url = client.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': settings.CLOUDFLARE_R2_BUCKET_NAME,
            'Key': key,
            'ContentType': content_type,
        },
        ExpiresIn=3600,
    )

    return JsonResponse({'url': presigned_url, 'key': key})


@login_required
@site_admin_required
@require_POST
def video_confirm(request, lesson_pk):
    lesson = get_object_or_404(Lesson, pk=lesson_pk)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    title = data.get('title', '').strip()
    key = data.get('key', '').strip()
    order = int(data.get('order', lesson.videos.count()))
    description = data.get('description', '').strip()

    if not title or not key:
        return JsonResponse({'error': 'title and key required'}, status=400)

    video = LessonVideo(lesson=lesson, title=title, order=order)
    if description:
        video.description = description
    video.video_file.name = key
    video.save()

    return JsonResponse({'ok': True, 'id': video.pk, 'title': video.title})


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
@require_POST
def video_update(request, pk):
    video = get_object_or_404(LessonVideo, pk=pk)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    title = data.get('title', '').strip()
    description = data.get('description', '').strip()

    if not title:
        return JsonResponse({'error': 'title required'}, status=400)

    video.title = title
    video.description = description
    video.save(update_fields=['title', 'description'])

    return JsonResponse({'ok': True, 'title': video.title, 'description': video.description})


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
    weekdays = [
        (0, 'Пн'), (1, 'Вт'), (2, 'Ср'),
        (3, 'Чт'), (4, 'Пт'), (5, 'Сб'), (6, 'Вс')
    ]
    return render(request, 'admin_panel/calendar.html', {
        'slots': slots,
        'form': form,
        'weekdays': weekdays,
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
def slot_bulk_add(request):
    if request.method == 'POST':
        date_str = request.POST.get('date')
        time_from_str = request.POST.get('time_from')
        time_to_str = request.POST.get('time_to')

        if not all([date_str, time_from_str, time_to_str]):
            messages.error(request, 'Заполни все поля')
            return redirect('accounts:admin_calendar')

        try:
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time_from = datetime.strptime(time_from_str, '%H:%M').time()
            time_to = datetime.strptime(time_to_str, '%H:%M').time()
        except ValueError:
            messages.error(request, 'Неверный формат даты или времени')
            return redirect('accounts:admin_calendar')

        if time_from >= time_to:
            messages.error(request, 'Время начала должно быть раньше времени конца')
            return redirect('accounts:admin_calendar')

        created = 0
        skipped = 0
        current = datetime.combine(slot_date, time_from)
        end = datetime.combine(slot_date, time_to)

        while current < end:
            slot_time = current.time()
            _, was_created = AvailableSlot.objects.get_or_create(
                date=slot_date,
                time=slot_time,
            )
            if was_created:
                created += 1
            else:
                skipped += 1
            current += timedelta(minutes=30)

        msg = f'Создано {created} слотов'
        if skipped:
            msg += f', пропущено {skipped} (уже существуют)'
        messages.success(request, msg)

    return redirect('accounts:admin_calendar')


@login_required
@site_admin_required
def slot_week_add(request):
    if request.method == 'POST':
        weekdays = request.POST.getlist('weekdays')
        time_from_str = request.POST.get('time_from')
        time_to_str = request.POST.get('time_to')
        weeks = int(request.POST.get('weeks', 1))

        if not weekdays or not time_from_str or not time_to_str:
            messages.error(request, 'Заполни все поля')
            return redirect('accounts:admin_calendar')

        try:
            time_from = datetime.strptime(time_from_str, '%H:%M').time()
            time_to = datetime.strptime(time_to_str, '%H:%M').time()
            weekdays = [int(d) for d in weekdays]
        except ValueError:
            messages.error(request, 'Неверный формат')
            return redirect('accounts:admin_calendar')

        if time_from >= time_to:
            messages.error(request, 'Время начала должно быть раньше времени конца')
            return redirect('accounts:admin_calendar')

        from datetime import date
        today = date.today()
        created = 0
        skipped = 0

        for week in range(weeks):
            for weekday in weekdays:
                days_ahead = weekday - today.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                if week == 0 and days_ahead == 0:
                    days_ahead = 0
                slot_date = today + timedelta(days=days_ahead + week * 7)

                current = datetime.combine(slot_date, time_from)
                end = datetime.combine(slot_date, time_to)

                while current < end:
                    _, was_created = AvailableSlot.objects.get_or_create(
                        date=slot_date,
                        time=current.time(),
                    )
                    if was_created:
                        created += 1
                    else:
                        skipped += 1
                    current += timedelta(minutes=30)

        msg = f'Создано {created} слотов'
        if skipped:
            msg += f', пропущено {skipped} (уже существуют)'
        messages.success(request, msg)

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
        messages.info(request, 'Ya tienes acceso a este curso')
        return redirect('accounts:dashboard')

    success_url = request.build_absolute_uri('/checkout/success/?session_id={CHECKOUT_SESSION_ID}')
    cancel_url = request.build_absolute_uri('/checkout/cancel/')

    session = create_checkout_session(request.user, course, success_url, cancel_url)
    return redirect(session.url, permanent=False)


@login_required
def checkout_success(request):
    messages.success(request, '¡Pago realizado con éxito! El curso ya está disponible en tu cuenta.')
    return redirect('accounts:dashboard')


@login_required
def checkout_cancel(request):
    messages.error(request, 'Pago cancelado.')
    return redirect('accounts:dashboard')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        logger.error(f'Webhook signature error: {e}')
        return HttpResponse(status=400)

    logger.info(f'Webhook received: {event["type"]}')

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        meta = session.metadata.to_dict() if session.metadata else {}
        payment_type = meta.get('type', 'course')

        logger.info(f'Metadata: {meta}')

        if payment_type == 'meeting':
            _handle_meeting_payment(session, meta)
        else:
            _handle_course_payment(session, meta)

    return HttpResponse(status=200)


def _handle_course_payment(session, meta):
    from accounts.models import User

    user_id = meta.get('user_id')
    course_id = meta.get('course_id')

    if not user_id or not course_id:
        logger.error('Course payment: missing metadata')
        return

    try:
        from courses.models import Course, UserCourse

        user = User.objects.get(id=user_id)
        course = Course.objects.get(id=course_id)

        UserCourse.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'stripe_payment_intent': session.payment_intent or ''
            }
        )

        logger.info(f'Course access granted: user={user_id}, course={course_id}')

    except Exception as e:
        logger.error(f'Course payment error: {e}')


def _handle_meeting_payment(session, meta):
    from accounts.models import User
    from courses.notifications import notify_new_meeting
    from django.conf import settings as django_settings

    user_id = meta.get('user_id')
    lesson_id = meta.get('lesson_id')
    slot_id = meta.get('slot_id')
    comment = meta.get('comment', '')

    logger.info(f'Handle meeting: user={user_id}, lesson={lesson_id}, slot={slot_id}')

    if not all([user_id, lesson_id, slot_id]):
        logger.error('Meeting payment: missing metadata')
        return

    try:
        user = User.objects.get(id=user_id)
        lesson = Lesson.objects.get(id=lesson_id)
        slot = AvailableSlot.objects.get(id=slot_id)

        logger.info(f'Slot found: {slot.id}, booked={slot.is_booked}')

        if slot.is_booked:
            logger.warning('Slot already booked')
            return

        if Meeting.objects.filter(user=user, lesson=lesson).exists():
            logger.warning('User already has meeting for this lesson')
            return

        if Meeting.objects.filter(slot=slot).exists():
            logger.warning('Slot already has meeting')
            return

        meeting = Meeting.objects.create(
            user=user,
            lesson=lesson,
            slot=slot,
            comment=comment,
            payment_status='paid',
        )

        slot.is_booked = True
        slot.save()

        logger.info(f'Meeting created: {meeting.id}')

        admin_url = f'https://{django_settings.ALLOWED_HOSTS[0]}/admin-panel/meetings/'
        notify_new_meeting(meeting, admin_url)

    except Exception as e:
        logger.error(f'Meeting payment error: {e}')
