from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
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
    search_query = request.GET.get('q', '').strip()
    posts_qs = BlogPost.objects.filter(is_published=True)
    if category != 'all':
        posts_qs = posts_qs.filter(category=category)
    if search_query:
        posts_qs = posts_qs.filter(title__icontains=search_query) | posts_qs.filter(excerpt__icontains=search_query)

    featured = BlogPost.objects.filter(is_published=True, is_featured=True).first()
    paginator = Paginator(posts_qs.exclude(pk=featured.pk if featured else None), 6)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'selectroyal/blog.html', {
        'featured':   featured,
        'page_obj':   page_obj,
        'active_cat': category,
        'categories': BlogPost.CATEGORY_CHOICES,
        'search_query': search_query,
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
        'page_range':    paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1),
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


@login_required
def request_maid(request):
    """Submit an employer's matching request into their support conversation."""
    if request.method == 'GET':
        return render(request, 'selectroyal/request-maid.html')
    if request.method != 'POST':
        return HttpResponseNotAllowed(['GET', 'POST'])

    request_fields = [
        ('Service', 'service'), ('State', 'state'), ('City / Area', 'city'),
        ('Full Address', 'address'), ('Closest Landmark', 'landmark'),
        ('Work Type', 'worktype'), ('Minimum Experience', 'experience'),
        ('Skills Required', 'skills'), ('Gender Preference', 'gender_preference'),
        ('Monthly Budget', 'budget'), ('Additional Notes', 'notes'),
        ('Preferred Start Date', 'start_date'), ('Urgency', 'urgency'),
        ('Interview Method', 'interview_method'), ('Interview Days', 'interview_days'),
        ('Contact Name', 'contact_name'), ('Contact Phone', 'contact_phone'),
        ('Contact Email', 'contact_email'),
    ]
    from django.utils.html import escape
    table_rows = ''
    for label, key in request_fields:
        value = ' '.join(request.POST.get(key, '').split()) or '—'
        table_rows += (
            f'<tr>'
            f'<td style="padding:6px 10px;border:1px solid #e2e8f0;font-weight:600;'
            f'background:#f8fafc;white-space:nowrap;color:#374151;">{escape(label)}</td>'
            f'<td style="padding:6px 10px;border:1px solid #e2e8f0;color:#1f2937;">{escape(value)}</td>'
            f'</tr>'
        )
    body = (
        '<p style="margin:0 0 8px;font-weight:700;color:#111827;">📋 New employer placement request</p>'
        '<table style="border-collapse:collapse;width:100%;font-size:.85rem;font-family:inherit;">'
        '<thead><tr>'
        '<th style="padding:7px 10px;border:1px solid #e2e8f0;background:#1d4ed8;color:#fff;text-align:left;">Request Detail</th>'
        '<th style="padding:7px 10px;border:1px solid #e2e8f0;background:#1d4ed8;color:#fff;text-align:left;">Information</th>'
        '</tr></thead>'
        f'<tbody>{table_rows}</tbody>'
        '</table>'
    )
    SupportMessage.objects.create(sender=request.user, employer=request.user, body=body)
    return JsonResponse({
        'success': True,
        'chat_url': f"{request.build_absolute_uri('/support-chat/')}",
    }, status=201)


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
    User = get_user_model()
    employers = User.objects.filter(is_active=True, is_staff=False).order_by('first_name', 'last_name', 'username')

    if request.user.is_staff:
        selected_id = request.GET.get('employer')
        chat_employer = employers.filter(pk=selected_id).first() if selected_id else None
    else:
        chat_employer = request.user

    if chat_employer:
        # Mark as read: messages the current viewer did NOT send
        SupportMessage.objects.filter(
            employer=chat_employer,
            is_read=False,
        ).exclude(sender=request.user).update(is_read=True)

    return render(request, 'Dashboard/support-chat.html', {
        'chat_messages': SupportMessage.objects.filter(employer=chat_employer).select_related('sender').order_by('created_at')[:100] if chat_employer else [],
        'chat_employer': chat_employer,
        'employers': employers if request.user.is_staff else [],
        'is_resolved': SupportMessage.objects.filter(employer=chat_employer, is_resolved=True).exists() if chat_employer else False,
    })

@login_required
def support_messages(request):
    """AJAX endpoint for one private employer/support conversation."""
    User = get_user_model()
    if request.user.is_staff:
        employer_id = request.GET.get('employer') or request.POST.get('employer')
        employer = User.objects.filter(pk=employer_id, is_active=True, is_staff=False).first()
        if employer is None:
            return JsonResponse({'error': 'Choose an employer conversation first.'}, status=400)
    else:
        employer = request.user

    if request.method == 'GET':
        after_id = request.GET.get('after', '').strip()
        records = SupportMessage.objects.filter(employer=employer).select_related('sender').order_by('created_at')
        if after_id.isdigit():
            records = records.filter(pk__gt=int(after_id))
        records = records[:100]
        return JsonResponse({'messages': [_support_message_data(item, request.user) for item in records]})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Your message cannot be empty.'}, status=400)
    if len(body) > 2000:
        return JsonResponse({'error': 'Messages are limited to 2,000 characters.'}, status=400)

    message = SupportMessage.objects.create(sender=request.user, employer=employer, body=body)
    return JsonResponse({'message': _support_message_data(message, request.user)}, status=201)


def _support_message_data(message, viewer):
    sender_name = message.sender.get_full_name() or message.sender.username
    initials = ''.join(part[0] for part in sender_name.split()[:2]).upper() or 'SR'
    return {
        'id': message.pk,
        'sender': sender_name,
        'initials': initials,
        'body': message.body,
        'time': message.created_at.strftime('%H:%M'),
        'outgoing': message.sender_id == viewer.id,
    }


@login_required
def resolve_conversation(request):
    """Toggle resolved status for an entire employer conversation (POST only)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    User = get_user_model()
    if request.user.is_staff:
        employer_id = request.POST.get('employer')
        employer = User.objects.filter(pk=employer_id, is_active=True, is_staff=False).first()
        if employer is None:
            return JsonResponse({'error': 'Employer not found.'}, status=400)
    else:
        employer = request.user

    # Determine new state from request or toggle from current state
    action = request.POST.get('action', 'toggle')  # 'resolve' | 'reopen' | 'toggle'
    msgs = SupportMessage.objects.filter(employer=employer)
    if not msgs.exists():
        return JsonResponse({'error': 'No messages found for this conversation.'}, status=404)

    currently_resolved = msgs.filter(is_resolved=True).exists()
    if action == 'resolve':
        new_state = True
    elif action == 'reopen':
        new_state = False
    else:  # toggle
        new_state = not currently_resolved

    msgs.update(is_resolved=new_state)
    return JsonResponse({'resolved': new_state})


@login_required
def conversation_list(request):
    """AJAX endpoint — returns all employer conversations with metadata for the chat list panel."""
    if not request.user.is_staff:
        # Employers only see their own conversation
        employer = request.user
        last_msg = SupportMessage.objects.filter(employer=employer).order_by('-created_at').first()
        unread = SupportMessage.objects.filter(employer=employer, is_read=False).exclude(sender=employer).count()
        resolved = SupportMessage.objects.filter(employer=employer, is_resolved=True).exists()
        conversations = [{
            'employer_id': employer.pk,
            'name': employer.get_full_name() or employer.username,
            'initials': (employer.first_name[:1] + employer.last_name[:1]).upper() or employer.username[:2].upper(),
            'last_message': last_msg.body[:60] if last_msg else '',
            'last_time': last_msg.created_at.strftime('%H:%M') if last_msg else '',
            'unread': unread,
            'resolved': resolved,
        }]
        return JsonResponse({'conversations': conversations})

    # Admin sees all employer conversations
    User = get_user_model()
    employers = User.objects.filter(is_active=True, is_staff=False)
    conversations = []
    for emp in employers:
        last_msg = SupportMessage.objects.filter(employer=emp).order_by('-created_at').first()
        if last_msg is None:
            continue  # skip employers with no messages
        unread = SupportMessage.objects.filter(employer=emp, is_read=False, sender__is_staff=False).count()
        resolved = SupportMessage.objects.filter(employer=emp, is_resolved=True).exists()
        conversations.append({
            'employer_id': emp.pk,
            'name': emp.get_full_name() or emp.username,
            'initials': (emp.first_name[:1] + emp.last_name[:1]).upper() or emp.username[:2].upper(),
            'last_message': last_msg.body[:60],
            'last_time': last_msg.created_at.strftime('%H:%M'),
            'unread': unread,
            'resolved': resolved,
        })
    # Most recently active first
    conversations.sort(key=lambda c: c['last_time'], reverse=True)
    return JsonResponse({'conversations': conversations})


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
    whatsapp_url = ''
    if slug:
        maid = get_object_or_404(MaidProfile, slug=slug, is_active=True)
        similar_maids = list(
            MaidProfile.objects.filter(is_active=True)
            .exclude(pk=maid.pk)
            .order_by('?')[:3]
        )
        profile_url = request.build_absolute_uri(
            f"{request.path}?slug={maid.slug}"
        )
        wa_message = (
            f"Hello SelectRoyalMaids, I want to hire this maid:\n"
            f"Name: {maid.full_name.strip()}\n"
            f"Reg Number: {maid.reg_number}\n"
            f"Profile: {profile_url}"
        )
        wa_interview_message = (
            f"Hello SelectRoyalMaids, I want to interview this maid:\n"
            f"Name: {maid.full_name.strip()}\n"
            f"Reg Number: {maid.reg_number}\n"
            f"Profile: {profile_url}"
        )
        import urllib.parse
        whatsapp_url = f"https://wa.me/2349137894958?text={urllib.parse.quote(wa_message)}"
        whatsapp_interview_url = f"https://wa.me/2349137894958?text={urllib.parse.quote(wa_interview_message)}"
    return render(request, 'selectroyal/view-profile.html', {
        'maid': maid,
        'similar_maids': similar_maids,
        'whatsapp_url': whatsapp_url,
        'whatsapp_interview_url': whatsapp_interview_url,
    })
