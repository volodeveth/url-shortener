from django import forms
from .models import Link


class LinkForm(forms.ModelForm):
    """Form for creating short links"""

    class Meta:
        model = Link
        fields = ['original_url', 'custom_alias', 'title']
        widgets = {
            'original_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'https://example.com/very/long/url/that/needs/shortening',
            }),
            'custom_alias': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'my-custom-link (optional)',
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
                'placeholder': 'Link title (optional)',
            }),
        }

    def clean_custom_alias(self):
        alias = self.cleaned_data.get('custom_alias')
        if alias:
            # Remove spaces and special chars
            alias = alias.strip().lower()
            # Check if already exists
            if Link.objects.filter(custom_alias=alias).exists():
                raise forms.ValidationError('This alias is already taken.')
            # Check length
            if len(alias) < 3:
                raise forms.ValidationError('Alias must be at least 3 characters.')
            if len(alias) > 50:
                raise forms.ValidationError('Alias must be less than 50 characters.')
        return alias


class QuickLinkForm(forms.Form):
    """Quick link form for homepage"""

    url = forms.URLField(
        widget=forms.URLInput(attrs={
            'class': 'flex-1 px-4 py-3 border-2 border-gray-200 rounded-l-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg',
            'placeholder': 'Paste your long URL here...',
        })
    )
