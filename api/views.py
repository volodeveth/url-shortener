"""
REST API Views
"""
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from shortener.models import Link, Click
from accounts.models import User
from .serializers import (
    LinkSerializer,
    LinkCreateSerializer,
    ClickSerializer,
    LinkStatsSerializer,
)


class APIKeyAuthentication(TokenAuthentication):
    """Custom authentication using API key from header"""

    keyword = 'Bearer'

    def authenticate_credentials(self, key):
        try:
            user = User.objects.get(api_key=key)
            if not user.has_api_access:
                from rest_framework.exceptions import AuthenticationFailed
                raise AuthenticationFailed('API access requires Pro or Business plan.')
            return (user, key)
        except User.DoesNotExist:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Invalid API key.')


class LinkViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing links.

    list: Get all your links
    create: Create a new short link
    retrieve: Get link details
    destroy: Delete a link
    """

    serializer_class = LinkSerializer
    authentication_classes = [APIKeyAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Link.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return LinkCreateSerializer
        return LinkSerializer

    def perform_create(self, serializer):
        user = self.request.user

        # Check limit
        if not user.can_create_link():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(f'Link limit reached ({user.links_limit}). Upgrade your plan.')

        # Check custom alias permission
        if serializer.validated_data.get('custom_alias') and not user.can_use_custom_alias:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Custom aliases require Pro or Business plan.')

        serializer.save(user=user)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get detailed statistics for a link"""
        link = self.get_object()

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Calculate stats
        clicks = link.clicks.all()

        stats = {
            'total_clicks': link.clicks_count,
            'clicks_today': clicks.filter(clicked_at__gte=today).count(),
            'clicks_this_week': clicks.filter(clicked_at__gte=week_ago).count(),
            'clicks_this_month': clicks.filter(clicked_at__gte=month_ago).count(),
            'top_browsers': list(
                clicks.values('browser')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            ),
            'top_devices': list(
                clicks.values('device_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'top_countries': list(
                clicks.values('country')
                .exclude(country='')
                .annotate(count=Count('id'))
                .order_by('-count')[:5]
            ),
            'clicks_by_day': list(
                clicks.filter(clicked_at__gte=month_ago)
                .annotate(date=TruncDate('clicked_at'))
                .values('date')
                .annotate(count=Count('id'))
                .order_by('date')
            ),
        }

        serializer = LinkStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def qr(self, request, pk=None):
        """Get QR code for a link"""
        link = self.get_object()
        qr_code = link.generate_qr_code()

        return Response({
            'short_code': link.short_code,
            'short_url': request.build_absolute_uri(link.short_url),
            'qr_code': qr_code,
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_user_stats(request):
    """Get current user statistics"""
    user = request.user

    total_links = user.links.count()
    total_clicks = Click.objects.filter(link__user=user).count()

    # Clicks over time
    last_30_days = timezone.now() - timedelta(days=30)
    clicks_by_day = (
        Click.objects
        .filter(link__user=user, clicked_at__gte=last_30_days)
        .annotate(date=TruncDate('clicked_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    return Response({
        'username': user.username,
        'plan': user.plan,
        'links_limit': user.links_limit,
        'links_used': total_links,
        'total_clicks': total_clicks,
        'clicks_by_day': list(clicks_by_day),
    })


@api_view(['POST'])
def api_shorten(request):
    """
    Quick API endpoint to shorten URL (works with API key)
    """
    # Check authentication
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if auth_header.startswith('Bearer '):
        api_key = auth_header[7:]
        try:
            user = User.objects.get(api_key=api_key)
            if not user.has_api_access:
                return Response(
                    {'error': 'API access requires Pro or Business plan.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid API key.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    else:
        user = None  # Anonymous link

    # Get URL from request
    url = request.data.get('url')
    custom_alias = request.data.get('alias')
    title = request.data.get('title', '')

    if not url:
        return Response(
            {'error': 'URL is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate custom alias
    if custom_alias:
        if user and not user.can_use_custom_alias:
            return Response(
                {'error': 'Custom aliases require Pro or Business plan.'},
                status=status.HTTP_403_FORBIDDEN
            )
        if Link.objects.filter(custom_alias=custom_alias).exists():
            return Response(
                {'error': 'This alias is already taken.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Check user limit
    if user and not user.can_create_link():
        return Response(
            {'error': f'Link limit reached ({user.links_limit}). Upgrade your plan.'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Create link
    link = Link.objects.create(
        original_url=url,
        custom_alias=custom_alias if custom_alias else None,
        title=title,
        user=user
    )

    return Response({
        'success': True,
        'short_code': link.short_code,
        'short_url': request.build_absolute_uri(link.short_url),
        'original_url': link.original_url,
        'qr_code': link.generate_qr_code(),
    }, status=status.HTTP_201_CREATED)
