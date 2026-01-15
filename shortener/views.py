"""
URL Shortener Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseRedirect
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from .models import Link, Click
from .forms import LinkForm, QuickLinkForm


def home(request):
    """Homepage with quick link shortener"""
    if request.method == 'POST':
        form = QuickLinkForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']

            # Create link
            link = Link.objects.create(
                original_url=url,
                user=request.user if request.user.is_authenticated else None
            )

            # Return JSON for AJAX or redirect
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'short_url': request.build_absolute_uri(link.short_url),
                    'short_code': link.short_code,
                })

            messages.success(request, f'Link created: {link.short_url}')
            return redirect('link_detail', code=link.short_code)
    else:
        form = QuickLinkForm()

    # Stats for homepage
    stats = {
        'total_links': Link.objects.count(),
        'total_clicks': Click.objects.count(),
    }

    return render(request, 'shortener/home.html', {
        'form': form,
        'stats': stats,
    })


def redirect_link(request, code):
    """Redirect short URL to original URL"""
    # Try custom alias first, then short code
    link = Link.objects.filter(custom_alias=code).first()
    if not link:
        link = get_object_or_404(Link, short_code=code)

    # Check if active and not expired
    if not link.is_active:
        return render(request, 'shortener/link_inactive.html', {'link': link})

    if link.is_expired:
        return render(request, 'shortener/link_expired.html', {'link': link})

    # Record click
    Click.record_click(link, request)

    # Redirect
    return HttpResponseRedirect(link.original_url)


@login_required
def dashboard(request):
    """User dashboard with links and stats"""
    user = request.user
    links = user.links.all()[:10]  # Latest 10 links

    # Calculate stats
    total_links = user.links.count()
    total_clicks = Click.objects.filter(link__user=user).count()

    # Clicks over last 7 days
    last_week = timezone.now() - timedelta(days=7)
    clicks_by_day = (
        Click.objects
        .filter(link__user=user, clicked_at__gte=last_week)
        .annotate(date=TruncDate('clicked_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    # Top links
    top_links = user.links.order_by('-clicks_count')[:5]

    # Device breakdown
    device_stats = (
        Click.objects
        .filter(link__user=user)
        .values('device_type')
        .annotate(count=Count('id'))
    )

    # Calculate links remaining
    links_limit = user.plan_config['links_limit']
    links_remaining = max(0, links_limit - total_links) if links_limit != -1 else 0

    context = {
        'links': links,
        'total_links': total_links,
        'total_clicks': total_clicks,
        'clicks_by_day': list(clicks_by_day),
        'top_links': top_links,
        'device_stats': list(device_stats),
        'plan_config': user.plan_config,
        'can_create': user.can_create_link(),
        'links_remaining': links_remaining,
    }

    return render(request, 'shortener/dashboard.html', context)


@login_required
def create_link(request):
    """Create new short link"""
    user = request.user

    # Check limit
    if not user.can_create_link():
        messages.error(request, f'You have reached your link limit ({user.links_limit}). Upgrade your plan!')
        return redirect('profile')

    if request.method == 'POST':
        form = LinkForm(request.POST)
        if form.is_valid():
            # Check custom alias permission
            if form.cleaned_data.get('custom_alias') and not user.can_use_custom_alias:
                messages.error(request, 'Custom aliases require Pro or Business plan.')
                return redirect('create_link')

            link = form.save(commit=False)
            link.user = user
            link.save()

            messages.success(request, 'Link created successfully!')
            return redirect('link_detail', code=link.short_code)
    else:
        form = LinkForm()

    return render(request, 'shortener/create_link.html', {
        'form': form,
        'can_use_custom_alias': user.can_use_custom_alias,
    })


@login_required
def link_detail(request, code):
    """Link details and statistics"""
    link = get_object_or_404(Link, short_code=code)

    # Check ownership (allow viewing own links or public stats)
    if link.user and link.user != request.user:
        messages.error(request, 'You do not have permission to view this link.')
        return redirect('dashboard')

    # Get analytics
    last_30_days = timezone.now() - timedelta(days=30)

    clicks_by_day = (
        link.clicks
        .filter(clicked_at__gte=last_30_days)
        .annotate(date=TruncDate('clicked_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    browser_stats = (
        link.clicks
        .values('browser')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    device_stats = (
        link.clicks
        .values('device_type')
        .annotate(count=Count('id'))
    )

    os_stats = (
        link.clicks
        .values('os')
        .annotate(count=Count('id'))
        .order_by('-count')[:5]
    )

    recent_clicks = link.clicks.all()[:20]

    # Generate QR code
    qr_code = link.generate_qr_code()

    context = {
        'link': link,
        'qr_code': qr_code,
        'clicks_by_day': list(clicks_by_day),
        'browser_stats': list(browser_stats),
        'device_stats': list(device_stats),
        'os_stats': list(os_stats),
        'recent_clicks': recent_clicks,
        'full_short_url': request.build_absolute_uri(link.short_url),
    }

    return render(request, 'shortener/link_detail.html', context)


@login_required
def delete_link(request, code):
    """Delete a link"""
    link = get_object_or_404(Link, short_code=code, user=request.user)

    if request.method == 'POST':
        link.delete()
        messages.success(request, 'Link deleted successfully.')
        return redirect('dashboard')

    return render(request, 'shortener/delete_link.html', {'link': link})


@login_required
def links_list(request):
    """All user links with pagination"""
    links = request.user.links.all()

    # Search
    search = request.GET.get('search', '')
    if search:
        links = links.filter(
            Q(original_url__icontains=search) |
            Q(title__icontains=search) |
            Q(short_code__icontains=search)
        )

    return render(request, 'shortener/links_list.html', {
        'links': links,
        'search': search,
    })
