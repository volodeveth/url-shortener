from django.urls import path
from . import views

urlpatterns = [
    # Homepage
    path('', views.home, name='home'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Link management
    path('links/', views.links_list, name='links_list'),
    path('links/create/', views.create_link, name='create_link'),
    path('links/<str:code>/', views.link_detail, name='link_detail'),
    path('links/<str:code>/delete/', views.delete_link, name='delete_link'),

    # Redirect (must be last - catches all short codes)
    path('<str:code>', views.redirect_link, name='redirect_link'),
]
