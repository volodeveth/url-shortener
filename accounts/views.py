from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .forms import SignUpForm, LoginForm


def signup_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


@login_required
def profile_view(request):
    """User profile and settings"""
    user = request.user
    plan_config = user.plan_config

    context = {
        'user': user,
        'plan_config': plan_config,
        'plans': settings.PLANS,
        'links_count': user.links.count(),
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def generate_api_key_view(request):
    """Generate new API key"""
    if request.method == 'POST':
        if request.user.has_api_access:
            api_key = request.user.generate_api_key()
            messages.success(request, f'New API key generated!')
        else:
            messages.error(request, 'API access requires Pro or Business plan.')

    return redirect('profile')
