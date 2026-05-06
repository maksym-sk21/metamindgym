from django.db import models
from django.conf import settings


class Course(models.Model):
    COURSE_TYPE_CHOICES = [
        ('free', 'Gratis'),
        ('paid_1', 'Curso 1'),
        ('paid_2', 'Curso 2'),
        ('paid_3', 'Curso 3'),
        ('paid_4', 'Curso 4'),
        ('paid_5', 'Curso 5'),
        ('paid_6', 'Curso 6'),
        ('paid_7', 'Curso 7'),
        ('paid_8', 'Curso 8'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES, unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    stripe_price_id = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons'
    )
    title = models.CharField(max_length=200, verbose_name='Название урока')
    description = models.TextField(blank=True, verbose_name='Описание')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    zip_file = models.FileField(upload_to='lessons_zip/', blank=True, null=True, verbose_name='ZIP архив')
    tilda_path = models.CharField(max_length=500, blank=True, verbose_name='Путь к странице Tilda')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'
        ordering = ['order']

    def __str__(self):
        return f'{self.course.title} — {self.title}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def extract_zip(self):
        import zipfile
        import io
        from django.core.files.base import ContentFile
        from django.core.files.storage import default_storage

        with self.zip_file.open('rb') as f:
            zip_data = f.read()

        index_path = None

        with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
            for name in z.namelist():
                if name.endswith('/'):
                    continue

                file_data = z.read(name)
                save_path = f'lessons/{self.id}/{name}'

                if default_storage.exists(save_path):
                    default_storage.delete(save_path)
                default_storage.save(save_path, ContentFile(file_data))

                if name.endswith('index.html') and index_path is None:
                    index_path = save_path

        if index_path:
            Lesson.objects.filter(pk=self.pk).update(tilda_path=index_path)
            self.tilda_path = index_path


class LessonVideo(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='videos'
    )
    title = models.CharField(max_length=200, verbose_name='Название видео')
    description = models.TextField(blank=True, verbose_name='Описание видео')
    video_file = models.FileField(
        upload_to='lesson_videos/',
        verbose_name='Видео файл'
    )
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Видео урока'
        verbose_name_plural = 'Видео уроков'
        ordering = ['order']

    def __str__(self):
        return f'{self.lesson.title} — {self.title}'


class UserCourse(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_courses'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='user_courses'
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ('user', 'course')
        verbose_name = 'Доступ к курсу'
        verbose_name_plural = 'Доступы к курсам'

    def __str__(self):
        return f'{self.user.email} — {self.course.title}'


class AvailableSlot(models.Model):
    date = models.DateField(verbose_name='Дата')
    time = models.TimeField(verbose_name='Время')
    is_booked = models.BooleanField(default=False, verbose_name='Занято')

    class Meta:
        verbose_name = 'Доступный слот'
        verbose_name_plural = 'Доступные слоты'
        ordering = ['date', 'time']
        unique_together = ('date', 'time')

    def __str__(self):
        return f'{self.date} {self.time} — {"ocupado" if self.is_booked else "disponible"}'


class Meeting(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('confirmed', 'Confirmada'),
        ('cancelled', 'Cancelada'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('unpaid', 'No se paga'),
        ('paid', 'Pagado'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='meetings'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name='meetings'
    )
    slot = models.OneToOneField(
        AvailableSlot,
        on_delete=models.CASCADE,
        related_name='meeting'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid',
        verbose_name='Статус оплаты'
    )
    comment = models.TextField(blank=True, verbose_name='Комментарий пользователя')
    created_at = models.DateTimeField(auto_now_add=True)
    meet_link = models.URLField(blank=True, verbose_name='Ссылка на встречу (Google Meet)')

    class Meta:
        verbose_name = 'Встреча'
        verbose_name_plural = 'Встречи'

    def __str__(self):
        return f'{self.user.email} — {self.lesson.title} — {self.slot.date} {self.slot.time}'
