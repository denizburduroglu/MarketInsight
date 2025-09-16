import finnhub
from django.conf import settings
from decimal import Decimal
import logging
from datetime import datetime, timedelta, date
import time
from django.db.models import Max, Min

from .models import SP500Company, CompanyMetrics

logger = logging.getLogger(__name__)

class FinnhubService:
    def __init__(self):
        self.api_key = getattr(settings, 'FINNHUB_API_KEY', '')
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not set in settings")
        self.client = finnhub.Client(api_key=self.api_key)

    def get_stock_symbols(self, exchange='US'):
        """Return S&P 500 companies with latest metrics from the local database.
        The 'exchange' parameter is ignored since we always work with the S&P 500 list.
        Returns a list of dicts with keys compatible with downstream consumers.
        """
        try:
            companies = SP500Company.objects.filter(is_active=True).order_by('symbol')
            results = []
            today = date.today()
            one_year_ago = today - timedelta(days=365)

            for company in companies:
                # Latest metrics for current values
                latest_metrics = (company.metrics
                                  .filter(date__lte=today)
                                  .order_by('-date', '-last_updated')
                                  .first())

                # 52-week high/low from historical metrics if available
                hist_qs = company.metrics.filter(date__gte=one_year_ago)
                agg = hist_qs.aggregate(max_high=Max('high_price'), min_low=Min('low_price')) if hist_qs.exists() else {}
                high_52w = agg.get('max_high')
                low_52w = agg.get('min_low')

                # Current price and other metrics
                price = float(latest_metrics.close_price) if latest_metrics and latest_metrics.close_price is not None else 0.0
                volume = int(latest_metrics.volume) if latest_metrics and latest_metrics.volume is not None else 0
                market_cap_usd = int(latest_metrics.market_cap) if latest_metrics and latest_metrics.market_cap is not None else None
                market_cap_millions = round(market_cap_usd / 1_000_000, 2) if market_cap_usd else None
                pe_ratio = float(latest_metrics.pe_ratio) if latest_metrics and latest_metrics.pe_ratio is not None else None

                # Compute change vs previous close using prior day's close if present
                change = 0.0
                change_percent = 0.0
                if latest_metrics:
                    prev_metrics = (company.metrics
                                    .filter(date__lt=latest_metrics.date)
                                    .order_by('-date', '-last_updated')
                                    .first())
                    if prev_metrics and prev_metrics.close_price is not None and latest_metrics.close_price is not None:
                        try:
                            change = float(latest_metrics.close_price) - float(prev_metrics.close_price)
                            if float(prev_metrics.close_price) != 0:
                                change_percent = (change / float(prev_metrics.close_price)) * 100.0
                        except Exception:
                            pass

                results.append({
                    'symbol': company.symbol,
                    'name': company.name,
                    'exchange': 'S&P 500',
                    'sector': '',  # Sector not available in DB currently
                    'market_cap': market_cap_millions,  # in millions, aligns with UI and filters
                    'price': price,
                    'change': change,
                    'change_percent': change_percent,
                    'volume': volume,
                    'pe_ratio': pe_ratio,
                    'logo': '',
                    'weburl': '',
                    'fifty_two_week_high': float(high_52w) if high_52w is not None else None,
                    'fifty_two_week_low': float(low_52w) if low_52w is not None else None,
                    'ma_20': float(latest_metrics.ma_20) if latest_metrics and latest_metrics.ma_20 is not None else None,
                    'ma_50': float(latest_metrics.ma_50) if latest_metrics and latest_metrics.ma_50 is not None else None,
                    'ma_100': float(latest_metrics.ma_100) if latest_metrics and latest_metrics.ma_100 is not None else None,
                    'ma_200': float(latest_metrics.ma_200) if latest_metrics and latest_metrics.ma_200 is not None else None,
                })

            return results
        except Exception as e:
            logger.error(f"Error fetching stock symbols from DB: {e}")
            return []

    def get_company_profile(self, symbol):
        """Get company profile information"""
        try:
            profile = self.client.company_profile2(symbol=symbol)
            return profile
        except Exception as e:
            logger.error(f"Error fetching company profile for {symbol}: {e}")
            return {}

    def get_quote(self, symbol):
        """Get real-time quote for a symbol"""
        try:
            quote = self.client.quote(symbol)
            return quote
        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return {}

    def get_basic_financials(self, symbol):
        """Get basic financial metrics"""
        try:
            financials = self.client.company_basic_financials(symbol, 'all')
            return financials
        except Exception as e:
            logger.error(f"Error fetching financials for {symbol}: {e}")
            return {}

    def filter_companies(self, filter_obj, limit=50):
        """Filter companies based on the given criteria using local DB data for S&P 500."""
        try:
            # Always use S&P 500 list from DB; ignore exchange filter
            symbols = self.get_stock_symbols()

            if not symbols:
                return []

            filtered_companies = []
            processed = 0

            for symbol_info in symbols:
                if processed >= limit:
                    break

                symbol = symbol_info.get('symbol', '')
                if not symbol:
                    continue

                try:
                    # Build pseudo profile/quote/financials from DB-backed data
                    profile = {
                        'name': symbol_info.get('name', ''),
                        'exchange': symbol_info.get('exchange', 'S&P 500'),
                        'finnhubIndustry': symbol_info.get('sector', ''),
                        'marketCapitalization': symbol_info.get('market_cap', 0) or 0,
                        'logo': symbol_info.get('logo', ''),
                        'weburl': symbol_info.get('weburl', ''),
                    }
                    quote = {
                        'c': symbol_info.get('price', 0) or 0,
                        'd': symbol_info.get('change', 0) or 0,
                        'dp': symbol_info.get('change_percent', 0) or 0,
                        'v': symbol_info.get('volume', 0) or 0,
                    }
                    financials = {
                        'metric': {
                            'peBasicExclExtraTTM': symbol_info.get('pe_ratio', None),
                        }
                    }

                    # Apply filters
                    if not self._passes_filters(profile, quote, financials, filter_obj):
                        continue

                    # Format company data for UI
                    company_data = {
                        'symbol': symbol,
                        'name': profile.get('name', ''),
                        'exchange': profile.get('exchange', 'S&P 500'),
                        'sector': profile.get('finnhubIndustry', ''),
                        'market_cap': profile.get('marketCapitalization', 0),
                        'price': quote.get('c', 0),  # current price
                        'change': quote.get('d', 0),  # change
                        'change_percent': quote.get('dp', 0),  # change percent
                        'volume': quote.get('v', 0),  # volume
                        'pe_ratio': financials.get('metric', {}).get('peBasicExclExtraTTM', None),
                        'logo': profile.get('logo', ''),
                        'weburl': profile.get('weburl', ''),
                        # extra fields that may be useful elsewhere
                        'fifty_two_week_high': symbol_info.get('fifty_two_week_high'),
                        'fifty_two_week_low': symbol_info.get('fifty_two_week_low'),
                        'ma_20': symbol_info.get('ma_20'),
                        'ma_50': symbol_info.get('ma_50'),
                        'ma_100': symbol_info.get('ma_100'),
                        'ma_200': symbol_info.get('ma_200'),
                    }

                    filtered_companies.append(company_data)
                    processed += 1

                except Exception as e:
                    logger.error(f"Error processing symbol {symbol}: {e}")
                    continue

            return filtered_companies

        except Exception as e:
            logger.error(f"Error in filter_companies: {e}")
            return []

    def _passes_filters(self, profile, quote, financials, filter_obj):
        """Check if a company passes all the specified filters"""
        try:
            # Sector filter
            if filter_obj.sector:
                company_sector = profile.get('finnhubIndustry', '').lower()
                if filter_obj.sector.lower() not in company_sector:
                    return False

            # Market cap filters
            market_cap = profile.get('marketCapitalization', 0)
            if filter_obj.min_market_cap and market_cap < filter_obj.min_market_cap:
                return False
            if filter_obj.max_market_cap and market_cap > filter_obj.max_market_cap:
                return False

            # Price filters
            current_price = quote.get('c', 0)
            if filter_obj.min_price and current_price < float(filter_obj.min_price):
                return False
            if filter_obj.max_price and current_price > float(filter_obj.max_price):
                return False

            # Volume filter
            volume = quote.get('v', 0)
            if filter_obj.min_volume and volume < filter_obj.min_volume:
                return False

            # P/E ratio filters
            pe_ratio = financials.get('metric', {}).get('peBasicExclExtraTTM', None)
            if pe_ratio is not None:
                if filter_obj.min_pe_ratio and pe_ratio < float(filter_obj.min_pe_ratio):
                    return False
                if filter_obj.max_pe_ratio and pe_ratio > float(filter_obj.max_pe_ratio):
                    return False

            return True

        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            return False

    def get_moving_average(self, symbol, period=50):
        """Get moving average for a symbol"""
        try:
            # Get historical data for the period
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period + 30)  # Extra days to account for weekends/holidays

            # Convert to Unix timestamps
            start_timestamp = int(start_date.timestamp())
            end_timestamp = int(end_date.timestamp())

            # Get candle data
            candles = self.client.stock_candles(symbol, 'D', start_timestamp, end_timestamp)

            if not candles or candles.get('s') != 'ok':
                return None

            # Calculate moving average from closing prices
            closing_prices = candles.get('c', [])
            if len(closing_prices) < period:
                return None

            # Take the last 'period' closing prices
            recent_prices = closing_prices[-period:]
            moving_average = sum(recent_prices) / len(recent_prices)

            return round(moving_average, 2)

        except Exception as e:
            logger.error(f"Error fetching moving average for {symbol}: {e}")
            return None

    def search_companies(self, query):
        """Search for companies by name or symbol"""
        try:
            results = self.client.symbol_lookup(query)
            return results.get('result', [])
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []