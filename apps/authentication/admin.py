from django.contrib import admin
from .models import ActivityLog

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__username', 'description', 'metadata')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
