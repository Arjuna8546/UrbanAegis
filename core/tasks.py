from celery import shared_task
from django.core.mail import send_mail
from django.utils.timezone import now
from datetime import timedelta
from core.models import Users
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


@shared_task
def notify_inactive_users():
    cutoff_date = now() - timedelta(days=1)
    print(f"Cutoff Date: {cutoff_date}")
    inactive_users = Users.objects.filter(last_login__lt=cutoff_date, is_active=True)
    
    for user in inactive_users:
        print(f"User: {user.email}, Last Login: {user.last_login}")
        if user.email:
            html_content = render_to_string('email_template.html', {'user': user})
            text_content = strip_tags(html_content)
            email = EmailMultiAlternatives(
                subject="We Miss You!",
                body=text_content,
                from_email="support@example.com",
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
    return f"Notified {inactive_users.count()} users."