from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.shortcuts import render

urlpatterns = [
    path('', include('MaidApp.urls')),
    path('', include('Authentication.urls')),
    path('admin/', admin.site.urls),
    path('summernote/', include('django_summernote.urls')),
]

# Profile photos are stored in MEDIA_ROOT. Django's ``static()`` helper omits
# this route when DEBUG=False, so add the media route explicitly for the
# deployed application as well.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# ── Custom error handlers ─────────────────────────────────────────────────────
def handler400(request, exception=None):
    return render(request, '400.html', status=400)

def handler403(request, exception=None):
    return render(request, '403.html', status=403)

def handler404(request, exception=None):
    return render(request, '404.html', status=404)

def handler500(request):
    return render(request, '500.html', status=500)
