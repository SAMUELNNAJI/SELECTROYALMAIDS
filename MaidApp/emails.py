import logging
import mimetypes
import re
from pathlib import Path

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


def send_email(subject, to_email, template_name, context=None, from_email=None, attachments=None):
    """Send one transactional message through the configured email backend.

    ``attachments`` is an optional list of ``(filename, content, mimetype)`` tuples.
    """
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
    for filename, content, mime_type in (attachments or []):
        msg.attach(filename, content, mime_type)
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


def send_request_form_email(employer, placement, request_details_html=None):
    """Send a placement request receipt to the employer and notify the company inbox."""
    # 1) Receipt / confirmation to the employer who submitted the request
    send_email(
        "Placement Request Received - SelectRoyal Maids",
        employer.email,
        'emails/request_form_submitted.html',
        {'employer': employer, 'placement': placement},
    )
    # 2) New placement-request notification to the company inbox
    send_email(
        f"New Placement Request #{placement.id} - {employer.get_full_name() or employer.username}",
        settings.NOTIFICATION_EMAIL,
        'emails/placement_request_notification.html',
        {
            'employer': employer,
            'placement': placement,
            'request_details': request_details_html,
        },
    )


def send_maid_application_email(application):
    """Send a new maid registration to the company inbox, photo attached when present."""
    attachments = []
    if application.profile_photo and application.profile_photo.name:
        try:
            content_type = mimetypes.guess_type(application.profile_photo.name)[0] or 'application/octet-stream'
            with application.profile_photo.open('rb') as photo:
                attachments.append((
                    f'maid-application-{application.pk}-photo{Path(application.profile_photo.name).suffix}',
                    photo.read(),
                    content_type,
                ))
        except Exception:
            logger.exception('Could not attach applicant photo for application %s.', application.pk)

    return send_email(
        f"New Maid Application #{application.pk} - {application.first_name} {application.last_name}",
        settings.NOTIFICATION_EMAIL,
        'emails/maid_application_notification.html',
        {'application': application},
        attachments=attachments,
    )


def send_maid_registration_success_email(application):
    """Confirm successful registration to the maid who just applied."""
    return send_email(
        "Registration Successful - Welcome to SelectRoyal Maids",
        application.email,
        'emails/maid_registration_success.html',
        {'application': application},
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


def send_contact_email(first_name, last_name, email, phone, city, source, subject, message):
    """Forward a contact-form submission to the company inbox."""
    return send_email(
        f"New Contact Message: {subject} — {first_name} {last_name}",
        settings.DEFAULT_FROM_EMAIL,          # sent TO the company inbox
        'emails/contact_message.html',
        {
            'first_name': first_name,
            'last_name':  last_name,
            'email':      email,
            'phone':      phone or '—',
            'city':       city or '—',
            'source':     source or '—',
            'subject':    subject,
            'message':    message,
        },
        from_email=settings.DEFAULT_FROM_EMAIL,
    )


def send_contact_ack_email(first_name, email, subject):
    """Send an acknowledgement to the visitor who submitted the form."""
    if not email:
        return False
    return send_email(
        "We've received your message – SelectRoyal Maids",
        email,                                  # acknowledgement TO the submitter
        'emails/contact_ack.html',
        {'first_name': first_name, 'subject': subject},
    )


def send_password_reset_email(user, reset_url):
    """Send the one-time password reset link to the user."""
    return send_email(
        "Reset Your Password – SelectRoyal Maids",
        user.email,
        'emails/password_reset_link.html',
        {'user': user, 'reset_url': reset_url},
    )


def send_password_changed_email(user):
    """Notify the user that their password was successfully changed."""
    return send_email(
        "Your Password Has Been Changed – SelectRoyal Maids",
        user.email,
        'emails/password_changed.html',
        {'user': user},
    )
