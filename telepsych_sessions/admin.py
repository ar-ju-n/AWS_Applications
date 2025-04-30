from django.contrib import admin
from .models import Patient, Psychiatrist, Session, SessionReview
from .models_notification import Notification
from django.utils.html import format_html

class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at', 'user')
    search_fields = ('user__email', 'message')
    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} notification(s) marked as read.")
    mark_as_read.short_description = 'Mark selected notifications as read'

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} notification(s) marked as unread.")
    mark_as_unread.short_description = 'Mark selected notifications as unread'

class SessionInline(admin.TabularInline):
    model = Session
    extra = 0
    fields = ('psychiatrist', 'patient', 'scheduled_time', 'status', 'duration')
    readonly_fields = ('scheduled_time', 'status')

class PatientAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'date_of_birth')
    search_fields = ('user__email', 'phone_number')
    list_filter = ('date_of_birth',)
    inlines = [SessionInline]

class PsychiatristAdmin(admin.ModelAdmin):
    list_display = ('user', 'specialization', 'license_number')
    search_fields = ('user__email', 'specialization', 'license_number')
    list_filter = ('specialization',)
    inlines = [SessionInline]

class SessionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'psychiatrist', 'scheduled_time', 'colored_status', 'duration')
    list_filter = ('status', 'scheduled_time', 'psychiatrist__user__email')
    search_fields = ('patient__user__email', 'psychiatrist__user__email', 'notes')
    fieldsets = (
        (None, {'fields': ('patient', 'psychiatrist', 'scheduled_time', 'duration', 'status')}),
        ('Notes', {'fields': ('notes',)}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    ordering = ('-scheduled_time',)
    readonly_fields = ('created_at', 'updated_at')

    def colored_status(self, obj):
        color = {
            'PENDING': 'orange',
            'ACCEPTED': 'green',
            'REJECTED': 'red',
            'COMPLETED': 'blue',
            'CANCELLED': 'gray',
        }.get(obj.status, 'black')
        return format_html('<span style="color: {};"><b>{}</b></span>', color, obj.get_status_display())
    colored_status.short_description = 'Status'

class SessionReviewAdmin(admin.ModelAdmin):
    list_display = ('session', 'patient', 'rating', 'short_feedback', 'created_at')
    search_fields = ('session__id', 'patient__user__email', 'feedback')
    list_filter = ('rating', 'created_at')
    readonly_fields = ('session', 'patient', 'created_at')

    def short_feedback(self, obj):
        return (obj.feedback[:50] + '...') if obj.feedback and len(obj.feedback) > 50 else obj.feedback
    short_feedback.short_description = 'Feedback'

admin.site.register(Patient, PatientAdmin)
admin.site.register(Psychiatrist, PsychiatristAdmin)
admin.site.register(Notification, NotificationAdmin)
admin.site.register(Session, SessionAdmin)
admin.site.register(SessionReview, SessionReviewAdmin)
