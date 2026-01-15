"""
Custom User model with subscription plans
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    """Extended User model with plan support"""

    PLAN_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    ]

    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    plan_expires = models.DateTimeField(null=True, blank=True)
    api_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.username} ({self.plan})"

    @property
    def plan_config(self):
        """Get plan configuration"""
        return settings.PLANS.get(self.plan, settings.PLANS['free'])

    @property
    def links_limit(self):
        """Get links limit for user's plan"""
        return self.plan_config['links_limit']

    @property
    def can_use_custom_alias(self):
        """Check if user can use custom aliases"""
        return self.plan_config['custom_alias']

    @property
    def has_api_access(self):
        """Check if user has API access"""
        return self.plan_config['api_access']

    def can_create_link(self):
        """Check if user can create more links"""
        limit = self.links_limit
        if limit == -1:  # Unlimited
            return True
        current_count = self.links.count()
        return current_count < limit

    def generate_api_key(self):
        """Generate new API key"""
        import secrets
        self.api_key = secrets.token_hex(32)
        self.save()
        return self.api_key
