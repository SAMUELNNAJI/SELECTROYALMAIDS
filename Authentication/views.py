from decimal import Decimal, InvalidOperation
import logging
from threading import Thread

import requests as http_requests
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.hashers import make_password, identify_hasher
from django.db import IntegrityError, transaction
from django.db.models import Q, Count, Sum, Case, When, Value, IntegerField
from django.views.decorators.http import require_POST
from datetime import timedelta
from MaidApp.models import BlogPost, FAQ, LegacyEmployer, MaidProfile, MaidRegistration, MaidRecommendation, PlacementRequest, Service, SupportMessage
from MaidApp.image_utils import resolve_image_url
from MaidApp.emails import send_payment_success_email, send_payment_failed_email, send_signup_welcome_email, send_blog_alert_email, send_password_reset_email, send_password_changed_email, send_maid_recommended_email, send_maid_application_decline_email
from .models import EmployerProfile, PendingSignup

logger = logging.getLogger(__name__)


def _resolve_assignment_target(assigned_to):
    """Parse an 'assigned_to' form value into (site_user, legacy_employer).

    Accepts 'user:<id>' for site employer accounts, 'legacy:<id>' for rows
    imported from request.sql, and anything empty/unknown as (None, None).
    """
    value = (assigned_to or '').strip()
    if value.startswith('user:'):
        return User.objects.filter(pk=value.split(':', 1)[1]).first(), None
    if value.startswith('legacy:'):
        return None, LegacyEmployer.objects.filter(pk=value.split(':', 1)[1]).first()
    return None, None


def _payment_callback_url(request):
    """Return the one canonical public URL Flutterwave should redirect to."""
    from django.conf import settings as django_settings

    base_url = django_settings.PAYMENT_CALLBACK_URL
    if base_url:
        return f"{base_url}{reverse('Authentication:payment_callback')}"
    return request.build_absolute_uri(reverse('Authentication:payment_callback'))


def _send_payment_confirmation_emails_in_background(user, plan):
    """Keep slow SMTP delivery from delaying Flutterwave's browser callback."""
    def send_emails():
        try:
            send_signup_welcome_email(user, plan)
            send_payment_success_email(user, plan)
        except Exception:
            logger.exception('Email delivery failed after payment for %s.', user.email)

    Thread(target=send_emails, name='payment-confirmation-email', daemon=True).start()


def _send_new_blog_post_alerts(post):
    """Notify each active employer once a post is made public."""
    for user in User.objects.filter(is_active=True, is_staff=False).exclude(email=''):
        send_blog_alert_email(user, post)


# ── Auth ──────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user     = None
        try:
            user_by_email = User.objects.filter(email__iexact=email).first()
            if user_by_email:
                user = authenticate(request, username=user_by_email.username, password=password)
        except User.DoesNotExist:
            pass
        if user is None:
            user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            if user.is_superuser:
                return redirect('Authentication:admin_dashboard')
            return redirect('Authentication:employer_dashboard')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'Authentication/login.html')


def signup_view(request):
    """
    Validates signup data and stores it in the database as a PendingSignup.
    No user is created here — account creation happens only after payment succeeds.
    Returns JSON so the multi-step form can stay on the page.
    """
    if request.method == 'POST':
        from django.http import JsonResponse
        from django.urls import reverse
        import secrets

        first_name       = request.POST.get('firstName', '').strip()
        last_name        = request.POST.get('lastName', '').strip()
        email            = request.POST.get('email', '').strip().lower()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        phone            = request.POST.get('phone', '').strip()
        city             = request.POST.get('city', '').strip()
        plan_raw         = request.POST.get('plan', 'standard').strip()
        plan             = plan_raw if plan_raw in ('standard', 'premium') else 'standard'

        # ── Field validation ──────────────────────────────────────────────────
        if not first_name:
            return JsonResponse({'ok': False, 'error': 'Please enter your first name.'})
        if not last_name:
            return JsonResponse({'ok': False, 'error': 'Please enter your last name.'})
        if not email:
            return JsonResponse({'ok': False, 'error': 'Please enter your email address.'})
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'ok': False, 'error': 'Please enter a valid email address.'})
        if not password:
            return JsonResponse({'ok': False, 'error': 'Please enter a password.'})
        if len(password) < 8:
            return JsonResponse({'ok': False, 'error': 'Password must be at least 8 characters.'})
        if password != confirm_password:
            return JsonResponse({'ok': False, 'error': 'Passwords do not match.'})
        try:
            validate_password(password)
        except ValidationError as error:
            return JsonResponse({'ok': False, 'error': ' '.join(error.messages)})
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'ok': False, 'error': 'An account with this email already exists.'})

        # ── Store signup data in database (survives cross-domain redirects) ────
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=2)
        PendingSignup.objects.filter(email__iexact=email, expires_at__lt=timezone.now()).delete()
        pending, _ = PendingSignup.objects.update_or_create(
            email=email,
            defaults={
                'first_name': first_name,
                'last_name': last_name,
                # A pending signup can exist briefly before checkout; never store its
                # password in plain text during that interval.
                'password': make_password(password),
                'phone': phone,
                'city': city,
                'plan': plan,
                'service': request.POST.get('service', '').strip(),
                'how_heard': request.POST.get('howHeard', '').strip(),
                'request_details': request.POST.get('requestDetails', '').strip(),
                'token': token,
                'expires_at': expires_at,
            },
        )
        request.session['pending_signup_token'] = pending.token
        request.session.modified = True

        return JsonResponse({'ok': True, 'redirect': reverse('Authentication:payment_page')})

    return render(request, 'Authentication/signup.html')


def payment_page(request):
    """
    Renders the Flutterwave inline payment page.
    Requires a pending_signup in session or database — otherwise sends user back to signup.
    """
    from django.conf import settings as django_settings

    pending = None
    token = request.session.get('pending_signup_token')
    if token:
        pending = PendingSignup.objects.filter(token=token).first()
    if not pending:
        return redirect('Authentication:signup')
    if pending.is_expired:
        pending.delete()
        return redirect('Authentication:signup')

    # Allow the employer to save/adjust their request details right on the
    # payment screen before completing the subscription.
    if request.method == 'POST':
        pending.request_details = request.POST.get('requestDetails', '').strip()
        pending.save(update_fields=['request_details'])

    plan        = pending.plan
    amount      = EmployerProfile.PLAN_AMOUNTS[plan]
    plan_label  = 'Premium Plan — ₦20,000' if plan == 'premium' else 'Standard Plan — ₦10,000'

    context = {
        'flw_public_key': django_settings.FLUTTERWAVE_PUBLIC_KEY,
        'email':          pending.email,
        'first_name':     pending.first_name,
        'last_name':      pending.last_name,
        'phone':          pending.phone,
        'request_details': pending.request_details,
        'amount':         amount,
        'plan':           plan,
        'plan_label':     plan_label,
        'tx_ref_token':   pending.token,
    }
    return render(request, 'Authentication/payment.html', context)


def payment_redirect(request):
    """
    Server-side redirect to Flutterwave hosted payment page.
    This avoids the unreliable inline checkout JS modal.
    """
    from django.conf import settings as django_settings

    pending = None
    token = request.session.get('pending_signup_token')
    if token:
        pending = PendingSignup.objects.filter(token=token).first()
    if not pending:
        return redirect('Authentication:signup')

    if pending.is_expired:
        pending.delete()
        return redirect('Authentication:signup')

    plan = pending.plan
    amount = EmployerProfile.PLAN_AMOUNTS[plan]
    tx_ref = pending.token

    callback_url = _payment_callback_url(request)

    payload = {
        "tx_ref": tx_ref,
        "amount": str(amount),
        "currency": "NGN",
        "redirect_url": callback_url,
        "payment_options": "card,account,ussd",
        "customer": {
            "email": pending.email,
            "phone_number": pending.phone,
            "name": pending.first_name + ' ' + pending.last_name,
        },
        "customizations": {
            "title": "SelectRoyalMaids",
            "description": 'Premium Plan — ₦20,000' if plan == 'premium' else 'Standard Plan — ₦10,000',
        },
    }

    try:
        resp = http_requests.post(
            'https://api.flutterwave.com/v3/payments',
            headers={
                'Authorization': 'Bearer ' + django_settings.FLUTTERWAVE_SECRET_KEY,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (http_requests.RequestException, ValueError):
        logger.exception('Flutterwave checkout initialization failed.')
        messages.error(request, 'Unable to connect to payment gateway. Please try again.')
        return redirect('Authentication:payment_page')

    if data.get('status') == 'success' and data.get('data', {}).get('link'):
        return redirect(data['data']['link'])

    messages.error(request, 'Payment initialization failed. Please try again or contact support.')
    return redirect('Authentication:payment_page')


def payment_callback(request):
    """
    Flutterwave redirects here after the customer completes (or cancels) payment.
    Query params: status, tx_ref, transaction_id
    We verify server-side, then create the account only on confirmed success.
    """
    try:
        return _payment_callback_inner(request)
    except Exception:
        logger.exception('Unhandled exception in payment_callback.')
        return redirect('Authentication:payment_failed')


def _payment_callback_inner(request):
    from django.conf import settings as django_settings

    callback_data = request.POST if request.method == 'POST' else request.GET
    status         = callback_data.get('status', '')
    transaction_id = callback_data.get('transaction_id', '')
    tx_ref         = callback_data.get('tx_ref', '')

    logger.info('payment_callback received: status=%s tx_ref=%s transaction_id=%s',
                status, tx_ref, transaction_id)

    # ── Payment not completed / cancelled ────────────────────────────────────
    # Flutterwave returns different success labels depending on the payment
    # method: 'successful' (most methods), 'completed' (card payments) and
    # occasionally 'success-pending-validation'. Treat all of them as paid,
    # then confirm authoritatively via the server-side verify call below.
    if status not in ('successful', 'completed', 'success-pending-validation') or not transaction_id:
        logger.warning('payment_callback: non-successful status=%s, redirecting to failed.', status)
        return redirect('Authentication:payment_failed')

    # ── Server-side verification ──────────────────────────────────────────────
    try:
        verify_url = django_settings.FLUTTERWAVE_VERIFY_URL.format(id=transaction_id)
        resp = http_requests.get(
            verify_url,
            headers={'Authorization': f'Bearer {django_settings.FLUTTERWAVE_SECRET_KEY}'},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except (http_requests.RequestException, ValueError):
        logger.exception('Flutterwave transaction verification request failed.')
        return redirect('Authentication:payment_failed')

    transaction_data = data.get('data', {})
    logger.info('payment_callback verify response: status=%s tx_status=%s amount=%s currency=%s tx_ref=%s',
                data.get('status'), transaction_data.get('status'),
                transaction_data.get('amount'), transaction_data.get('currency'),
                transaction_data.get('tx_ref'))

    if data.get('status') != 'success' or transaction_data.get('status') != 'successful':
        logger.warning('payment_callback: verification failed — data=%s', data)
        return redirect('Authentication:payment_failed')

    # ── Retrieve pending signup from database ─────────────────────────────────
    pending = PendingSignup.objects.filter(token=tx_ref).first()
    if not pending:
        logger.warning('payment_callback: no PendingSignup for tx_ref=%s — may have already been processed.', tx_ref)
        # Could be a duplicate callback for an already-processed payment.
        # Try to find the created user and redirect them to success.
        existing_user = User.objects.filter(
            employer_profile__payment_ref=str(transaction_id)
        ).first()
        if existing_user:
            try:
                existing_user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, existing_user)
            except Exception:
                pass
            return redirect('Authentication:payment_success')
        return redirect('Authentication:signup')

    if hasattr(pending, 'is_expired') and pending.is_expired:
        pending.delete()
        logger.warning('payment_callback: PendingSignup expired for tx_ref=%s', tx_ref)
        return redirect('Authentication:signup')

    # ── Amount validation (use int comparison to avoid float precision issues) ─
    if transaction_data.get('tx_ref') != pending.token:
        logger.error('payment_callback: tx_ref mismatch flw=%s pending=%s',
                     transaction_data.get('tx_ref'), pending.token)
        return redirect('Authentication:payment_failed')
    if transaction_data.get('currency') != 'NGN':
        logger.error('payment_callback: currency mismatch: %s', transaction_data.get('currency'))
        return redirect('Authentication:payment_failed')
    try:
        # Round to nearest integer to handle Flutterwave returning 10000.0 vs 10000
        flw_amount = round(float(transaction_data.get('amount', 0)))
    except (TypeError, ValueError):
        logger.exception('payment_callback: could not parse amount %s', transaction_data.get('amount'))
        return redirect('Authentication:payment_failed')
    expected_amt = int(EmployerProfile.PLAN_AMOUNTS[pending.plan])
    if flw_amount != expected_amt:
        logger.error('payment_callback: amount mismatch flw=%s expected=%s', flw_amount, expected_amt)
        return redirect('Authentication:payment_failed')

    # ── Create the account now that payment is confirmed ──────────────────────
    user = None
    try:
        with transaction.atomic():
            pending = PendingSignup.objects.select_for_update().get(pk=pending.pk)
            user = User.objects.filter(email__iexact=pending.email).first()
            if not user:
                user = User(
                    username=pending.email,
                    email=pending.email,
                    first_name=pending.first_name,
                    last_name=pending.last_name,
                    is_active=True,
                )
                try:
                    identify_hasher(pending.password)
                    user.password = pending.password
                except ValueError:
                    # Supports pending records created before password hashing was added.
                    user.password = make_password(pending.password)
                user.save()

            EmployerProfile.objects.update_or_create(
                user=user,
                defaults={
                    'phone': pending.phone,
                    'city': pending.city,
                    'service_needed': pending.service,
                    'how_heard': pending.how_heard,
                    'request_details': pending.request_details,
                    'plan': pending.plan,
                    'payment_status': 'paid',
                    'payment_ref': str(transaction_id),
                },
            )
            pending.delete()
    except (IntegrityError, PendingSignup.DoesNotExist):
        logger.exception('Could not finalize verified Flutterwave payment %s.', transaction_id)
        return redirect('Authentication:payment_failed')
    except Exception:
        logger.exception('Unexpected error finalizing payment %s.', transaction_id)
        return redirect('Authentication:payment_failed')

    if user is None:
        logger.error('Payment %s verified but user object is None after account creation.', transaction_id)
        return redirect('Authentication:payment_failed')

    # Clear the pending signup token from the session
    try:
        request.session.pop('pending_signup_token', None)
    except Exception:
        pass  # session may not be available in all contexts

    # Log the user in. We set the backend directly — this is the correct approach
    # when a user object was not fetched via authenticate(). Django's login()
    # calls session.cycle_key() which requires a real session middleware — on
    # production this is always present.
    logged_in = False
    try:
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        logged_in = True
        logger.info('User %s logged in after payment.', user.email)
    except Exception:
        logger.exception('login() failed after payment for %s — will redirect to login page.', user.email)

    # Do not make Flutterwave's browser callback wait for SMTP.  On Render a
    # stalled mail connection can otherwise outlive the request and produce a
    # 500 after the account/payment has already been committed.
    _send_payment_confirmation_emails_in_background(user, user.employer_profile.plan)

    if logged_in:
        return redirect('Authentication:payment_success')

    # Login failed (rare session edge case) — redirect to login with a message
    # so the user can log in manually. Their account IS created and paid.
    logger.warning('Redirecting %s to login after payment because session login failed.', user.email)
    return redirect(f"{reverse('Authentication:login')}?payment=done")


def payment_success(request):
    """Success landing page shown after a confirmed payment."""
    # Accept authenticated users OR users arriving directly from a payment
    # (payment=done param) to handle the rare case where session login failed.
    if not request.user.is_authenticated:
        if request.GET.get('payment') == 'done':
            # Show a minimal success message — they are paid, just need to log in
            return render(request, 'Authentication/payment_success.html', {'needs_login': True})
        return redirect('Authentication:login')
    return render(request, 'Authentication/payment_success.html', {'needs_login': False})


def payment_failed(request):
    """Shown when payment is cancelled or verification fails."""
    pending = None
    token = request.session.get('pending_signup_token')
    if token:
        pending = PendingSignup.objects.filter(token=token).first()
    if pending:
        try:
            # Failed payments occur before an account is created.
            send_payment_failed_email(User(email=pending.email, username=pending.email))
        except Exception:
            logger.exception('Unable to send payment-failed email.')
    return render(request, 'Authentication/payment_failed.html')


def logout_view(request):
    logout(request)
    return redirect('MaidApp:index')


# ── Password Reset ────────────────────────────────────────────────────────────

@require_POST
def password_reset_request(request):
    """
    AJAX endpoint: validate email, generate a signed reset token, send the link.
    Always returns ok=True for valid-looking emails (prevents user enumeration).
    """
    from django.http import JsonResponse
    import json, secrets
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_encode
    from django.utils.encoding import force_bytes

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    email = data.get('email', '').strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

    # Look up the user silently — don't reveal whether the email exists
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user:
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = (
            request.scheme + '://' + request.get_host()
            + reverse('Authentication:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        )
        try:
            send_password_reset_email(user, reset_url)
        except Exception:
            logger.exception('Failed to send password reset email to %s', email)

    # Always return success to prevent email enumeration
    return JsonResponse({'ok': True})


def password_reset_confirm(request, uidb64, token):
    """
    GET  — show the set-new-password form (validates token first).
    POST — save the new password, send confirmation email, redirect to login.
    """
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    # Decode the user
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Validate the token
    token_valid = user is not None and default_token_generator.check_token(user, token)

    if request.method == 'GET':
        return render(request, 'Authentication/password_reset_confirm.html', {
            'token_valid': token_valid,
            'uidb64': uidb64,
            'token': token,
        })

    # POST — process the new password
    from django.http import JsonResponse
    import json

    if not token_valid:
        return JsonResponse({'error': 'This reset link is invalid or has expired. Please request a new one.'}, status=400)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    password  = data.get('password', '')
    password2 = data.get('password2', '')

    if not password:
        return JsonResponse({'error': 'Please enter a new password.'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters.'}, status=400)
    if password != password2:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)
    try:
        validate_password(password, user=user)
    except ValidationError as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

    user.set_password(password)
    user.save()

    # Send confirmation email (non-blocking — failure must not break the flow)
    try:
        send_password_changed_email(user)
    except Exception:
        logger.exception('Failed to send password-changed email to %s', user.email)

    return JsonResponse({'ok': True})


# ── Dashboards ────────────────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    from django.utils.html import strip_tags
    import re

    # ── Payment gate ──────────────────────────────────────────────────────────
    try:
        profile = request.user.employer_profile
    except Exception:
        profile = None

    if profile is None or not profile.is_paid:
        return redirect('Authentication:payment_page')
    unread_count = SupportMessage.objects.filter(
        employer=request.user,
        is_read=False,
    ).exclude(sender=request.user).count()

    # Real maid requests — messages the employer sent that start with the request header
    raw_requests = (
        SupportMessage.objects
        .filter(employer=request.user, sender=request.user)
        .filter(body__contains='New employer placement request')
        .order_by('-created_at')[:5]
    )

    # Parse service and city out of each stored HTML table body
    def _extract(body, label):
        pattern = re.compile(
            r'<td[^>]*>\s*' + re.escape(label) + r'\s*</td>\s*<td[^>]*>(.*?)</td>',
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(body)
        if m:
            return strip_tags(m.group(1)).strip() or '—'
        return '—'

    recent_requests = []
    for msg in raw_requests:
        recent_requests.append({
            'service':  _extract(msg.body, 'Service'),
            'city':     _extract(msg.body, 'City / Area'),
            'date':     msg.created_at,
        })

    # Dashboard stat counts
    total_requests  = SupportMessage.objects.filter(
        employer=request.user, sender=request.user,
        body__contains='New employer placement request',
    ).count()
    maids_available = MaidProfile.objects.filter(is_active=True, assign_status='unassigned').count()

    # Maid recommendations from admin (pending only — declined/responded ones are hidden)
    recommendations = MaidRecommendation.objects.filter(
        employer=request.user,
        status='pending',
    ).select_related('maid')

    return render(request, 'Dashboard/Employer.html', {
        'unread_count':    unread_count,
        'recent_requests': recent_requests,
        'profile':         profile,
        'total_requests':  total_requests,
        'maids_available': maids_available,
        'recommendations': recommendations,
        'recommendation_count': recommendations.count(),
    })


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')

    maid_query = request.GET.get('mq', '').strip()
    maids_qs = MaidProfile.objects.filter(is_active=True).order_by('-created_at', '-id')
    if maid_query:
        maids_qs = maids_qs.filter(
            Q(full_name__icontains=maid_query) |
            Q(reg_number__icontains=maid_query)
        ).distinct()

    # Paginate the maids table — rendering every profile inline made the page
    # multi-megabyte. 50 per page keeps the dashboard snappy; search still
    # covers the whole table.
    maids_page = Paginator(maids_qs, 50).get_page(request.GET.get('page', 1))

    employer_query = request.GET.get('eq', '').strip()
    employers_qs = EmployerProfile.objects.filter(payment_status='paid').select_related('user').order_by('-created_at')
    if employer_query:
        employers_qs = employers_qs.filter(
            Q(user__first_name__icontains=employer_query) |
            Q(user__last_name__icontains=employer_query) |
            Q(user__email__icontains=employer_query) |
            Q(phone__icontains=employer_query)
        )

    paid_employers = EmployerProfile.objects.filter(payment_status='paid')
    # Revenue + count computed in a single DB query instead of iterating every
    # employer row in Python (this used to fetch all rows on every page load).
    revenue_agg = paid_employers.aggregate(
        cnt=Count('id'),
        total=Sum(
            Case(
                When(plan='premium', then=Value(EmployerProfile.PLAN_AMOUNTS['premium'])),
                default=Value(EmployerProfile.PLAN_AMOUNTS['standard']),
                output_field=IntegerField(),
            )
        ),
    )
    paid_employer_count = revenue_agg['cnt'] or 0
    total_revenue = revenue_agg['total'] or 0

    blog_paginator = Paginator(BlogPost.objects.all(), 20)
    blog_page_num = request.GET.get('page', 1)

    # Employer pickers that back the "Assigned To" selector on the maid
    # placement form. maid_count lets the UI flag Standard employers that
    # already hold their one allowed maid.
    assignment_employers_site = (
        EmployerProfile.objects
        .select_related('user')
        .annotate(maid_count=Count('user__assigned_maids'))
        .order_by('user__first_name', 'user__last_name')
    )
    assignment_employers_legacy = (
        LegacyEmployer.objects.filter(is_spam=False)
        .annotate(maid_count=Count('assigned_maids'))
        .order_by('legacy_id')
    )

    # ── All Employers tab data ────────────────────────────────────────────────
    ae_tab = request.GET.get('ae_tab', request.GET.get('tab', 'site'))
    if ae_tab not in ('site', 'legacy'):
        ae_tab = 'site'
    ae_query = request.GET.get('q', '').strip()
    ae_plan = request.GET.get('plan', '')
    ae_show_spam = request.GET.get('spam') == '1'

    ae_site_page = ae_legacy_page = None
    ae_maids_by_employer = {}
    ae_placements_by_employer = {}
    ae_maids_by_reg = {}

    if ae_tab == 'site':
        ae_qs = EmployerProfile.objects.select_related('user').annotate(
            maid_count=Count('user__assigned_maids'))
        if ae_query:
            ae_qs = ae_qs.filter(
                Q(user__first_name__icontains=ae_query) |
                Q(user__last_name__icontains=ae_query) |
                Q(user__username__icontains=ae_query) |
                Q(user__email__icontains=ae_query) |
                Q(phone__icontains=ae_query)
            )
        if ae_plan in ('standard', 'premium'):
            ae_qs = ae_qs.filter(plan=ae_plan)
        ae_site_page = Paginator(ae_qs.order_by('-created_at'), 25).get_page(request.GET.get('page', 1))
        ae_employer_ids = [profile.user_id for profile in ae_site_page.object_list]
        for maid in MaidProfile.objects.filter(assigned_employer_id__in=ae_employer_ids):
            ae_maids_by_employer.setdefault(maid.assigned_employer_id, []).append(maid)
        ae_concluded = (
            PlacementRequest.objects
            .filter(employer_id__in=ae_employer_ids, candidate__isnull=False, status='concluded')
            .select_related('candidate')
            .order_by('-concluded_at')
        )
        for placement in ae_concluded:
            ae_placements_by_employer.setdefault(placement.employer_id, []).append(placement)
    else:
        ae_qs = LegacyEmployer.objects.all()
        if not ae_show_spam:
            ae_qs = ae_qs.filter(is_spam=False)
        if ae_query:
            ae_qs = ae_qs.filter(
                Q(first_name__icontains=ae_query) |
                Q(last_name__icontains=ae_query) |
                Q(email__icontains=ae_query) |
                Q(phone__icontains=ae_query) |
                Q(company__icontains=ae_query) |
                Q(home_address__icontains=ae_query)
            )
        if ae_plan in ('standard', 'premium'):
            ae_qs = ae_qs.filter(plan=ae_plan)
        ae_legacy_page = Paginator(ae_qs.order_by('legacy_id'), 25).get_page(request.GET.get('page', 1))
        ae_row_ids = [row.pk for row in ae_legacy_page.object_list]
        for maid in MaidProfile.objects.filter(assigned_legacy_employer_id__in=ae_row_ids):
            ae_maids_by_employer.setdefault(maid.assigned_legacy_employer_id, []).append(maid)
        ae_reg_numbers = {row.assigned_reg_number for row in ae_legacy_page.object_list if row.assigned_reg_number}
        if ae_reg_numbers:
            for maid in MaidProfile.objects.filter(reg_number__in=ae_reg_numbers):
                ae_maids_by_reg.setdefault(maid.reg_number.lower(), maid)

    ae_site_rows = []
    ae_legacy_rows = []
    if ae_tab == 'site' and ae_site_page:
        ae_site_rows = [
            {
                'profile':    profile,
                'maids':      ae_maids_by_employer.get(profile.user_id, []),
                'placements': ae_placements_by_employer.get(profile.user_id, []),
            }
            for profile in ae_site_page.object_list
        ]
    elif ae_tab == 'legacy' and ae_legacy_page:
        ae_legacy_rows = [
            {
                'row':         record,
                'maids':       ae_maids_by_employer.get(record.pk, []),
                'legacy_maid': ae_maids_by_reg.get(record.assigned_reg_number.lower()) if record.assigned_reg_number else None,
            }
            for record in ae_legacy_page.object_list
        ]

    context = {
        # stat cards
        'maid_count':            MaidRegistration.objects.count(),
        'paid_employer_count':   paid_employer_count,
        'total_revenue':         total_revenue,
        'support_count':         SupportMessage.objects.filter(
                                     employer__isnull=False,
                                 ).values('employer').distinct().count(),
        # unread badge — messages sent by employers (non-staff) that admin hasn't read
        'unread_count':          SupportMessage.objects.filter(
                                     is_read=False,
                                     sender__is_staff=False,
                                 ).count(),
        # maids tab (paginated)
        'maid_query':            maid_query,
        'maid_total':            maids_page.paginator.count,
        'recent_maids':          MaidRegistration.objects.order_by('-created_at')[:5],
        'all_maids':             maids_page,
        # employers tab
        'employer_query':        employer_query,
        'employers':             employers_qs,
        # all employers tab
        'ae_tab': ae_tab,
        'ae_query': ae_query,
        'ae_plan': ae_plan,
        'ae_show_spam': ae_show_spam,
        'ae_site_page': ae_site_page,
        'ae_legacy_page': ae_legacy_page,
        'ae_site_rows': ae_site_rows,
        'ae_legacy_rows': ae_legacy_rows,
        'ae_stats': {
            'site_total':     EmployerProfile.objects.count(),
            'legacy_total':   LegacyEmployer.objects.filter(is_spam=False).count(),
            'legacy_spam':    LegacyEmployer.objects.filter(is_spam=True).count(),
            'assigned_total': MaidProfile.objects.filter(assign_status='assigned').count(),
        },
        # content tabs
        'faqs':                  FAQ.objects.all(),
        'services':              Service.objects.all(),
        'service_icon_choices':  Service.ICON_CHOICES,
        'service_badge_choices': Service.BADGE_CHOICES,
        'placements':            PlacementRequest.objects.select_related('employer', 'candidate').all()[:50],
        'assignment_employers_site':   assignment_employers_site,
        'assignment_employers_legacy': assignment_employers_legacy,
        'page_obj':           blog_paginator.get_page(blog_page_num),
        'page_range':         blog_paginator.get_elided_page_range(blog_page_num or 1, on_each_side=2, on_ends=1),
        'blog_categories':    BlogPost.CATEGORY_CHOICES,
    }
    return render(request, 'Dashboard/Admin.html', context)


@login_required
def recommend_maids_list(request):
    """JSON feed for the Recommend-a-Maid modal.

    The modal loads this lazily on first open so the dashboard itself stays
    lightweight while still offering every active maid (newest first).
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Forbidden.'}, status=403)

    maids = (
        MaidProfile.objects.filter(is_active=True)
        .order_by('-created_at', '-id')
    )
    data = [
        {
            'id': m.id,
            'full_name': m.full_name,
            'first_name': m.first_name,
            'reg_number': m.reg_number,
            'age': m.age or '',
            'photo_url': m.photo_url() if m.photo_url() else '',
            'available': m.is_available,
        }
        for m in maids
    ]
    return JsonResponse({'count': len(data), 'maids': data})


@login_required
def recommend_maid(request, employer_id):
    """Let an admin recommend a maid to a specific employer (from the modal)."""
    if not request.user.is_superuser or request.method != 'POST':
        return redirect('Authentication:employer_dashboard')

    employer = get_object_or_404(User, pk=employer_id)
    maid = get_object_or_404(MaidProfile, pk=request.POST.get('maid_id'), is_active=True)
    notes = request.POST.get('notes', '').strip()

    recommendation, created = MaidRecommendation.objects.get_or_create(
        employer=employer,
        maid=maid,
        defaults={
            'status': 'pending',
            'recommended_by': request.user,
            'notes': notes,
        },
    )
    if created:
        # Notify the employer by email that a maid has been recommended for them.
        try:
            send_maid_recommended_email(employer, maid)
        except Exception:
            logger.exception('Failed to send maid-recommended email to %s.', employer.email)
        messages.success(request, f'Recommended {maid.full_name} to {employer.get_full_name() or employer.username}.')
    else:
        messages.info(request, f'{maid.full_name} was already recommended to this employer.')

    return redirect('/admin/dashboard/?tab=employers')


@login_required
def respond_recommendation(request, recommendation_id):
    """Let an employer accept or decline a recommended maid card."""
    if request.method != 'POST':
        return redirect('Authentication:employer_dashboard')

    recommendation = get_object_or_404(
        MaidRecommendation,
        pk=recommendation_id,
        employer=request.user,
        status='pending',
    )
    action = request.POST.get('action', '').strip()

    if action == 'accept':
        recommendation.accept()
        # Notify admin as a support message (renders as a card in the support chat).
        card_html = (
            '<div style="border:1px solid #bbf7d0;background:#f0fdf4;border-radius:10px;'
            'padding:12px 14px;font-family:\'Inter\',sans-serif;line-height:1.5;">'
            '<div style="font-size:.72rem;font-weight:800;letter-spacing:.05em;color:#15803d;'
            'text-transform:uppercase;margin-bottom:6px;">'
            '<i class="fa-solid fa-circle-check"></i> Recommendation Accepted</div>'
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<div style="width:40px;height:40px;border-radius:50%;background:#bbf7d0;color:#15803d;'
            'display:flex;align-items:center;justify-content:center;font-weight:800;flex-shrink:0;">'
            '<i class="fa-solid fa-user-check"></i></div>'
            '<div>'
            '<div style="font-size:.9rem;font-weight:700;color:#14532d;">'
            '<a href="/view-profile/?slug=' + recommendation.maid.slug + '" '
            'target="_blank" style="color:#166534;text-decoration:underline;">'
            + recommendation.maid.full_name + '</a>'
            '<span style="font-weight:500;color:#166534;"> (' + recommendation.maid.reg_number + ')</span>'
            '</div>'
            '<div style="font-size:.78rem;color:#166534;">' + (request.user.get_full_name() or request.user.username) + ' accepted this recommended maid.</div>'
            '</div></div></div>'
        )
        SupportMessage.objects.create(
            sender=request.user,
            employer=request.user,
            body=card_html,
        )
        messages.success(
            request,
            f'You have accepted {recommendation.maid.full_name}. Our team has been notified and will proceed with the placement.'
        )
    elif action == 'decline':
        recommendation.decline()
        messages.info(request, f'{recommendation.maid.full_name} has been removed from your recommendations.')
    else:
        messages.error(request, 'Invalid action.')

    return redirect('Authentication:employer_dashboard')
@login_required
def conclude_placement(request, placement_id):
    if not request.user.is_superuser or request.method != 'POST':
        return redirect('Authentication:employer_dashboard')
    placement = get_object_or_404(PlacementRequest, pk=placement_id, status='requested')
    candidate = get_object_or_404(MaidProfile, pk=request.POST.get('candidate_id'), is_active=True)
    placement.conclude(candidate)
    candidate.assign_status = 'assigned'
    candidate.save(update_fields=['assign_status'])
    message = f'Placement concluded for {placement.employer.get_full_name() or placement.employer.username}. '
    message += 'The Premium replacement window ends ' + placement.replacement_expires_at.strftime('%d %b %Y') + '.' if placement.plan == 'premium' else 'Standard requests do not include free replacements.'
    messages.success(request, message)
    return redirect('/admin/dashboard/?tab=placements')


@login_required
def record_free_replacement(request, placement_id):
    if not request.user.is_superuser or request.method != 'POST':
        return redirect('Authentication:employer_dashboard')
    placement = get_object_or_404(PlacementRequest, pk=placement_id)
    candidate = get_object_or_404(MaidProfile, pk=request.POST.get('candidate_id'), is_active=True, assign_status='unassigned')
    try:
        replacement = placement.record_free_replacement(candidate)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('/admin/dashboard/?tab=placements')
    candidate.assign_status = 'assigned'
    candidate.save(update_fields=['assign_status'])
    messages.success(request, f'Free Premium replacement recorded for the same {replacement.role} position. Coverage still expires {replacement.replacement_expires_at.strftime("%d %b %Y")}.')
    return redirect('/admin/dashboard/?tab=placements')


# ── MaidProfile CRUD ──────────────────────────────────────────────────────────

@login_required
def maid_edit(request, maid_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    maid = get_object_or_404(MaidProfile, pk=maid_id)
    page = request.POST.get('page', 1)
    if request.method == 'POST':
        maid.full_name      = request.POST.get('full_name',   maid.full_name).strip()
        maid.address        = request.POST.get('address',     maid.address).strip()
        maid.age            = request.POST.get('age',         maid.age).strip()
        maid.phone          = request.POST.get('phone',       maid.phone).strip()
        maid.email          = request.POST.get('email',       maid.email).strip()
        maid.description    = request.POST.get('description', maid.description).strip()
        maid.assign_status  = request.POST.get('assign_status', maid.assign_status)
        maid.assigned_employer, maid.assigned_legacy_employer = _resolve_assignment_target(
            request.POST.get('assigned_to'))
        maid.is_featured    = request.POST.get('is_featured') == 'on'
        maid.is_active      = request.POST.get('is_active')  == 'on'
        if request.FILES.get('profile_image'):
            maid.image = request.FILES['profile_image']
        try:
            maid.save()
        except ValueError as exc:
            # Plan capacity violated (e.g. a Standard employer getting a 2nd maid).
            messages.error(request, str(exc))
            return redirect(f'/admin/dashboard/?tab=maids&page={page}')
        messages.success(request, f'Profile "{maid.full_name}" updated.')
    return redirect(f'/admin/dashboard/?tab=maids&page={page}')


@login_required
def maid_delete(request, maid_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        maid = MaidProfile.objects.filter(pk=maid_id).first()
        if maid:
            name = maid.full_name
            maid.delete()
            messages.success(request, f'Profile "{name}" deleted.')
    page = request.POST.get('page', 1)
    return redirect(f'/admin/dashboard/?tab=maids&page={page}')


@login_required
def maid_toggle_status(request, maid_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        maid = get_object_or_404(MaidProfile, pk=maid_id)
        maid.assign_status = 'unassigned' if maid.assign_status == 'assigned' else 'assigned'
        maid.save()
        messages.success(request, f'{maid.full_name} marked as {"Available" if maid.assign_status == "unassigned" else "Assigned"}.')
    page = request.POST.get('page', 1)
    return redirect(f'/admin/dashboard/?tab=maids&page={page}')


@login_required
def maid_create(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if full_name:
            import re
            slug_base = re.sub(r'[^a-z0-9]+', '-', full_name.lower()).strip('-')
            slug = slug_base
            counter = 1
            while MaidProfile.objects.filter(slug=slug).exists():
                slug = f'{slug_base}-{counter}'
                counter += 1
            maid = MaidProfile(
                slug=slug,
                full_name=full_name,
                address=request.POST.get('address', '').strip(),
                age=request.POST.get('age', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                description=request.POST.get('description', '').strip(),
                image=request.FILES.get('profile_image'),
                assign_status=request.POST.get('assign_status', 'unassigned'),
                is_featured=request.POST.get('is_featured') == 'on',
                is_active=True,
            )
            maid.assigned_employer, maid.assigned_legacy_employer = _resolve_assignment_target(
                request.POST.get('assigned_to'))
            try:
                maid.save()
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('/admin/dashboard/?tab=maids')
            messages.success(request, f'Maid "{full_name}" added.')
        else:
            messages.error(request, 'Full name is required.')
    return redirect('/admin/dashboard/?tab=maids')

@login_required
def all_employers(request):
    """Master list of every employer on the platform.

    Two sources are combined here:
      * 'site'   — employer accounts registered on this site (EmployerProfile);
      * 'legacy' — rows imported from the old website's request.sql dump
                   (LegacyEmployer).

    Each employer is shown with their details and every maid assigned to them
    (direct assignments plus, for site employers, concluded placements).
    """
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')

    tab = request.GET.get('tab', 'site')
    if tab not in ('site', 'legacy'):
        tab = 'site'
    query = request.GET.get('q', '').strip()
    plan = request.GET.get('plan', '')
    show_spam = request.GET.get('spam') == '1'

    site_page = legacy_page = None
    maids_by_employer = {}
    placements_by_employer = {}
    maids_by_reg = {}

    if tab == 'site':
        qs = EmployerProfile.objects.select_related('user').annotate(
            maid_count=Count('user__assigned_maids'))
        if query:
            qs = qs.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__username__icontains=query) |
                Q(user__email__icontains=query) |
                Q(phone__icontains=query)
            )
        if plan in ('standard', 'premium'):
            qs = qs.filter(plan=plan)
        site_page = Paginator(qs.order_by('-created_at'), 25).get_page(request.GET.get('page', 1))
        employer_ids = [profile.user_id for profile in site_page.object_list]
        for maid in MaidProfile.objects.filter(assigned_employer_id__in=employer_ids):
            maids_by_employer.setdefault(maid.assigned_employer_id, []).append(maid)
        concluded = (
            PlacementRequest.objects
            .filter(employer_id__in=employer_ids, candidate__isnull=False, status='concluded')
            .select_related('candidate')
            .order_by('-concluded_at')
        )
        for placement in concluded:
            placements_by_employer.setdefault(placement.employer_id, []).append(placement)
    else:
        qs = LegacyEmployer.objects.all()
        if not show_spam:
            qs = qs.filter(is_spam=False)
        if query:
            qs = qs.filter(
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query) |
                Q(company__icontains=query) |
                Q(home_address__icontains=query)
            )
        if plan in ('standard', 'premium'):
            qs = qs.filter(plan=plan)
        legacy_page = Paginator(qs.order_by('legacy_id'), 25).get_page(request.GET.get('page', 1))
        row_ids = [row.pk for row in legacy_page.object_list]
        for maid in MaidProfile.objects.filter(assigned_legacy_employer_id__in=row_ids):
            maids_by_employer.setdefault(maid.assigned_legacy_employer_id, []).append(maid)
        # Resolve the maid reg numbers recorded in the dump in a single query.
        reg_numbers = {row.assigned_reg_number for row in legacy_page.object_list if row.assigned_reg_number}
        if reg_numbers:
            for maid in MaidProfile.objects.filter(reg_number__in=reg_numbers):
                maids_by_reg.setdefault(maid.reg_number.lower(), maid)

    context = {
        'tab': tab,
        'query': query,
        'plan': plan,
        'show_spam': show_spam,
        'site_page': site_page,
        'legacy_page': legacy_page,
        'stats': {
            'site_total':     EmployerProfile.objects.count(),
            'legacy_total':   LegacyEmployer.objects.filter(is_spam=False).count(),
            'legacy_spam':    LegacyEmployer.objects.filter(is_spam=True).count(),
            'assigned_total': MaidProfile.objects.filter(assign_status='assigned').count(),
        },
        'unread_count': SupportMessage.objects.filter(
                             is_read=False,
                             sender__is_staff=False,
                         ).count(),
    }
    if tab == 'site':
        context['site_rows'] = [
            {
                'profile':    profile,
                'maids':      maids_by_employer.get(profile.user_id, []),
                'placements': placements_by_employer.get(profile.user_id, []),
            }
            for profile in site_page.object_list
        ]
    else:
        context['legacy_rows'] = [
            {
                'row':         record,
                'maids':       maids_by_employer.get(record.pk, []),
                'legacy_maid': maids_by_reg.get(record.assigned_reg_number.lower()) if record.assigned_reg_number else None,
            }
            for record in legacy_page.object_list
        ]
    return render(request, 'Dashboard/AllEmployers.html', context)


@login_required
def faq_create(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        answer   = request.POST.get('answer', '').strip()
        order    = request.POST.get('order', 0)
        if question and answer:
            FAQ.objects.create(question=question, answer=answer, order=order)
            messages.success(request, 'FAQ added successfully.')
        else:
            messages.error(request, 'Question and answer are required.')
    return redirect('/admin/dashboard/?tab=faq')


@login_required
def faq_edit(request, faq_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    faq = get_object_or_404(FAQ, pk=faq_id)
    if request.method == 'POST':
        faq.question  = request.POST.get('question', faq.question).strip()
        faq.answer    = request.POST.get('answer',   faq.answer).strip()
        faq.order     = request.POST.get('order',    faq.order)
        faq.is_active = request.POST.get('is_active') == 'on'
        faq.save()
        messages.success(request, 'FAQ updated successfully.')
    return redirect('/admin/dashboard/?tab=faq')


@login_required
def faq_delete(request, faq_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        FAQ.objects.filter(pk=faq_id).delete()
        messages.success(request, 'FAQ deleted.')
    return redirect('/admin/dashboard/?tab=faq')


# ── Service CRUD ──────────────────────────────────────────────────────────────

@login_required
def service_create(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        slug  = request.POST.get('slug', '').strip()
        title = request.POST.get('title', '').strip()
        desc  = request.POST.get('description', '').strip()
        feats = request.POST.get('features', '').strip()
        if slug and title and desc and feats:
            raw_image_url = request.POST.get('image_url', '').strip()
            uploaded      = request.FILES.get('service_image')
            Service.objects.create(
                slug=slug, title=title,
                badge_label=request.POST.get('badge_label', '').strip(),
                badge_color=request.POST.get('badge_color', 'blue'),
                icon=request.POST.get('icon', 'fa-star'),
                description=desc, features=feats,
                # Resolve share/page links (e.g. share.google, unsplash.com
                # pages) to the actual image URL so they render in <img>.
                image_url=resolve_image_url(raw_image_url) if (raw_image_url and not uploaded) else '',
                image_file=uploaded,
                available_count=request.POST.get('available_count', '0+').strip(),
                avg_rating=request.POST.get('avg_rating', '4.9★').strip(),
                guarantee_days=int(request.POST.get('guarantee_days', 30) or 30),
                order=int(request.POST.get('order', 0) or 0),
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, f'Service "{title}" created.')
        else:
            messages.error(request, 'Slug, title, description and features are required.')
    return redirect('/admin/dashboard/?tab=services')


@login_required
def service_edit(request, service_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    svc = get_object_or_404(Service, pk=service_id)
    if request.method == 'POST':
        svc.slug            = request.POST.get('slug',            svc.slug).strip()
        svc.title           = request.POST.get('title',           svc.title).strip()
        svc.badge_label     = request.POST.get('badge_label',     svc.badge_label).strip()
        svc.badge_color     = request.POST.get('badge_color',     svc.badge_color)
        svc.icon            = request.POST.get('icon',            svc.icon)
        svc.description     = request.POST.get('description',     svc.description).strip()
        svc.features        = request.POST.get('features',        svc.features).strip()
        # ── Image handling: upload wins, then explicit removal, then URL ──────
        uploaded      = request.FILES.get('service_image')
        remove_image  = request.POST.get('remove_service_image') == 'on'

        if uploaded:
            # A fresh upload replaces BOTH the old local file and any stored URL.
            if svc.image_file:
                svc.image_file.delete(save=False)
            svc.image_file = uploaded
            svc.image_url = ''
        elif remove_image:
            # Explicit clear request → card degrades to the icon placeholder.
            if svc.image_file:
                svc.image_file.delete(save=False)
            svc.image_file = None
            svc.image_url = ''
        else:
            raw_image_url = request.POST.get('image_url', '').strip()
            if raw_image_url:
                resolved = resolve_image_url(raw_image_url)
                if resolved != svc.image_url and svc.image_file:
                    svc.image_file.delete(save=False)
                    svc.image_file = None
                svc.image_url = resolved
            # else: nothing supplied — keep whatever currently exists

        svc.available_count = request.POST.get('available_count', svc.available_count).strip()
        svc.avg_rating      = request.POST.get('avg_rating',      svc.avg_rating).strip()
        svc.guarantee_days  = int(request.POST.get('guarantee_days', svc.guarantee_days) or svc.guarantee_days)
        svc.order           = int(request.POST.get('order', svc.order) or svc.order)
        svc.is_active       = request.POST.get('is_active') == 'on'
        svc.save()
        messages.success(request, f'Service "{svc.title}" updated.')
    return redirect('/admin/dashboard/?tab=services')


@login_required
def service_delete(request, service_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        svc = Service.objects.filter(pk=service_id).first()
        if svc:
            name = svc.title
            svc.delete()
            messages.success(request, f'Service "{name}" deleted.')
    return redirect('/admin/dashboard/?tab=services')


# ── Blog CRUD ─────────────────────────────────────────────────────────────────

@login_required
def blog_create(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        slug  = request.POST.get('slug', '').strip()
        title = request.POST.get('title', '').strip()
        if slug and title:
            post = BlogPost.objects.create(
                slug=slug, title=title,
                excerpt=request.POST.get('excerpt', '').strip(),
                category=request.POST.get('category', 'general'),
                author_name='SelectRoyal Maids Admin',
                cover_image=resolve_image_url(request.POST.get('cover_image', '').strip()),
                cover_image_file=request.FILES.get('cover_image_file'),
                content=request.POST.get('content', '').strip(),
                tags=request.POST.get('tags', '').strip(),
                read_time=int(request.POST.get('read_time', 5) or 5),
                is_featured=request.POST.get('is_featured') == 'on',
                is_published=request.POST.get('is_published') == 'on',
                published_at=timezone.now(),
            )
            messages.success(request, f'Post "{title}" created.')
            if post.is_published:
                _send_new_blog_post_alerts(post)
            return redirect('/admin/dashboard/?tab=blog')
        else:
            messages.error(request, 'Slug and title are required.')
    return render(request, 'Dashboard/blog_create.html', {
        'blog_categories': BlogPost.CATEGORY_CHOICES,
    })


@login_required
def blog_edit(request, post_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    post = get_object_or_404(BlogPost, pk=post_id)
    if request.method == 'POST':
        was_published = post.is_published
        post.slug         = request.POST.get('slug',         post.slug).strip()
        post.title        = request.POST.get('title',        post.title).strip()
        post.excerpt      = request.POST.get('excerpt',      post.excerpt).strip()
        post.category     = request.POST.get('category',     post.category)
        post.author_name  = 'SelectRoyal Maids Admin'
        cover_url = request.POST.get('cover_image', '').strip()
        uploaded_cover = request.FILES.get('cover_image_file')
        if uploaded_cover:
            post.cover_image_file = uploaded_cover
        elif cover_url:
            # Selecting a URL explicitly replaces any previously uploaded file.
            if post.cover_image_file:
                post.cover_image_file.delete(save=False)
            post.cover_image_file = None
            post.cover_image = resolve_image_url(cover_url)
        post.content      = request.POST.get('content',      post.content).strip()
        post.tags         = request.POST.get('tags',         post.tags).strip()
        post.read_time    = int(request.POST.get('read_time', post.read_time) or post.read_time)
        post.is_featured  = request.POST.get('is_featured') == 'on'
        post.is_published = request.POST.get('is_published') == 'on'
        post.save()
        messages.success(request, f'Post "{post.title}" updated.')
        if post.is_published and not was_published:
            _send_new_blog_post_alerts(post)
        return redirect('/admin/dashboard/?tab=blog')
    return render(request, 'Dashboard/blog_edit.html', {
        'post': post,
        'blog_categories': BlogPost.CATEGORY_CHOICES,
    })


@login_required
def blog_delete(request, post_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    if request.method == 'POST':
        post = BlogPost.objects.filter(pk=post_id).first()
        if post:
            title = post.title
            post.delete()
            messages.success(request, f'Post "{title}" deleted.')
    return redirect('/admin/dashboard/?tab=blog')


@login_required
def video_conferencing(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    room_name = request.GET.get('room', '').strip()
    if not room_name:
        import secrets, time
        room_name = f'SelectRoyalMaids_{int(time.time())}_{secrets.token_hex(3)}'
    jitsi_url = f'https://meet.jit.si/{room_name}'
    return render(request, 'Dashboard/video_conferencing.html', {
        'room_name': room_name,
        'jitsi_url': jitsi_url,
    })


@login_required
def application_view(request, application_id):
    """Display a maid application in document format with print option."""
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    application = get_object_or_404(MaidRegistration, pk=application_id)
    return render(request, 'Dashboard/application_detail.html', {'application': application})


@login_required
@require_POST
def application_decline(request, application_id):
    """Decline a maid application, send email, and delete the record."""
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    application = get_object_or_404(MaidRegistration, pk=application_id)
    reason = request.POST.get('reason', '').strip()
    # Send decline email
    send_maid_application_decline_email(application, reason)
    name = f'{application.first_name} {application.last_name}'
    application.delete()
    messages.success(request, f'Application for {name} has been declined and deleted.')
    return redirect('/admin/dashboard/')


@login_required
@require_POST
def application_upload(request, application_id):
    """Upload a maid application as a profile using the Add Maid fields."""
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    application = get_object_or_404(MaidRegistration, pk=application_id)
    # Create slug from application data
    full_name = f'{application.first_name} {application.last_name}'
    import re
    slug_base = re.sub(r'[^a-z0-9]+', '-', full_name.lower()).strip('-')
    slug = slug_base
    counter = 1
    while MaidProfile.objects.filter(slug=slug).exists():
        slug = f'{slug_base}-{counter}'
        counter += 1
    # Create MaidProfile from application data
    MaidProfile.objects.create(
        slug=slug,
        full_name=full_name,
        address=f'{application.city}, {application.state}',
        age=(timezone.now().year - application.date_of_birth.year) if application.date_of_birth else '',
        phone=application.phone,
        email=application.email,
        description=application.bio,
        image=application.profile_photo if application.profile_photo else None,
        assign_status='unassigned',
        is_featured=False,
        is_active=True,
    )
    name = f'{application.first_name} {application.last_name}'
    application.delete()
    messages.success(request, f'{name} has been uploaded as a maid profile.')
    return redirect('/admin/dashboard/?tab=maids')
