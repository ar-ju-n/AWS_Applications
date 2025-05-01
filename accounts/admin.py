from django.contrib import admin
from .models import CustomUser
from .models_researcher import Researcher

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'role', 'is_active', 'is_staff')
    list_filter = ('role', 'is_active', 'is_staff')
    search_fields = ('email', 'name')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'password1', 'password2'),
        }),
    )

@admin.register(Researcher)
class ResearcherAdmin(admin.ModelAdmin):
    list_display = ('user', 'institution', 'specialization', 'created_at')
    list_filter = ('institution', 'specialization')
    search_fields = ('user__email', 'institution', 'specialization')
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('user',)}),
        ('Research Information', {
            'fields': ('institution', 'specialization', 'research_interests', 'publications')
        }),
    )
