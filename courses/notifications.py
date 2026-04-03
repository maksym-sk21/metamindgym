import requests
from django.conf import settings


def send_telegram(message: str):
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_ADMIN_CHAT_ID

    if not token or not chat_id:
        return

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        requests.post(url, data={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }, timeout=5)
    except Exception:
        pass


def notify_new_meeting(meeting, admin_url: str):
    message = (
        f'📅 <b>Новая заявка на встречу</b>\n\n'
        f'👤 <b>Пользователь:</b> {meeting.user.username}\n'
        f'📧 <b>Email:</b> {meeting.user.email}\n'
        f'📚 <b>Курс:</b> {meeting.lesson.course.title}\n'
        f'📖 <b>Урок:</b> {meeting.lesson.title}\n'
        f'🗓 <b>Дата:</b> {meeting.slot.date} в {meeting.slot.time}\n'
        f'💬 <b>Комментарий:</b> {meeting.comment or "—"}\n\n'
        f'👉 <a href="{admin_url}">Открыть в админке</a>'
    )
    send_telegram(message)