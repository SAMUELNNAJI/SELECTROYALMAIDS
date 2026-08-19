import json
import urllib.request

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from MaidApp.models import BlogPost, FAQ, MaidRegistration, Service, SupportMessage
from Authentication.models import EmployerProfile


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
    if request.method == 'POST':
        first_name       = request.POST.get('firstName', '').strip()
        last_name        = request.POST.get('lastName', '').strip()
        email            = request.POST.get('email', '').strip()
        phone            = request.POST.get('phone', '').strip()
        city             = request.POST.get('city', '').strip()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        service          = request.POST.get('service', '').strip()
        how_heard        = request.POST.get('howHeard', '').strip()
        plan             = request.POST.get('plan', 'standard')

        if plan not in ('standard', 'premium'):
            plan = 'standard'

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'Authentication/signup.html')

        if User.objects.filter(username=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'Authentication/signup.html')

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        user.is_staff     = False
        user.is_superuser = False
        user.save()

        profile = EmployerProfile.objects.create(
            user=user,
            phone=phone,
            city=city,
            service_needed=service,
            how_heard=how_heard,
            plan=plan,
            payment_status='pending',
        )

        # ── Initialise Paystack transaction ────────────────────────────────
        amount_kobo  = profile.amount * 100   # Paystack expects kobo
        callback_url = request.build_absolute_uri('/signup/payment/callback/')

        payload = json.dumps({
            'email':        email,
            'amount':       amount_kobo,
            'callback_url': callback_url,
            'metadata': {
                'user_id':    user.pk,
                'plan':       plan,
                'first_name': first_name,
            },
        }).encode('utf-8')

        req = urllib.request.Request(
            settings.PAYSTACK_INIT_URL,
            data=payload,
            headers={
                'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
                'Content-Type':  'application/json',
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if data.get('status') and data['data'].get('authorization_url'):
                login(request, user)
                return redirect(data['data']['authorization_url'])
        except Exception:
            pass

        # Paystack unreachable — log user in, let them pay later from dashboard
        login(request, user)
        messages.warning(
            request,
            'Account created but we could not reach the payment gateway. '
            'Please complete payment from your dashboard.',
        )
        return redirect('Authentication:employer_dashboard')

    return render(request, 'Authentication/signup.html')


def payment_callback_view(request):
    """
    Paystack redirects here after payment with ?reference=<ref>.
    We verify server-side and update the employer profile.
    """
    reference = request.GET.get('reference', '').strip()
    if not reference:
        messages.error(request, 'Invalid payment reference.')
        return redirect('Authentication:employer_dashboard')

    verify_url = f'{settings.PAYSTACK_VERIFY_URL}{reference}'
    req = urllib.request.Request(
        verify_url,
        headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception:
        messages.error(request, 'Could not verify your payment. Please contact support.')
        return redirect('Authentication:employer_dashboard')

    if data.get('status') and data['data'].get('status') == 'success':
        user_id = data['data'].get('metadata', {}).get('user_id')
        try:
            profile = EmployerProfile.objects.get(user_id=user_id)
            profile.payment_status = 'paid'
            profile.payment_ref    = reference
            profile.save()

            # Ensure the user is logged in after Paystack redirect
            if not request.user.is_authenticated:
                login(request, profile.user,
                      backend='django.contrib.auth.backends.ModelBackend')

            messages.success(
                request,
                f'Payment successful! Your {profile.get_plan_display()} plan is now active.',
            )
        except EmployerProfile.DoesNotExist:
            messages.error(request, 'Profile not found after payment. Please contact support.')
    else:
        user_id = data.get('data', {}).get('metadata', {}).get('user_id')
        if user_id:
            EmployerProfile.objects.filter(user_id=user_id).update(payment_status='failed')
        messages.error(request, 'Payment was not completed. Please try again from your dashboard.')

    return redirect('Authentication:employer_dashboard')


def logout_view(request):
    logout(request)
    return redirect('MaidApp:index')


# ── Dashboards ────────────────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    try:
        profile = request.user.employer_profile
    except EmployerProfile.DoesNotExist:
        profile = None
    return render(request, 'Dashboard/Employer.html', {'profile': profile})


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')

    context = {
        'maid_count':            MaidRegistration.objects.count(),
        'employer_count':        User.objects.filter(is_superuser=False, is_active=True).count(),
        'support_count':         SupportMessage.objects.count(),
        'recent_maids':          MaidRegistration.objects.order_by('-created_at')[:5],
        'all_maids':             MaidRegistration.objects.order_by('-created_at'),
        'faqs':                  FAQ.objects.all(),
        'services':              Service.objects.all(),
        'service_icon_choices':  Service.ICON_CHOICES,
        'service_badge_choices': Service.BADGE_CHOICES,
        'blog_posts':            BlogPost.objects.all(),
        'blog_categories':       BlogPost.CATEGORY_CHOICES,
    }
    return render(request, 'Dashboard/Admin.html', context)


# ── FAQ CRUD ──────────────────────────────────────────────────────────────────

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
            Service.objects.create(
                slug=slug,
                title=title,
                badge_label=request.POST.get('badge_label', '').strip(),
                badge_color=request.POST.get('badge_color', 'blue'),
                icon=request.POST.get('icon', 'fa-star'),
                description=desc,
                features=feats,
                image_url=request.POST.get('image_url', '').strip(),
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
        svc.image_url       = request.POST.get('image_url',       svc.image_url).strip()
        svc.available_count = request.POST.get('available_count', svc.available_count).strip()
        svc.avg_rating      = request.POST.get('avg_rating',      svc.avg_rating).strip()
        svc.guarantee_days  = int(request.POST.get('guarantee_days', svc.guarantee_days) or svc.guarantee_days)
        svc.order           = int(request.POST.get('order',       svc.order) or svc.order)
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
            post = BlogPost(
                slug=slug,
                title=title,
                excerpt=request.POST.get('excerpt', '').strip(),
                category=request.POST.get('category', 'general'),
                author_name='Admin',
                author_avatar='',
                author_bio='This article was written and reviewed by the SelectRoyal Maids admin team.',
                content=request.POST.get('content', '').strip(),
                tags=request.POST.get('tags', '').strip(),
                read_time=int(request.POST.get('read_time', 5) or 5),
                is_featured=request.POST.get('is_featured') == 'on',
                is_published=request.POST.get('is_published') == 'on',
                published_at=timezone.now(),
            )
            # Cover image: uploaded file takes priority over URL
            uploaded = request.FILES.get('cover_image_file')
            if uploaded:
                post.cover_image_file = uploaded
                post.cover_image = ''
            else:
                post.cover_image = request.POST.get('cover_image', '').strip()
            post.save()
            messages.success(request, f'Post "{title}" published.')
            return redirect('/admin/dashboard/?tab=blog')
        else:
            messages.error(request, 'Slug and title are required.')
    # GET — render the dedicated editor page
    context = {
        'blog_categories': BlogPost.CATEGORY_CHOICES,
        'default_author':  request.user.get_full_name() or request.user.username,
    }
    return render(request, 'Dashboard/blog_create.html', context)


@login_required
def blog_edit(request, post_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    post = get_object_or_404(BlogPost, pk=post_id)
    if request.method == 'POST':
        post.slug          = request.POST.get('slug',          post.slug).strip()
        post.title         = request.POST.get('title',         post.title).strip()
        post.excerpt       = request.POST.get('excerpt',       post.excerpt).strip()
        post.category      = request.POST.get('category',      post.category)
        post.author_name   = 'Admin'
        post.author_bio    = 'This article was written and reviewed by the SelectRoyal Maids admin team.'
        post.content       = request.POST.get('content',       post.content).strip()
        post.tags          = request.POST.get('tags',          post.tags).strip()
        post.read_time     = int(request.POST.get('read_time', post.read_time) or post.read_time)
        post.is_featured   = request.POST.get('is_featured') == 'on'
        post.is_published  = request.POST.get('is_published') == 'on'
        # Cover image: uploaded file takes priority over URL
        uploaded = request.FILES.get('cover_image_file')
        if uploaded:
            post.cover_image_file = uploaded
            post.cover_image = ''
        else:
            url = request.POST.get('cover_image', '').strip()
            if url:
                post.cover_image = url
                post.cover_image_file = None
        post.save()
        messages.success(request, f'Post "{post.title}" updated.')
        return redirect('/admin/dashboard/?tab=blog')
    # GET — render the dedicated editor page with the post pre-loaded
    context = {
        'post':            post,
        'blog_categories': BlogPost.CATEGORY_CHOICES,
    }
    return render(request, 'Dashboard/blog_edit.html', context)


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
