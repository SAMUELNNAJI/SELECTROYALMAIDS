from django.contrib import admin
from .models import MaidRegistration


@admin.register(MaidRegistration)
class MaidRegistrationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'role', 'city', 'phone', 'created_at')
    list_filter = ('role', 'work_type', 'state')
    search_fields = ('first_name', 'last_name', 'email', 'phone')
