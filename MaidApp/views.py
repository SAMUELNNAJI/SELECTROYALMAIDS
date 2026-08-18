from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .models import BlogPost, FAQ, MaidRegistration, Service, SupportMessage


def index(request):
    return render(request, 'selectroyal/index.html')


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
    # increment view count
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
    return render(request, 'selectroyal/find-a-maid.html')


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
    return render(request, 'selectroyal/view-profile.html')
