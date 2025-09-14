from django.db import models
from django.contrib.auth.models import User

class CompanyFilter(models.Model):
    EXCHANGE_CHOICES = [
        ('', 'All Exchanges'),
        ('US', 'US Markets'),
        ('NYSE', 'New York Stock Exchange'),
        ('NASDAQ', 'NASDAQ'),
        ('AMEX', 'American Stock Exchange'),
    ]

    SECTOR_CHOICES = [
        ('', 'All Sectors'),
        ('Technology', 'Technology'),
        ('Healthcare', 'Healthcare'),
        ('Financial Services', 'Financial Services'),
        ('Consumer Cyclical', 'Consumer Cyclical'),
        ('Communication Services', 'Communication Services'),
        ('Industrials', 'Industrials'),
        ('Consumer Defensive', 'Consumer Defensive'),
        ('Energy', 'Energy'),
        ('Real Estate', 'Real Estate'),
        ('Materials', 'Materials'),
        ('Utilities', 'Utilities'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="Filter name for your reference")

    # Basic filters
    exchange = models.CharField(max_length=20, choices=EXCHANGE_CHOICES, blank=True, default='')
    sector = models.CharField(max_length=50, choices=SECTOR_CHOICES, blank=True, default='')

    # Market cap filters (in millions)
    min_market_cap = models.BigIntegerField(null=True, blank=True, help_text="Minimum market cap in millions USD")
    max_market_cap = models.BigIntegerField(null=True, blank=True, help_text="Maximum market cap in millions USD")

    # Price filters
    min_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Minimum stock price")
    max_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Maximum stock price")

    # Volume filters
    min_volume = models.BigIntegerField(null=True, blank=True, help_text="Minimum daily volume")

    # Performance filters
    min_pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Minimum P/E ratio")
    max_pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Maximum P/E ratio")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class SavedCompany(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    exchange = models.CharField(max_length=20)
    sector = models.CharField(max_length=50, blank=True)
    market_cap = models.BigIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'symbol']
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.symbol} - {self.name}"
