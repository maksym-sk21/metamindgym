from django.contrib import admin
from .models import Course, Lesson, LessonVideo, UserCourse, AvailableSlot, Meeting


class LessonVideoInline(admin.TabularInline):
    model = LessonVideo
    extra = 1
    fields = ('title', 'video_file', 'order')
    ordering = ('order',)


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ('title', 'order', 'is_active')
    ordering = ('order',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'course_type', 'price', 'is_active')


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'order', 'is_active')
    list_filter = ('course',)
    ordering = ('course', 'order')


@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'granted_at')
    list_filter = ('course',)


@admin.register(LessonVideo)
class LessonVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'order')
    list_filter = ('lesson__course',)


@admin.register(AvailableSlot)
class AvailableSlotAdmin(admin.ModelAdmin):
    list_display = ('date', 'time', 'is_booked')
    list_filter = ('date', 'is_booked')


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('user', 'lesson', 'slot', 'status', 'created_at')
    list_filter = ('status',)