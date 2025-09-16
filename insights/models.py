from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

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

    # Moving average filters
    MOVING_AVERAGE_PERIOD_CHOICES = [
        (20, '20-day MA'),
        (50, '50-day MA'),
        (100, '100-day MA'),
        (200, '200-day MA'),
    ]

    enable_moving_average_filter = models.BooleanField(default=False, help_text="Enable moving average filter")
    moving_average_period = models.IntegerField(choices=MOVING_AVERAGE_PERIOD_CHOICES, default=50, help_text="Moving average period in days")
    below_moving_average_only = models.BooleanField(default=True, help_text="Show only stocks below their moving average (value buy indicator)")

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


class SP500Company(models.Model):
    """Model to store S&P 500 companies list"""
    symbol = models.CharField(max_length=10, unique=True, primary_key=True)
    name = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True, help_text="Whether this company is currently in S&P 500")
    added_to_sp500 = models.DateField(null=True, blank=True, help_text="Date when added to S&P 500")
    removed_from_sp500 = models.DateField(null=True, blank=True, help_text="Date when removed from S&P 500")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']
        verbose_name = "S&P 500 Company"
        verbose_name_plural = "S&P 500 Companies"

    def __str__(self):
        return f"{self.symbol} - {self.name}"


class CompanyMetrics(models.Model):
    """Daily metrics for S&P 500 companies"""
    company = models.ForeignKey(SP500Company, on_delete=models.CASCADE, related_name='metrics')
    date = models.DateField(default=date.today)

    # Stock price data
    open_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    high_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    low_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    close_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    volume = models.BigIntegerField(null=True, blank=True)

    # Price changes
    daily_change = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Daily price change")
    daily_change_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, help_text="Daily change percentage")
    monthly_change = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Monthly price change")
    monthly_change_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, help_text="Monthly change percentage")
    yearly_change = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Yearly price change")
    yearly_change_percent = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True, help_text="Yearly change percentage")

    # Company info
    sector = models.CharField(max_length=100, blank=True, help_text="Company sector")

    # Market metrics
    market_cap = models.BigIntegerField(null=True, blank=True, help_text="Market cap in USD")
    pe_ratio = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    price_to_book = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    dividend_yield = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    # Moving averages
    ma_20 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, help_text="20-day moving average")
    ma_50 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, help_text="50-day moving average")
    ma_100 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, help_text="100-day moving average")
    ma_200 = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, help_text="200-day moving average")

    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['company', 'date']
        ordering = ['-date', 'company__symbol']
        indexes = [
            models.Index(fields=['date']),
            models.Index(fields=['last_updated']),
            models.Index(fields=['company', 'date']),
        ]

    def __str__(self):
        return f"{self.company.symbol} - {self.date}"

    @property
    def is_updated_today(self):
        """Check if this record was updated today"""
        return self.last_updated.date() == date.today()

    @classmethod
    def needs_update_today(cls, company_symbol):
        """Check if a company needs update for today"""
        try:
            latest_metric = cls.objects.filter(
                company__symbol=company_symbol,
                date=date.today()
            ).latest('last_updated')
            return not latest_metric.is_updated_today
        except cls.DoesNotExist:
            return True
