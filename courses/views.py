from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Course, Lesson, UserCourse, AvailableSlot, Meeting
import json
from .notifications import notify_new_meeting


def get_user_accessible_courses(user):
    return set(
        UserCourse.objects.filter(user=user).values_list('course_id', flat=True)
    )


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

    if request.method == 'POST':
        slot_id = request.POST.get('slot_id')
        comment = request.POST.get('comment', '')
        slot = get_object_or_404(AvailableSlot, id=slot_id, is_booked=False)

        if Meeting.objects.filter(user=request.user, lesson=lesson).exists():
            messages.error(request, 'Ya tienes una reunión reservada para esta lección')
            return redirect('courses:course_detail', course_id=course.id)

        meeting = Meeting.objects.create(
            user=request.user,
            lesson=lesson,
            slot=slot,
            comment=comment,
        )
        slot.is_booked = True
        slot.save()

        admin_url = request.build_absolute_uri('/admin-panel/meetings/')
        notify_new_meeting(meeting, admin_url)

        messages.success(request, f'Reunión reservada para el {slot.date} a las {slot.time}')
        return redirect('courses:course_detail', course_id=course.id)

    slots = AvailableSlot.objects.filter(is_booked=False).order_by('date', 'time')
    existing_meeting = Meeting.objects.filter(user=request.user, lesson=lesson).first()

    return render(request, 'courses/book_meeting.html', {
        'course': course,
        'lesson': lesson,
        'slots': slots,
        'existing_meeting': existing_meeting,
    })


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

