import time
import requests
from datetime import date, datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from insights.models import SP500Company, CompanyMetrics


class Command(BaseCommand):
    help = 'Collect daily metrics for S&P 500 companies with rate limiting (60 calls/minute)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if data already exists for today',
        )
        parser.add_argument(
            '--symbol',
            type=str,
            help='Update specific company symbol only',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=60,
            help='Number of companies to update per minute (default: 60)',
        )

    def handle(self, *args, **options):
        force_update = options['force']
        specific_symbol = options['symbol']
        batch_size = options['batch_size']

        # Get Finnhub API key from settings
        api_key = getattr(settings, 'FINNHUB_API_KEY', None)
        if not api_key:
            self.stdout.write(
                self.style.ERROR('FINNHUB_API_KEY not found in settings')
            )
            return

        # Get companies to update
        if specific_symbol:
            companies = SP500Company.objects.filter(
                symbol=specific_symbol,
                is_active=True
            )
        else:
            companies = SP500Company.objects.filter(is_active=True)

        if not companies.exists():
            self.stdout.write(
                self.style.WARNING('No companies found to update')
            )
            return

        self.stdout.write(f'Found {companies.count()} companies to process')

        # Filter companies that need updates
        companies_to_update = []
        for company in companies:
            if force_update or CompanyMetrics.needs_update_today(company.symbol):
                companies_to_update.append(company)

        if not companies_to_update:
            self.stdout.write(
                self.style.SUCCESS('All companies are already updated for today')
            )
            return

        self.stdout.write(
            f'Updating {len(companies_to_update)} companies that need updates'
        )

        # Process companies with rate limiting
        processed = 0
        start_time = time.time()

        for i, company in enumerate(companies_to_update):
            try:
                # Rate limiting: ensure we don't exceed batch_size per minute
                if i > 0 and i % batch_size == 0:
                    elapsed = time.time() - start_time
                    if elapsed < 60:
                        sleep_time = 60 - elapsed
                        self.stdout.write(
                            f'Rate limiting: sleeping for {sleep_time:.1f} seconds...'
                        )
                        time.sleep(sleep_time)
                    start_time = time.time()

                # Fetch company data
                success = self.fetch_company_data(company, api_key)
                if success:
                    processed += 1
                    self.stdout.write(f'[SUCCESS] Updated {company.symbol}')
                else:
                    self.stdout.write(f'[FAILED] Failed to update {company.symbol}')

                # Small delay between requests
                time.sleep(1)

            except KeyboardInterrupt:
                self.stdout.write('\nInterrupted by user')
                break
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error updating {company.symbol}: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Completed. Successfully updated {processed} out of '
                f'{len(companies_to_update)} companies'
            )
        )

    def fetch_company_data(self, company, api_key):
        """Fetch and save company data from Finnhub API"""
        try:
            # Get quote data
            quote_url = f'https://finnhub.io/api/v1/quote'
            quote_params = {
                'symbol': company.symbol,
                'token': api_key
            }

            quote_response = requests.get(quote_url, params=quote_params, timeout=10)
            quote_response.raise_for_status()
            quote_data = quote_response.json()

            # Get basic financials
            metrics_url = f'https://finnhub.io/api/v1/stock/metric'
            metrics_params = {
                'symbol': company.symbol,
                'metric': 'all',
                'token': api_key
            }

            metrics_response = requests.get(metrics_url, params=metrics_params, timeout=10)
            metrics_response.raise_for_status()
            metrics_data = metrics_response.json()

            # Create or update metrics record
            today = date.today()
            company_metrics, created = CompanyMetrics.objects.get_or_create(
                company=company,
                date=today,
                defaults={}
            )

            # Update quote data
            if 'c' in quote_data:  # current price
                company_metrics.close_price = quote_data['c']
            if 'h' in quote_data:  # high price
                company_metrics.high_price = quote_data['h']
            if 'l' in quote_data:  # low price
                company_metrics.low_price = quote_data['l']
            if 'o' in quote_data:  # open price
                company_metrics.open_price = quote_data['o']
            if 'pc' in quote_data:  # previous close
                company_metrics.previous_close = quote_data['pc']

            # Update metrics data
            if 'metric' in metrics_data:
                metric = metrics_data['metric']

                if 'marketCapitalization' in metric:
                    company_metrics.market_cap = int(metric['marketCapitalization'] * 1000000)  # Convert to actual value
                if 'peBasicExclExtraTTM' in metric:
                    company_metrics.pe_ratio = metric['peBasicExclExtraTTM']
                if 'pbAnnual' in metric:
                    company_metrics.price_to_book = metric['pbAnnual']
                if 'dividendYieldIndicatedAnnual' in metric:
                    company_metrics.dividend_yield = metric['dividendYieldIndicatedAnnual']

            # Get technical indicators (moving averages)
            tech_url = f'https://finnhub.io/api/v1/indicator'
            for period in [20, 50, 100, 200]:
                try:
                    tech_params = {
                        'symbol': company.symbol,
                        'resolution': 'D',
                        'from': int((datetime.now().timestamp() - (period + 10) * 86400)),
                        'to': int(datetime.now().timestamp()),
                        'indicator': 'sma',
                        'timeperiod': period,
                        'token': api_key
                    }

                    tech_response = requests.get(tech_url, params=tech_params, timeout=10)
                    if tech_response.status_code == 200:
                        tech_data = tech_response.json()
                        if 'sma' in tech_data and tech_data['sma']:
                            latest_ma = tech_data['sma'][-1]
                            if period == 20:
                                company_metrics.ma_20 = latest_ma
                            elif period == 50:
                                company_metrics.ma_50 = latest_ma
                            elif period == 100:
                                company_metrics.ma_100 = latest_ma
                            elif period == 200:
                                company_metrics.ma_200 = latest_ma

                    time.sleep(0.2)  # Small delay between technical indicator requests

                except Exception as e:
                    self.stdout.write(f'Warning: Could not fetch {period}-day MA for {company.symbol}: {str(e)}')

            company_metrics.save()
            return True

        except requests.exceptions.RequestException as e:
            self.stdout.write(f'API request failed for {company.symbol}: {str(e)}')
            return False
        except Exception as e:
            self.stdout.write(f'Unexpected error for {company.symbol}: {str(e)}')
            return False