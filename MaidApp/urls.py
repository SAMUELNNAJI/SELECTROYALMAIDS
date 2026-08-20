from django.urls import path
from . import views

app_name = "MaidApp"

urlpatterns = [
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    path('blog/', views.blog, name='blog'),
    path('blog/<slug:slug>/', views.blog_post, name='blog-post'),
    path('contact/', views.contact, name='contact'),
    path('Maids/', views.find_a_maid, name='find-a-maid'),
    path('how-it-works/', views.how_it_works, name='how-it-works'),
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    path('refund-policy/', views.refund_policy, name='refund-policy'),
    path('request-maid/', views.request_maid, name='request-maid'),
    path('apply/', views.register_as_maid, name='apply'),
    path('safety-guidelines/', views.safety_guidelines, name='safety-guidelines'),
    path('services/', views.services, name='services'),
    path('support-chat/', views.support_chat, name='support-chat'),
    path('support-chat/messages/', views.support_messages, name='support-messages'),
    path('support-chat/resolve/', views.resolve_conversation, name='resolve-conversation'),
    path('support-chat/list/', views.conversation_list, name='conversation-list'),
    path('terms-of-service/', views.terms_of_service, name='terms-of-service'),
    path('view-profile/', views.view_profile, name='view-profile'),
]
