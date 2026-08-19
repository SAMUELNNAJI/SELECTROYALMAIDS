from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .models import BlogPost, FAQ, MaidProfile, MaidRegistration, Service, SupportMessage


def index(request):
    # Featured maids for hero carousel (first 3 featured, fallback to first 3)
    hero_maids = list(MaidProfile.objects.filter(is_active=True, is_featured=True)[:3])
    if len(hero_maids) < 3:
        hero_maids += list(
            MaidProfile.objects.filter(is_active=True, is_featured=False)[:3 - len(hero_maids)]
        )

    # Top maids grid — available first, then 8 total
    top_maids = list(MaidProfile.objects.filter(is_active=True, assign_status='unassigned')[:4])
    if len(top_maids) < 4:
        top_maids += list(
            MaidProfile.objects.filter(is_active=True).exclude(
                pk__in=[m.pk for m in top_maids]
            )[:4 - len(top_maids)]
        )

    return render(request, 'selectroyal/index.html', {
        'hero_maids': hero_maids,
        'top_maids':  top_maids,
    })


def about(request):
    return render(request, 'selectroyal/about.html')


def blog(request):
    category = request.GET.get('cat', 'all')
    posts_qs = BlogPost.objects.filter(is_published=True)
    if category != 'all':
        posts_qs = posts_qs.filter(category=category)

    featured = BlogPost.objects.filter(is_published=True, is_featured=True).first()
    paginator = Paginator(posts_qs.exclude(pk=featured.pk if featured else None), 6)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'selectroyal/blog.html', {
        'featured':   featured,
        'page_obj':   page_obj,
        'active_cat': category,
        'categories': BlogPost.CATEGORY_CHOICES,
    })


def blog_post(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    BlogPost.objects.filter(pk=post.pk).update(views=post.views + 1)
    post.views += 1
    related = BlogPost.objects.filter(
        is_published=True, category=post.category
    ).exclude(pk=post.pk)[:3]
    return render(request, 'selectroyal/blog-post.html', {
        'post':    post,
        'related': related,
    })


def contact(request):
    return render(request, 'selectroyal/contact.html')


def find_a_maid(request):
    qs = MaidProfile.objects.filter(is_active=True).order_by('full_name')

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(full_name__icontains=query)

    availability = request.GET.get('avail', '')
    if availability == 'available':
        qs = qs.filter(assign_status='unassigned')
    elif availability == 'assigned':
        qs = qs.filter(assign_status='assigned')

    city = request.GET.get('city', '').strip()
    if city:
        qs = qs.filter(address__icontains=city)

    paginator = Paginator(qs, 24)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'selectroyal/find-a-maid.html', {
        'page_obj':     page_obj,
        'total':        qs.count(),
        'query':        query,
        'city':         city,
        'availability': availability,
        'cities': [
            'Lagos', 'Abuja', 'Port Harcourt', 'Ibadan', 'Kano',
            'Enugu', 'Benin City', 'Warri', 'Owerri', 'Delta',
            'Anambra', 'Rivers', 'Ogun',
        ],
    })


def how_it_works(request):
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'created_at')
    return render(request, 'selectroyal/how-it-works.html', {'faqs': faqs})


def privacy_policy(request):
    return render(request, 'selectroyal/privacy-policy.html')


def refund_policy(request):
    return render(request, 'selectroyal/refund-policy.html')


def request_maid(request):
    return render(request, 'selectroyal/request-maid.html')


def register_as_maid(request):
    if request.method == 'POST':
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'date_of_birth', 'gender',
            'state', 'city', 'role', 'work_type', 'years_experience', 'availability',
            'expected_salary', 'languages', 'skills', 'bio', 'nin', 'reference_name',
            'reference_phone',
        ]
        application = MaidRegistration(**{field: request.POST[field].strip() for field in fields})
        if request.FILES.get('profile_photo'):
            application.profile_photo = request.FILES['profile_photo']
        application.save()
        messages.success(request, 'Your application has been received. Our verification team will contact you shortly.')
        return redirect('MaidApp:apply')
    return render(request, 'selectroyal/register-as-maid.html')


@login_required
def support_chat(request):
    return render(request, 'Dashboard/support-chat.html', {
        'chat_messages': SupportMessage.objects.select_related('sender').order_by('-created_at')[:100],
    })


def safety_guidelines(request):
    return render(request, 'selectroyal/safety-guidelines.html')


def services(request):
    service_list = Service.objects.filter(is_active=True).order_by('order', 'created_at')
    return render(request, 'selectroyal/services.html', {'service_list': service_list})


def terms_of_service(request):
    return render(request, 'selectroyal/terms-of-service.html')


def view_profile(request):
    slug = request.GET.get('slug', '').strip()
    maid = None
    similar_maids = []
    if slug:
        maid = get_object_or_404(MaidProfile, slug=slug, is_active=True)
        # 3 other maids excluding the current one
        similar_maids = list(
            MaidProfile.objects.filter(is_active=True)
            .exclude(pk=maid.pk)
            .order_by('?')[:3]
        )
    return render(request, 'selectroyal/view-profile.html', {
        'maid': maid,
        'similar_maids': similar_maids,
    })
