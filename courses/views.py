from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from .models import Course, Lesson, UserCourse, AvailableSlot, Meeting
import json
import stripe
from .notifications import notify_new_meeting

stripe.api_key = settings.STRIPE_SECRET_KEY


def get_user_accessible_courses(user):
    return set(
        UserCourse.objects.filter(user=user).values_list('course_id', flat=True)
    )


def free_lesson_view(request):
    course = get_object_or_404(Course, course_type='free', is_active=True)
    lesson = course.lessons.filter(is_active=True).first()
    if not lesson:
        return render(request, 'courses/lesson_view.html', {
            'course': course,
            'lesson': None,
            'lessons': [],
            'is_free_preview': True,
        })
    lessons = course.lessons.filter(is_active=True)
    return render(request, 'courses/lesson_view.html', {
        'course': course,
        'lesson': lesson,
        'lessons': lessons,
        'is_free_preview': True,
    })


@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    accessible = get_user_accessible_courses(request.user)

    if course.id not in accessible:
        messages.error(request, 'No tienes acceso a este curso')
        return redirect('accounts:dashboard')

    lessons = course.lessons.filter(is_active=True)
    return render(request, 'courses/course_detail.html', {
        'course': course,
        'lessons': lessons,
    })


@login_required
def lesson_view(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_active=True)
    accessible = get_user_accessible_courses(request.user)

    if course.id not in accessible:
        messages.error(request, 'No tienes acceso a este curso')
        return redirect('accounts:dashboard')

    lessons = course.lessons.filter(is_active=True)
    return render(request, 'courses/lesson_view.html', {
        'course': course,
        'lesson': lesson,
        'lessons': lessons,
    })


@login_required
def book_meeting(request, course_id, lesson_id):
    course = get_object_or_404(Course, id=course_id, is_active=True)
    lesson = get_object_or_404(Lesson, id=lesson_id, course=course, is_active=True)
    accessible = get_user_accessible_courses(request.user)

    if course.id not in accessible:
        messages.error(request, 'No tienes acceso a este curso')
        return redirect('accounts:dashboard')

    existing_meeting = Meeting.objects.filter(user=request.user, lesson=lesson).first()

    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        comment = request.POST.get('comment', '')

        if existing_meeting:
            messages.error(request, 'Ya tienes una reunión reservada para esta lección')
            return redirect('courses:course_detail', course_id=course.id)

        slot = get_object_or_404(AvailableSlot, id=slot_id, is_booked=False)

        success_url = request.build_absolute_uri(
            f'/courses/{course_id}/lessons/{lesson_id}/book/success/?session_id={{CHECKOUT_SESSION_ID}}'
        )
        cancel_url = request.build_absolute_uri(
            f'/courses/{course_id}/lessons/{lesson_id}/book/'
        )

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_MEETING_PRICE_ID,
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.user.email,
            metadata={
                'type': 'meeting',
                'user_id': str(request.user.id),
                'lesson_id': str(lesson.id),
                'slot_id': str(slot.id),
                'comment': comment,
            }
        )

        return redirect(checkout_session.url, permanent=False)

    slots = AvailableSlot.objects.filter(is_booked=False).order_by('date', 'time')

    return render(request, 'courses/book_meeting.html', {
        'course': course,
        'lesson': lesson,
        'slots': slots,
        'existing_meeting': existing_meeting,
        'meeting_price_id': settings.STRIPE_MEETING_PRICE_ID,
    })


@login_required
def book_meeting_success(request, course_id, lesson_id):
    messages.success(request, '¡Pago realizado! Tu reunión ha sido reservada.')
    return redirect('courses:course_detail', course_id=course_id)


@login_required
def get_slots(request):
    date = request.GET.get('date')
    if not date:
        return JsonResponse({'slots': []})

    slots = AvailableSlot.objects.filter(
        date=date,
        is_booked=False
    ).values('id', 'time')

    return JsonResponse({'slots': list(slots)})