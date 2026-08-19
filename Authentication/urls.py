from django.urls import path
from . import views

app_name = "Authentication"

urlpatterns = [
    path('login/',                                 views.login_view,          name='login'),
    path('signup/',                                views.signup_view,         name='signup'),
    path('logout/',                                views.logout_view,         name='logout'),
    path('employer/dashboard/',                    views.employer_dashboard,  name='employer_dashboard'),
    path('admin/dashboard/',                       views.admin_dashboard,     name='admin_dashboard'),
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
]
