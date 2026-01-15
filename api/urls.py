from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'links', views.LinkViewSet, basename='link')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Custom endpoints
    path('shorten/', views.api_shorten, name='api_shorten'),
    path('me/', views.api_user_stats, name='api_user_stats'),
]
