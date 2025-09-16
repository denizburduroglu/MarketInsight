import time
import requests
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from insights.models import SP500Company, CompanyMetrics
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Worker to fetch S&P 500 company metrics from Finnhub API with enhanced rate limiting'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of companies to process per batch (default: 10)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Delay between API calls in seconds (default: 1.0)',
        )
        parser.add_argument(
            '--max-companies',
            type=int,
            help='Maximum number of companies to process in this run',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if data already exists for today',
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        delay = options['delay']
        max_companies = options['max_companies']
        force_update = options['force']

        # Get Finnhub API key from settings
        api_key = getattr(settings, 'FINNHUB_API_KEY', None)
        if not api_key or api_key == 'demo':
            self.stdout.write(
                self.style.ERROR('FINNHUB_API_KEY not properly configured in settings')
            )
            return

        # Get companies that need updates
        companies = self.get_companies_to_update(force_update, max_companies)

        if not companies:
            self.stdout.write(
                self.style.SUCCESS('All companies are up to date for today')
            )
            return

        total_companies = len(companies)
        self.stdout.write(f'Processing {total_companies} companies in batches of {batch_size}')

        processed = 0
        successful = 0
        failed = 0

        # Process companies in batches
        for i in range(0, total_companies, batch_size):
            batch = companies[i:i + batch_size]
            batch_start_time = time.time()

            self.stdout.write(f'Processing batch {i//batch_size + 1} ({len(batch)} companies)...')

            for company in batch:
                try:
                    if self.fetch_and_save_metrics(company, api_key):
                        successful += 1
                        self.stdout.write(f'[SUCCESS] {company.symbol}')
                    else:
                        failed += 1
                        self.stdout.write(f'[FAILED] {company.symbol}')

                    processed += 1

                    # Add delay between requests
                    time.sleep(delay)

                except KeyboardInterrupt:
                    self.stdout.write('\nInterrupted by user')
                    break
                except Exception as e:
                    failed += 1
                    self.stdout.write(f'[ERROR] {company.symbol}: {str(e)}')

            # Rate limiting: ensure we respect API limits
            batch_elapsed = time.time() - batch_start_time
            min_batch_time = batch_size * delay + 2  # Add buffer

            if batch_elapsed < min_batch_time:
                sleep_time = min_batch_time - batch_elapsed
                self.stdout.write(f'Rate limiting: waiting {sleep_time:.1f}s before next batch')
                time.sleep(sleep_time)

        self.stdout.write(
            self.style.SUCCESS(
                f'Completed! Processed: {processed}, Successful: {successful}, Failed: {failed}'
            )
        )

    def get_companies_to_update(self, force_update, max_companies):
        """Get list of companies that need updates"""
        companies = SP500Company.objects.filter(is_active=True).order_by('symbol')

        if not force_update:
            # Filter companies that need updates today
            companies_to_update = []
            for company in companies:
                if CompanyMetrics.needs_update_today(company.symbol):
                    companies_to_update.append(company)
            companies = companies_to_update
        else:
            companies = list(companies)

        # Limit number of companies if specified
        if max_companies:
            companies = companies[:max_companies]

        return companies

    def fetch_and_save_metrics(self, company, api_key):
        """Fetch metrics for a single company and save to database"""
        try:
            with transaction.atomic():
                # Get or create today's metrics record
                today = date.today()
                metrics, created = CompanyMetrics.objects.get_or_create(
                    company=company,
                    date=today,
                    defaults={}
                )

                # Fetch company profile for sector info
                sector = self.fetch_company_sector(company.symbol, api_key)
                if sector:
                    metrics.sector = sector

                # Fetch real-time quote
                quote_data = self.fetch_quote(company.symbol, api_key)
                if quote_data:
                    self.update_price_data(metrics, quote_data)

                # Fetch basic financials
                financials = self.fetch_financials(company.symbol, api_key)
                if financials:
                    self.update_financial_metrics(metrics, financials)

                # Calculate price changes
                self.calculate_price_changes(metrics, company)

                metrics.save()
                return True

        except Exception as e:
            logger.error(f"Error processing {company.symbol}: {str(e)}")
            return False

    def fetch_company_sector(self, symbol, api_key):
        """Fetch company sector from profile"""
        try:
            url = 'https://finnhub.io/api/v1/stock/profile2'
            params = {'symbol': symbol, 'token': api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            return data.get('finnhubIndustry', '')

        except Exception as e:
            logger.warning(f"Could not fetch sector for {symbol}: {str(e)}")
            return None

    def fetch_quote(self, symbol, api_key):
        """Fetch real-time quote data"""
        try:
            url = 'https://finnhub.io/api/v1/quote'
            params = {'symbol': symbol, 'token': api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {str(e)}")
            return None

    def fetch_financials(self, symbol, api_key):
        """Fetch basic financial metrics"""
        try:
            url = 'https://finnhub.io/api/v1/stock/metric'
            params = {'symbol': symbol, 'metric': 'all', 'token': api_key}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            return response.json()

        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {str(e)}")
            return None

    def update_price_data(self, metrics, quote_data):
        """Update price-related fields from quote data"""
        if 'c' in quote_data:  # current price
            metrics.close_price = Decimal(str(quote_data['c']))
        if 'h' in quote_data:  # high price
            metrics.high_price = Decimal(str(quote_data['h']))
        if 'l' in quote_data:  # low price
            metrics.low_price = Decimal(str(quote_data['l']))
        if 'o' in quote_data:  # open price
            metrics.open_price = Decimal(str(quote_data['o']))
        if 'pc' in quote_data:  # previous close - used for daily change calculation
            previous_close = Decimal(str(quote_data['pc']))
            if metrics.close_price:
                metrics.daily_change = metrics.close_price - previous_close
                if previous_close != 0:
                    metrics.daily_change_percent = (metrics.daily_change / previous_close) * 100

    def update_financial_metrics(self, metrics, financials):
        """Update financial metrics from API data"""
        if 'metric' in financials:
            metric = financials['metric']

            if 'marketCapitalization' in metric and metric['marketCapitalization']:
                # Convert from millions to actual value
                metrics.market_cap = int(metric['marketCapitalization'] * 1_000_000)

            if 'peBasicExclExtraTTM' in metric and metric['peBasicExclExtraTTM']:
                metrics.pe_ratio = Decimal(str(metric['peBasicExclExtraTTM']))

            if 'pbAnnual' in metric and metric['pbAnnual']:
                metrics.price_to_book = Decimal(str(metric['pbAnnual']))

            if 'dividendYieldIndicatedAnnual' in metric and metric['dividendYieldIndicatedAnnual']:
                metrics.dividend_yield = Decimal(str(metric['dividendYieldIndicatedAnnual']))

    def calculate_price_changes(self, metrics, company):
        """Calculate monthly and yearly price changes"""
        if not metrics.close_price:
            return

        try:
            today = date.today()

            # Monthly change (30 days ago)
            month_ago = today - timedelta(days=30)
            monthly_metrics = (company.metrics
                             .filter(date__lte=month_ago, close_price__isnull=False)
                             .order_by('-date')
                             .first())

            if monthly_metrics and monthly_metrics.close_price:
                metrics.monthly_change = metrics.close_price - monthly_metrics.close_price
                if monthly_metrics.close_price != 0:
                    metrics.monthly_change_percent = (metrics.monthly_change / monthly_metrics.close_price) * 100

            # Yearly change (365 days ago)
            year_ago = today - timedelta(days=365)
            yearly_metrics = (company.metrics
                            .filter(date__lte=year_ago, close_price__isnull=False)
                            .order_by('-date')
                            .first())

            if yearly_metrics and yearly_metrics.close_price:
                metrics.yearly_change = metrics.close_price - yearly_metrics.close_price
                if yearly_metrics.close_price != 0:
                    metrics.yearly_change_percent = (metrics.yearly_change / yearly_metrics.close_price) * 100

        except Exception as e:
            logger.warning(f"Could not calculate price changes for {company.symbol}: {str(e)}")