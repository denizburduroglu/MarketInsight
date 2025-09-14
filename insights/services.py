import finnhub
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class FinnhubService:
    def __init__(self):
        self.api_key = getattr(settings, 'FINNHUB_API_KEY', '')
        if not self.api_key:
            logger.warning("FINNHUB_API_KEY not set in settings")
        self.client = finnhub.Client(api_key=self.api_key)

    def get_stock_symbols(self, exchange='US'):
        """Get list of stock symbols from a specific exchange"""
        try:
            symbols = self.client.stock_symbols(exchange)
            return symbols
        except Exception as e:
            logger.error(f"Error fetching stock symbols: {e}")
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
        """Filter companies based on the given criteria"""
        try:
            # Get symbols from the specified exchange
            exchange = filter_obj.exchange if filter_obj.exchange else 'US'
            symbols = self.get_stock_symbols(exchange)

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
                    # Get company profile
                    profile = self.get_company_profile(symbol)
                    if not profile:
                        continue

                    # Get current quote
                    quote = self.get_quote(symbol)
                    if not quote:
                        continue

                    # Get basic financials
                    financials = self.get_basic_financials(symbol)

                    # Apply filters
                    if not self._passes_filters(profile, quote, financials, filter_obj):
                        continue

                    # Format company data
                    company_data = {
                        'symbol': symbol,
                        'name': profile.get('name', ''),
                        'exchange': profile.get('exchange', ''),
                        'sector': profile.get('finnhubIndustry', ''),
                        'market_cap': profile.get('marketCapitalization', 0),
                        'price': quote.get('c', 0),  # current price
                        'change': quote.get('d', 0),  # change
                        'change_percent': quote.get('dp', 0),  # change percent
                        'volume': quote.get('v', 0),  # volume
                        'pe_ratio': financials.get('metric', {}).get('peBasicExclExtraTTM', None),
                        'logo': profile.get('logo', ''),
                        'weburl': profile.get('weburl', ''),
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

    def search_companies(self, query):
        """Search for companies by name or symbol"""
        try:
            results = self.client.symbol_lookup(query)
            return results.get('result', [])
        except Exception as e:
            logger.error(f"Error searching companies: {e}")
            return []