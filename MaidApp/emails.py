import logging
import re
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)


def _html_to_text(html):
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def send_email(subject, to_email, template_name, context=None, from_email=None):
    """Send one transactional message through the configured email backend."""
    if context is None:
        context = {}
    context.setdefault('site_url', settings.SITE_URL)
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL

    try:
        validate_email(to_email)
    except ValidationError:
        logger.warning('Refusing to send %r to an invalid recipient.', subject)
        return False

    html_content = render_to_string(template_name, context)
    text_content = _html_to_text(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")
    try:
        sent = msg.send(fail_silently=False)
    except Exception:
        # Email must not roll back a confirmed payment, but failures must be visible.
        logger.exception('Unable to send transactional email %r to %s.', subject, to_email)
        return False
    return sent == 1


def send_payment_success_email(user, plan):
    send_email(
        f"Payment Successful - Welcome to SelectRoyal Maids ({plan.title()})",
        user.email,
        'emails/payment_success.html',
        {'user': user, 'plan': plan},
    )


def send_payment_failed_email(user):
    send_email(
        "Payment Failed - SelectRoyal Maids",
        user.email,
        'emails/payment_failed.html',
        {'user': user},
    )


def send_signup_welcome_email(user, plan):
    send_email(
        f"Welcome to SelectRoyal Maids - {plan.title()} Plan Activated",
        user.email,
        'emails/signup_welcome.html',
        {'user': user, 'plan': plan},
    )


def send_unread_support_email(employer, unread_count=1):
    send_email(
        "You have unread support messages - SelectRoyal Maids",
        employer.email,
        'emails/unread_support.html',
        {'employer': employer, 'unread_count': unread_count},
    )


def send_request_form_email(employer, placement):
    send_email(
        "Placement Request Received - SelectRoyal Maids",
        employer.email,
        'emails/request_form_submitted.html',
        {'employer': employer, 'placement': placement},
    )


def send_employer_action_email(employer, action, maid=None):
    send_email(
        f"Action Confirmed: {action} - SelectRoyal Maids",
        employer.email,
        'emails/employer_action.html',
        {'employer': employer, 'action': action, 'maid': maid},
    )


def send_blog_alert_email(user, post):
    send_email(
        f"New Blog Post: {post.title}",
        user.email,
        'emails/new_blog_post.html',
        {'user': user, 'post': post},
    )


def send_blog_subscribe_email(email):
    return send_email(
        "Successfully Subscribed to SelectRoyal Maids Blog",
        email,
        'emails/blog_subscribe.html',
        {'email': email},
    )
