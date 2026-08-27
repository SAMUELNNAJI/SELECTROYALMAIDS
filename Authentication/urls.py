from django.urls import path
from . import views

app_name = "Authentication"

urlpatterns = [
    path('login/',                                 views.login_view,          name='login'),
    path('signup/',                                views.signup_view,         name='signup'),
    path('logout/',                                views.logout_view,         name='logout'),

    # ── Password reset ────────────────────────────────────────────────────────
    path('password-reset/',                        views.password_reset_request,  name='password_reset_request'),
    path('password-reset/<uidb64>/<token>/',       views.password_reset_confirm,  name='password_reset_confirm'),

    # ── Payment flow ──────────────────────────────────────────────────────────
    path('payment/',                               views.payment_page,        name='payment_page'),
    path('payment/redirect/',                      views.payment_redirect,    name='payment_redirect'),
    path('payment/callback/',                      views.payment_callback,    name='payment_callback'),
    path('payment/success/',                       views.payment_success,     name='payment_success'),
    path('payment/failed/',                        views.payment_failed,      name='payment_failed'),

    path('admin/recommend-maids/list/', views.recommend_maids_list, name='recommend_maids_list'),
    path('admin/employer/<int:employer_id>/recommend/', views.recommend_maid, name='recommend_maid'),
    path('admin/recommendation/<int:recommendation_id>/respond/', views.respond_recommendation, name='respond_recommendation'),
    path('employer/dashboard/',                    views.employer_dashboard,  name='employer_dashboard'),
    path('admin/dashboard/',                       views.admin_dashboard,     name='admin_dashboard'),
    path('admin/employers/',                       views.all_employers,       name='all_employers'),
    path('admin/placements/<int:placement_id>/conclude/', views.conclude_placement, name='conclude_placement'),
    path('admin/placements/<int:placement_id>/replace/', views.record_free_replacement, name='record_free_replacement'),
    # MaidProfile CRUD
    path('admin/maid/create/',                     views.maid_create,         name='maid_create'),
    path('admin/maid/<int:maid_id>/edit/',         views.maid_edit,           name='maid_edit'),
    path('admin/maid/<int:maid_id>/delete/',       views.maid_delete,         name='maid_delete'),
    path('admin/maid/<int:maid_id>/toggle/',       views.maid_toggle_status,  name='maid_toggle_status'),
    # FAQ CRUD
    path('admin/faq/create/',                      views.faq_create,          name='faq_create'),
    path('admin/faq/<int:faq_id>/edit/',           views.faq_edit,            name='faq_edit'),
    path('admin/faq/<int:faq_id>/delete/',         views.faq_delete,          name='faq_delete'),
    # Service CRUD
    path('admin/service/create/',                  views.service_create,      name='service_create'),
    path('admin/service/<int:service_id>/edit/',   views.service_edit,        name='service_edit'),
    path('admin/service/<int:service_id>/delete/', views.service_delete,      name='service_delete'),
    # Blog CRUD
    path('admin/blog/create/',                     views.blog_create,         name='blog_create'),
    path('admin/blog/<int:post_id>/edit/',         views.blog_edit,           name='blog_edit'),
    path('admin/blog/<int:post_id>/delete/',       views.blog_delete,         name='blog_delete'),
    path('admin/video-conferencing/',               views.video_conferencing,  name='video_conferencing'),
    path('admin/video-conferencing/',               views.video_conferencing,  name='video_conferencing'),
    # Maid application actions
    path('admin/application/<int:application_id>/view/', views.application_view, name='application_view'),
    path('admin/application/<int:application_id>/decline/', views.application_decline, name='application_decline'),
    path('admin/application/<int:application_id>/upload/', views.application_upload, name='application_upload'),
]
