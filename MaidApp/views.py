from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import BlogPost, BlogSubscriber, FAQ, MaidProfile, MaidRegistration, PlacementRequest, Service, SupportMessage
from .emails import send_unread_support_email, send_request_form_email, send_employer_action_email, send_blog_alert_email, send_blog_subscribe_email, send_contact_email


def _pdf_escape(value):
    """Return text that is safe for the built-in PDF Helvetica font."""
    import unicodedata
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode('ascii')
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _maid_application_pdf(application):
    """Build a compact, dependency-free PDF containing the complete application."""
    rows = [
        ('Application ID', application.pk),
        ('Submitted', application.created_at.strftime('%d %B %Y, %H:%M')),
        ('Full name', f'{application.first_name} {application.last_name}'),
        ('Email', application.email), ('Phone', application.phone),
        ('Date of birth', application.date_of_birth.strftime('%d %B %Y')),
        ('Gender', application.gender), ('State', application.state),
        ('City / area', application.city), ('Role', application.get_role_display()),
        ('Work type', application.get_work_type_display()),
        ('Years of experience', application.years_experience),
        ('Availability', application.availability), ('Expected salary', application.expected_salary),
        ('Languages', application.languages), ('Skills', application.skills),
        ('About applicant', application.bio), ('NIN', application.nin),
        ('Reference name', application.reference_name),
        ('Reference phone', application.reference_phone),
    ]
    lines = ['SELECTROYAL MAIDS - MAID APPLICATION', '']
    for label, value in rows:
        text = f'{label}: {value}'
        while len(text) > 92:
            cut = text.rfind(' ', 0, 92) or 92
            lines.append(text[:cut])
            text = '    ' + text[cut:].lstrip()
        lines.append(text)

    page_lines = 46
    chunks = [lines[index:index + page_lines] for index in range(0, len(lines), page_lines)]
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', None]
    page_ids, content_ids = [], []
    for _ in chunks:
        page_ids.append(len(objects) + 1)
        objects.append(None)
        content_ids.append(len(objects) + 1)
        objects.append(None)
    objects[1] = f'<< /Type /Pages /Kids [{" ".join(f"{item} 0 R" for item in page_ids)}] /Count {len(page_ids)} >>'
    for index, chunk in enumerate(chunks):
        content = ['BT', '/F1 11 Tf', '50 790 Td', '14 TL']
        content.extend(f'({_pdf_escape(line)}) Tj T*' for line in chunk)
        content.append('ET')
        stream = '\n'.join(content).encode('latin-1')
        objects[page_ids[index] - 1] = f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /Contents {content_ids[index]} 0 R >>'
        objects[content_ids[index] - 1] = b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream'

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f'{number} 0 obj\n'.encode())
        pdf.extend(obj if isinstance(obj, bytes) else obj.encode())
        pdf.extend(b'\nendobj\n')
    startxref = len(pdf)
    pdf.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    pdf.extend(b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:]))
    pdf.extend(f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF'.encode())
    return bytes(pdf)


def _send_maid_application_to_whatsapp(application):
    """Upload the PDF to Meta and send it to the team WhatsApp number."""
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return False

    import json
    import uuid
    from urllib.request import Request, urlopen

    boundary = f'----SelectRoyal{uuid.uuid4().hex}'
    filename = f'maid-application-{application.pk}.pdf'
    pdf = _maid_application_pdf(application)
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        'Content-Type: application/pdf\r\n\r\n'
    ).encode() + pdf + f'\r\n--{boundary}--\r\n'.encode()
    headers = {
        'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}',
        'Content-Type': f'multipart/form-data; boundary={boundary}',
    }
    media_url = f'https://graph.facebook.com/v22.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/media'
    media_request = Request(media_url, data=body, headers=headers, method='POST')
    with urlopen(media_request, timeout=15) as response:
        media_id = json.loads(response.read().decode())['id']

    message = {
        'messaging_product': 'whatsapp',
        'to': settings.WHATSAPP_APPLICATION_RECIPIENT,
        'type': 'document',
        'document': {
            'id': media_id,
            'filename': filename,
            'caption': f'New maid application: {application.first_name} {application.last_name}',
        },
    }
    message_url = f'https://graph.facebook.com/v22.0/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages'
    message_request = Request(
        message_url, data=json.dumps(message).encode(),
        headers={'Authorization': f'Bearer {settings.WHATSAPP_ACCESS_TOKEN}', 'Content-Type': 'application/json'},
        method='POST',
    )
    with urlopen(message_request, timeout=15):
        pass
    return True


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


@require_POST
def contact_submit(request):
    """Receive the contact form via AJAX and forward it to the company inbox."""
    import json

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid request.'}, status=400)

    first_name = data.get('first_name', '').strip()
    last_name  = data.get('last_name',  '').strip()
    email      = data.get('email',      '').strip()
    phone      = data.get('phone',      '').strip()
    city       = data.get('city',       '').strip()
    source     = data.get('source',     '').strip()
    subject    = data.get('subject',    'General Enquiry').strip()
    message    = data.get('message',    '').strip()

    if not first_name:
        return JsonResponse({'error': 'Please enter your first name.'}, status=400)
    if not last_name:
        return JsonResponse({'error': 'Please enter your last name.'}, status=400)
    if not email or '@' not in email:
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)
    if not message:
        return JsonResponse({'error': 'Please enter your message.'}, status=400)

    sent = send_contact_email(first_name, last_name, email, phone, city, source, subject, message)
    if not sent:
        return JsonResponse({'error': 'Unable to send your message right now. Please try again or email us directly.'}, status=502)

    return JsonResponse({'ok': True})


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

    from Authentication.models import EmployerProfile
    profile = EmployerProfile.objects.filter(user=request.user).first()
    plan = profile.plan if profile else 'standard'
    prior_requests = PlacementRequest.objects.filter(employer=request.user).exclude(status='expired')
    if plan == 'premium' and prior_requests.exists():
        return JsonResponse({'error': 'Your Premium subscription is tied to your existing position. Contact support to request a replacement for that same role.'}, status=403)

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
    requires_payment = plan == 'standard' and prior_requests.exists()
    placement = PlacementRequest.objects.create(
        employer=request.user,
        role=request.POST.get('service', '').strip() or 'Unspecified role',
        plan=plan,
        requires_payment=requires_payment,
    )
    SupportMessage.objects.create(sender=request.user, employer=request.user, body=body)
    send_request_form_email(request.user, placement)
    return JsonResponse({
        'success': True,
        'placement_id': placement.pk,
        'requires_payment': requires_payment,
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
        try:
            sent_to_whatsapp = _send_maid_application_to_whatsapp(application)
        except Exception:
            sent_to_whatsapp = False
        if sent_to_whatsapp:
            messages.success(request, 'Your application has been received and sent to our verification team.')
        else:
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

        # Mark as read: any unread messages the current viewer did NOT send
        SupportMessage.objects.filter(
            employer=employer,
            is_read=False,
        ).exclude(sender=request.user).update(is_read=True)

        return JsonResponse({'messages': [_support_message_data(item, request.user) for item in records]})

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    body = request.POST.get('body', '').strip()
    if not body:
        return JsonResponse({'error': 'Your message cannot be empty.'}, status=400)
    if len(body) > 2000:
        return JsonResponse({'error': 'Messages are limited to 2,000 characters.'}, status=400)

    message = SupportMessage.objects.create(sender=request.user, employer=employer, body=body)
    if request.user.is_staff:
        unread_count = SupportMessage.objects.filter(
            employer=employer,
            is_read=False,
        ).exclude(sender=employer).count()
        send_unread_support_email(employer, unread_count=unread_count)
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


@require_POST
def employer_action_email(request):
    from django.middleware.csrf import get_token
    import json

    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    action = data.get('action', '').strip()
    maid_slug = data.get('maid_slug', '').strip()
    maid = None
    if maid_slug:
        maid = MaidProfile.objects.filter(slug=maid_slug, is_active=True).first()

    if not action:
        return JsonResponse({'error': 'Action is required.'}, status=400)

    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required.'}, status=401)

    send_employer_action_email(request.user, action, maid=maid)

    return JsonResponse({'ok': True})


@require_POST
def blog_subscribe(request):
    import json
    from django.core.exceptions import ValidationError
    from django.core.validators import validate_email
    try:
        data = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON.'}, status=400)

    email = data.get('email', '').strip().lower()
    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

    subscriber, created = BlogSubscriber.objects.get_or_create(
        email=email,
        defaults={'is_active': True},
    )
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.save(update_fields=['is_active'])

    email_sent = send_blog_subscribe_email(email)
    # The subscription is already saved.  Do not make the visitor repeat it if
    # a mail provider is temporarily unavailable; the UI can show an honest
    # delivery warning while staff investigate the email service.
    return JsonResponse({'ok': True, 'subscribed': created, 'email_sent': email_sent})
