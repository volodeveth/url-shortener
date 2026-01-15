from django.contrib import admin
from .models import Link, Click


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['short_code', 'original_url_truncated', 'user', 'clicks_count', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['short_code', 'original_url', 'custom_alias']
    readonly_fields = ['clicks_count', 'created_at']

    def original_url_truncated(self, obj):
        return obj.original_url[:50] + '...' if len(obj.original_url) > 50 else obj.original_url
    original_url_truncated.short_description = 'Original URL'


@admin.register(Click)
class ClickAdmin(admin.ModelAdmin):
    list_display = ['link', 'clicked_at', 'device_type', 'browser', 'country']
    list_filter = ['device_type', 'browser', 'os', 'clicked_at']
    search_fields = ['link__short_code', 'ip_address']
    readonly_fields = ['link', 'clicked_at', 'ip_address', 'user_agent']
