"""
URL Configuration for URL Shortener SaaS
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Main app
    path('', include('shortener.urls')),

    # Accounts (auth)
    path('accounts/', include('accounts.urls')),

    # API
    path('api/', include('api.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
