"""
URL Shortener Models - Link and Click tracking
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import shortuuid
import qrcode
from io import BytesIO
import base64


class Link(models.Model):
    """Shortened URL model"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='links',
        null=True,
        blank=True  # Allow anonymous links
    )
    original_url = models.URLField(max_length=2048)
    short_code = models.CharField(max_length=20, unique=True, db_index=True)
    custom_alias = models.CharField(max_length=50, unique=True, null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)

    # Stats
    clicks_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Settings
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'links'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.short_code} -> {self.original_url[:50]}"

    def save(self, *args, **kwargs):
        if not self.short_code:
            self.short_code = self.generate_short_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_short_code(length=7):
        """Generate unique short code"""
        return shortuuid.ShortUUID().random(length=length)

    @property
    def short_url(self):
        """Get full short URL"""
        code = self.custom_alias or self.short_code
        return f"/{code}"

    @property
    def is_expired(self):
        """Check if link is expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def increment_clicks(self):
        """Increment click counter"""
        self.clicks_count += 1
        self.save(update_fields=['clicks_count'])

    def generate_qr_code(self, size=200):
        """Generate QR code as base64 string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        # Use full URL for QR code
        full_url = f"https://your-domain.vercel.app{self.short_url}"
        qr.add_data(full_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{img_str}"


class Click(models.Model):
    """Click tracking model"""

    link = models.ForeignKey(
        Link,
        on_delete=models.CASCADE,
        related_name='clicks'
    )
    clicked_at = models.DateTimeField(auto_now_add=True)

    # Analytics data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(max_length=2048, blank=True)

    # Parsed data
    country = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    device_type = models.CharField(max_length=50, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=100, blank=True)
    os = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'clicks'
        ordering = ['-clicked_at']

    def __str__(self):
        return f"Click on {self.link.short_code} at {self.clicked_at}"

    @classmethod
    def record_click(cls, link, request):
        """Record a click with analytics data"""
        # Get IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')

        # Get user agent info
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        referrer = request.META.get('HTTP_REFERER', '')

        # Parse device type (basic)
        device_type = 'desktop'
        ua_lower = user_agent.lower()
        if 'mobile' in ua_lower or 'android' in ua_lower:
            device_type = 'mobile'
        elif 'tablet' in ua_lower or 'ipad' in ua_lower:
            device_type = 'tablet'

        # Parse browser (basic)
        browser = 'Other'
        if 'chrome' in ua_lower:
            browser = 'Chrome'
        elif 'firefox' in ua_lower:
            browser = 'Firefox'
        elif 'safari' in ua_lower:
            browser = 'Safari'
        elif 'edge' in ua_lower:
            browser = 'Edge'

        # Parse OS (basic)
        os_name = 'Other'
        if 'windows' in ua_lower:
            os_name = 'Windows'
        elif 'mac' in ua_lower:
            os_name = 'macOS'
        elif 'linux' in ua_lower:
            os_name = 'Linux'
        elif 'android' in ua_lower:
            os_name = 'Android'
        elif 'iphone' in ua_lower or 'ipad' in ua_lower:
            os_name = 'iOS'

        # Create click record
        click = cls.objects.create(
            link=link,
            ip_address=ip,
            user_agent=user_agent[:500],  # Limit length
            referrer=referrer[:2048] if referrer else '',
            device_type=device_type,
            browser=browser,
            os=os_name,
        )

        # Increment link counter
        link.increment_clicks()

        return click
