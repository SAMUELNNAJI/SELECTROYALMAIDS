from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from MaidApp.models import BlogPost, FAQ, MaidProfile, MaidRegistration, PlacementRequest, Service, SupportMessage
from .models import EmployerProfile


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
        from django.http import JsonResponse
        from django.urls import reverse

        first_name       = request.POST.get('firstName', '').strip()
        last_name        = request.POST.get('lastName', '').strip()
        email            = request.POST.get('email', '').strip()
        password         = request.POST.get('password', '')
        confirm_password = request.POST.get('confirmPassword', '')
        phone            = request.POST.get('phone', '').strip()
        city             = request.POST.get('city', '').strip()
        plan_raw         = request.POST.get('plan', 'standard').strip()
        plan             = plan_raw if plan_raw in ('standard', 'premium') else 'standard'

        # Validate all required fields
        if not first_name:
            return JsonResponse({'ok': False, 'error': 'Please enter your first name.'})
        if not last_name:
            return JsonResponse({'ok': False, 'error': 'Please enter your last name.'})
        if not email:
            return JsonResponse({'ok': False, 'error': 'Please enter your email address.'})
        if not password:
            return JsonResponse({'ok': False, 'error': 'Please enter a password.'})
        if len(password) < 8:
            return JsonResponse({'ok': False, 'error': 'Password must be at least 8 characters.'})
        if password != confirm_password:
            return JsonResponse({'ok': False, 'error': 'Passwords do not match.'})
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'ok': False, 'error': 'An account with this email already exists.'})

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

        EmployerProfile.objects.create(
            user=user,
            phone=phone,
            city=city,
            service_needed=request.POST.get('service', '').strip(),
            how_heard=request.POST.get('howHeard', '').strip(),
            plan=plan,
        )

        login(request, user)
        return JsonResponse({'ok': True, 'redirect': reverse('Authentication:employer_dashboard')})

    return render(request, 'Authentication/signup.html')


def logout_view(request):
    logout(request)
    return redirect('MaidApp:index')


# ── Dashboards ────────────────────────────────────────────────────────────────

@login_required
def employer_dashboard(request):
    from django.utils.html import strip_tags
    import re

    # Unread support messages
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

    # Employer profile
    try:
        profile = request.user.employer_profile
    except Exception:
        profile = None

    return render(request, 'Dashboard/Employer.html', {
        'unread_count':    unread_count,
        'recent_requests': recent_requests,
        'profile':         profile,
        'total_requests':  total_requests,
        'maids_available': maids_available,
    })


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
        'maid_count':            MaidRegistration.objects.count(),
        'employer_count':        User.objects.filter(is_superuser=False, is_active=True).count(),
        'support_count':         SupportMessage.objects.count(),
        # unread badge — messages sent by employers (non-staff) that admin hasn't read
        'unread_count':          SupportMessage.objects.filter(
                                     is_read=False,
                                     sender__is_staff=False,
                                 ).count(),
        # maids tab
        'maid_query':            maid_query,
        'recent_maids':          MaidRegistration.objects.order_by('-created_at')[:5],
        'all_maids':             maids_qs,
        # content tabs
        'faqs':                  FAQ.objects.all(),
        'services':              Service.objects.all(),
        'service_icon_choices':  Service.ICON_CHOICES,
        'service_badge_choices': Service.BADGE_CHOICES,
        'placements':            PlacementRequest.objects.select_related('employer', 'candidate').all()[:50],
        'page_obj':           Paginator(BlogPost.objects.all(), 20).get_page(request.GET.get('page', 1)),
        'page_range':         Paginator(BlogPost.objects.all(), 20).get_elided_page_range(request.GET.get('page', 1) or 1, on_each_side=2, on_ends=1),
        'blog_categories':    BlogPost.CATEGORY_CHOICES,
    }
    return render(request, 'Dashboard/Admin.html', context)


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
                cover_image_file=request.FILES.get('cover_image_file'),
                content=request.POST.get('content', '').strip(),
                tags=request.POST.get('tags', '').strip(),
                read_time=int(request.POST.get('read_time', 5) or 5),
                is_featured=request.POST.get('is_featured') == 'on',
                is_published=request.POST.get('is_published') == 'on',
                published_at=timezone.now(),
            )
            messages.success(request, f'Post "{title}" published.')
            return redirect('/admin/dashboard/?tab=blog')
        else:
            messages.error(request, 'Slug and title are required.')
    return render(request, 'Dashboard/blog_create.html')


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
        cover_url = request.POST.get('cover_image', '').strip()
        uploaded_cover = request.FILES.get('cover_image_file')
        if uploaded_cover:
            post.cover_image_file = uploaded_cover
        elif cover_url:
            # Selecting a URL explicitly replaces any previously uploaded file.
            if post.cover_image_file:
                post.cover_image_file.delete(save=False)
            post.cover_image_file = None
            post.cover_image = cover_url
        post.content      = request.POST.get('content',      post.content).strip()
        post.tags         = request.POST.get('tags',         post.tags).strip()
        post.read_time    = int(request.POST.get('read_time', post.read_time) or post.read_time)
        post.is_featured  = request.POST.get('is_featured') == 'on'
        post.is_published = request.POST.get('is_published') == 'on'
        post.save()
        messages.success(request, f'Post "{post.title}" updated.')
        return redirect('/admin/dashboard/?tab=blog')
    return render(request, 'Dashboard/blog_edit.html', {'post': post})


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
