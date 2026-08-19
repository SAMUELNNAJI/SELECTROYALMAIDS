from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from MaidApp.models import BlogPost, FAQ, MaidProfile, MaidRegistration, Service, SupportMessage


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
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')

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
        login(request, user)
        return redirect('Authentication:employer_dashboard')

    return render(request, 'Authentication/signup.html')


def logout_view(request):
    logout(request)
    return redirect('MaidApp:index')


# ── Dashboards ────────────────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    return render(request, 'Dashboard/Employer.html')


@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')

    maid_query = request.GET.get('mq', '').strip()
    maids_qs   = MaidProfile.objects.filter(is_active=True).order_by('full_name')
    if maid_query:
        maids_qs = maids_qs.filter(full_name__icontains=maid_query) | \
                   maids_qs.filter(reg_number__icontains=maid_query)
        maids_qs = maids_qs.distinct()

    context = {
        # stat cards
        'maid_count':            MaidProfile.objects.filter(is_active=True).count(),
        'employer_count':        User.objects.filter(is_superuser=False, is_active=True).count(),
        'support_count':         SupportMessage.objects.count(),
        # maids tab
        'maid_query':            maid_query,
        'recent_maids':          MaidProfile.objects.filter(is_active=True).order_by('full_name')[:5],
        'all_maids':             maids_qs,
        # content tabs
        'faqs':                  FAQ.objects.all(),
        'services':              Service.objects.all(),
        'service_icon_choices':  Service.ICON_CHOICES,
        'service_badge_choices': Service.BADGE_CHOICES,
        'blog_posts':            BlogPost.objects.all(),
        'blog_categories':       BlogPost.CATEGORY_CHOICES,
    }
    return render(request, 'Dashboard/Admin.html', context)


# ── MaidProfile CRUD ──────────────────────────────────────────────────────────

@login_required
def maid_edit(request, maid_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    maid = get_object_or_404(MaidProfile, pk=maid_id)
    if request.method == 'POST':
        maid.full_name      = request.POST.get('full_name',   maid.full_name).strip()
        maid.reg_number     = request.POST.get('reg_number',  maid.reg_number).strip()
        maid.address        = request.POST.get('address',     maid.address).strip()
        maid.age            = request.POST.get('age',         maid.age).strip()
        maid.phone          = request.POST.get('phone',       maid.phone).strip()
        maid.email          = request.POST.get('email',       maid.email).strip()
        maid.description    = request.POST.get('description', maid.description).strip()
        maid.assign_status  = request.POST.get('assign_status', maid.assign_status)
        maid.is_featured    = request.POST.get('is_featured') == 'on'
        maid.is_active      = request.POST.get('is_active')  == 'on'
        if request.FILES.get('profile_image'):
            maid.image = request.FILES['profile_image']
        maid.save()
        messages.success(request, f'Profile "{maid.full_name}" updated.')
    page = request.POST.get('page', 1)
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
        reg_number = request.POST.get('reg_number', '').strip()
        if full_name and reg_number:
            import re
            slug_base = re.sub(r'[^a-z0-9]+', '-', full_name.lower()).strip('-')
            slug = slug_base
            counter = 1
            while MaidProfile.objects.filter(slug=slug).exists():
                slug = f'{slug_base}-{counter}'
                counter += 1
            MaidProfile.objects.create(
                legacy_id=MaidProfile.objects.order_by('-legacy_id').values_list('legacy_id', flat=True).first() + 1,
                reg_number=reg_number,
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
            messages.success(request, f'Maid "{full_name}" added.')
        else:
            messages.error(request, 'Full name and registration number are required.')
    return redirect('/admin/dashboard/?tab=maids')

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
                slug=slug, title=title,
                badge_label=request.POST.get('badge_label', '').strip(),
                badge_color=request.POST.get('badge_color', 'blue'),
                icon=request.POST.get('icon', 'fa-star'),
                description=desc, features=feats,
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
            BlogPost.objects.create(
                slug=slug, title=title,
                excerpt=request.POST.get('excerpt', '').strip(),
                category=request.POST.get('category', 'general'),
                author_name='SelectRoyal Maids Admin',
                cover_image=request.POST.get('cover_image', '').strip(),
                content=request.POST.get('content', '').strip(),
                tags=request.POST.get('tags', '').strip(),
                read_time=int(request.POST.get('read_time', 5) or 5),
                is_featured=request.POST.get('is_featured') == 'on',
                is_published=request.POST.get('is_published') == 'on',
                published_at=timezone.now(),
            )
            messages.success(request, f'Post "{title}" published.')
        else:
            messages.error(request, 'Slug and title are required.')
    return redirect('/admin/dashboard/?tab=blog')


@login_required
def blog_edit(request, post_id):
    if not request.user.is_superuser:
        return redirect('Authentication:employer_dashboard')
    post = get_object_or_404(BlogPost, pk=post_id)
    if request.method == 'POST':
        post.slug         = request.POST.get('slug',         post.slug).strip()
        post.title        = request.POST.get('title',        post.title).strip()
        post.excerpt      = request.POST.get('excerpt',      post.excerpt).strip()
        post.category     = request.POST.get('category',     post.category)
        post.author_name  = 'SelectRoyal Maids Admin'
        post.cover_image  = request.POST.get('cover_image',  post.cover_image).strip()
        post.content      = request.POST.get('content',      post.content).strip()
        post.tags         = request.POST.get('tags',         post.tags).strip()
        post.read_time    = int(request.POST.get('read_time', post.read_time) or post.read_time)
        post.is_featured  = request.POST.get('is_featured') == 'on'
        post.is_published = request.POST.get('is_published') == 'on'
        post.save()
        messages.success(request, f'Post "{post.title}" updated.')
    return redirect('/admin/dashboard/?tab=blog')


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
