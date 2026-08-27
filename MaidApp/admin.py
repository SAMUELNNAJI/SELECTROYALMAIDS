from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from .models import MaidRegistration, MaidProfile, MaidRecommendation, SupportMessage, placement_capacity_error


class MaidProfileAdminForm(forms.ModelForm):
    """Adds inline validation for the maid placement (employer assignment).

    Mirrors MaidProfile.save() so admins get a normal form error instead of
    a server error when a plan's capacity would be exceeded (Standard = 1
    maid, Premium = unlimited).
    """

    class Meta:
        model = MaidProfile
        fields = '__all__'

    def clean(self):
        cleaned = super().clean()
        assign_status = cleaned.get('assign_status')
        employer = cleaned.get('assigned_employer')
        legacy_employer = cleaned.get('assigned_legacy_employer')

        if assign_status == 'unassigned' and (employer or legacy_employer):
            raise ValidationError(
                'This maid is marked Available but an employer is selected. '
                'Set the placement status to Assigned or clear the employer.')

        target = employer or legacy_employer
        if target:
            kind = 'user' if employer else 'legacy'
            error = placement_capacity_error(target, kind, exclude_pk=self.instance.pk)
            if error:
                raise ValidationError(error)
        return cleaned


@admin.register(MaidRegistration)
class MaidRegistrationAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'role', 'city', 'phone', 'created_at')
    list_filter = ('role', 'work_type', 'state')
    search_fields = ('first_name', 'last_name', 'email', 'phone')


def _next_reg_number():
    """Return the next SRM-XXXX reg number based on the highest existing number."""
    existing = (
        MaidProfile.objects
        .filter(reg_number__startswith='SRM-')
        .values_list('reg_number', flat=True)
    )
    max_num = 0
    for rn in existing:
        try:
            num = int(rn.split('-', 1)[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    return f'SRM-{max_num + 1}'


def _next_legacy_id():
    """Return max(legacy_id) + 1 so the unique constraint is always satisfied."""
    from django.db.models import Max
    result = MaidProfile.objects.aggregate(m=Max('legacy_id'))['m']
    return (result or 0) + 1


@admin.register(MaidProfile)
class MaidProfileAdmin(admin.ModelAdmin):
    form = MaidProfileAdminForm
    list_display = ('full_name', 'reg_number', 'age', 'assign_status', 'assigned_employer_label', 'is_featured', 'is_active', 'created_at')
    list_filter = ('assign_status', 'is_featured', 'is_active')
    search_fields = ('full_name', 'reg_number', 'email', 'phone', 'assigned_employer__first_name', 'assigned_employer__last_name', 'assigned_employer__email')
    ordering = ['-created_at']
    prepopulated_fields = {'slug': ('full_name',)}
    readonly_fields = ('reg_number', 'legacy_id')

    # Hide auto-generated fields from the add/edit form
    exclude = ('reg_number', 'legacy_id')

    def save_model(self, request, obj, form, change):
        if not change:  # only on creation
            obj.reg_number = _next_reg_number()
            obj.legacy_id = _next_legacy_id()
        # Auto-generate slug from full_name if not set
        if not obj.slug:
            base_slug = slugify(obj.full_name)
            slug = base_slug
            n = 1
            while MaidProfile.objects.filter(slug=slug).exclude(pk=obj.pk).exists():
                slug = f'{base_slug}-{n}'
                n += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)


@admin.register(MaidRecommendation)
class MaidRecommendationAdmin(admin.ModelAdmin):
    list_display = ('maid', 'employer', 'status', 'recommended_by', 'recommended_at', 'responded_at')
    list_filter = ('status', 'recommended_at')
    search_fields = ('maid__full_name', 'employer__email', 'employer__first_name', 'employer__last_name')
    autocomplete_fields = ('maid', 'employer', 'recommended_by')
    readonly_fields = ('recommended_at', 'responded_at')


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'employer', 'is_read', 'is_resolved', 'created_at')
    list_filter = ('is_read', 'is_resolved', 'created_at')
    search_fields = ('sender__email', 'employer__email', 'body')
