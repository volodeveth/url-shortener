"""
API Serializers
"""
from rest_framework import serializers
from shortener.models import Link, Click


class LinkSerializer(serializers.ModelSerializer):
    """Serializer for Link model"""

    short_url = serializers.SerializerMethodField()
    qr_code = serializers.SerializerMethodField()

    class Meta:
        model = Link
        fields = [
            'id',
            'original_url',
            'short_code',
            'custom_alias',
            'title',
            'short_url',
            'clicks_count',
            'created_at',
            'is_active',
            'qr_code',
        ]
        read_only_fields = ['id', 'short_code', 'clicks_count', 'created_at']

    def get_short_url(self, obj):
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.short_url)
        return obj.short_url

    def get_qr_code(self, obj):
        return obj.generate_qr_code()


class LinkCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating links via API"""

    class Meta:
        model = Link
        fields = ['original_url', 'custom_alias', 'title']

    def validate_custom_alias(self, value):
        if value:
            value = value.strip().lower()
            if Link.objects.filter(custom_alias=value).exists():
                raise serializers.ValidationError('This alias is already taken.')
            if len(value) < 3:
                raise serializers.ValidationError('Alias must be at least 3 characters.')
        return value


class ClickSerializer(serializers.ModelSerializer):
    """Serializer for Click model"""

    class Meta:
        model = Click
        fields = [
            'id',
            'clicked_at',
            'country',
            'city',
            'device_type',
            'browser',
            'os',
            'referrer',
        ]


class LinkStatsSerializer(serializers.Serializer):
    """Serializer for link statistics"""

    total_clicks = serializers.IntegerField()
    clicks_today = serializers.IntegerField()
    clicks_this_week = serializers.IntegerField()
    clicks_this_month = serializers.IntegerField()
    top_browsers = serializers.ListField()
    top_devices = serializers.ListField()
    top_countries = serializers.ListField()
    clicks_by_day = serializers.ListField()
