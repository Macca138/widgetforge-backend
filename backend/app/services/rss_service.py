import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import feedparser
import requests
import email.utils
from diskcache import Cache
from ..services.cache_service import cache

logger = logging.getLogger(__name__)

class RSSService:
    """Service for fetching and parsing RSS feeds with caching"""
    
    def __init__(self):
        self.financial_juice_url = "https://www.financialjuice.com/feed.ashx?xy=rss"
        self.cache_ttl = 300  # 5 minutes cache for frequent updates
        
    def fetch_financial_juice_news(self, max_items: int = 20) -> List[Dict]:
        """
        Fetch Financial Juice news with caching
        
        Args:
            max_items: Maximum number of news items to return
            
        Returns:
            List of news items with parsed data
        """
        cache_key = f"financial_juice_news_{max_items}"
        
        # Try to get from cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            logger.info(f"Fetching Financial Juice RSS feed: {self.financial_juice_url}")
            
            # Fetch RSS feed
            response = requests.get(self.financial_juice_url, timeout=10)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            news_items = []
            for entry in feed.entries[:max_items]:
                news_item = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': self._parse_date(entry.get('published', '')),
                    'published_raw': entry.get('published', ''),
                    'guid': entry.get('guid', ''),
                    'author': entry.get('author', 'FinancialJuice'),
                    'is_high_impact': self._is_high_impact_news(entry.get('title', '')),
                    'time_ago': self._get_time_ago(entry.get('published', ''))
                }
                news_items.append(news_item)
                
            # Cache the results
            cache.set(cache_key, news_items, expire=self.cache_ttl)
            
            logger.info(f"Successfully fetched {len(news_items)} news items")
            return news_items
            
        except requests.RequestException as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
            return []
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date string to datetime object"""
        if not date_str:
            return None
            
        try:
            # Parse RFC 2822 date format using email.utils
            parsed_date = email.utils.parsedate_tz(date_str)
            if parsed_date:
                timestamp = email.utils.mktime_tz(parsed_date)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            
        return None
    
    def _is_high_impact_news(self, title: str) -> bool:
        """
        Determine if news is high impact based on title keywords
        """
        high_impact_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'ppi',
            'gdp', 'employment', 'unemployment', 'nonfarm', 'payroll',
            'central bank', 'ecb', 'boe', 'boj', 'fomc', 'rate decision',
            'earnings', 'crash', 'surge', 'plunge', 'soars', 'tumbles',
            'recession', 'crisis', 'emergency', 'breaking', 'urgent'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in high_impact_keywords)
    
    def _get_time_ago(self, date_str: str) -> str:
        """Get human-readable time ago string"""
        parsed_date = self._parse_date(date_str)
        if not parsed_date:
            return "Unknown"
            
        now = datetime.now(timezone.utc)
        diff = now - parsed_date
        
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"

    def cross_reference_with_calendar(self, news_items: List[Dict], calendar_events: List[Dict]) -> List[Dict]:
        """Cross-reference news items with calendar events to find related events"""
        enhanced_news = []
        
        for news_item in news_items:
            enhanced_item = news_item.copy()
            news_title = news_item.get('title', '').lower()
            
            # Look for related economic events
            for event in calendar_events:
                event_title = event.get('title', '').lower()
                event_country = event.get('country', '').lower()
                
                # Check if news matches this event
                if self._is_news_event_match(news_title, event_title, event_country):
                    enhanced_item['related_event'] = {
                        'title': event.get('title', ''),
                        'country': event.get('country', ''),
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', ''),
                        'impact': event.get('impact', '')
                    }
                    break
            
            enhanced_news.append(enhanced_item)
        
        return enhanced_news
    
    def _is_news_event_match(self, news_title: str, event_title: str, event_country: str) -> bool:
        """Check if news item matches an economic calendar event"""
        # Currency/country mappings
        currency_mappings = {
            'usd': ['us', 'usa', 'united states', 'american', 'dollar'],
            'eur': ['eu', 'euro', 'european', 'eurozone'],  
            'gbp': ['uk', 'british', 'britain', 'england', 'pound'],
            'jpy': ['japan', 'japanese', 'yen'],
            'aud': ['australia', 'australian', 'aussie'],
            'cad': ['canada', 'canadian', 'cad'],
            'chf': ['swiss', 'switzerland', 'franc'],
            'nzd': ['new zealand', 'nz', 'kiwi']
        }
        
        # Check if news mentions the country/currency
        country_mentioned = False
        if event_country in currency_mappings:
            country_terms = currency_mappings[event_country]
            if any(term in news_title for term in country_terms):
                country_mentioned = True
        
        if not country_mentioned:
            return False
        
        # Economic indicator matching
        specific_mappings = {
            'employment change': ['employment change', 'jobs'],
            'unemployment rate': ['unemployment rate'],
            'gdp': ['gdp', 'gross domestic product'],
            'inflation': ['inflation', 'cpi', 'consumer price'],
            'interest rate': ['interest rate', 'rate decision'],
            'retail sales': ['retail sales'],
            'manufacturing': ['manufacturing', 'pmi'],
            'trade balance': ['trade balance'],
            'building permits': ['building permits'],
            'housing': ['housing', 'home sales']
        }
        
        # Check for indicator matches
        for indicator, terms in specific_mappings.items():
            if indicator in event_title:
                if any(term in news_title for term in terms):
                    return True
        
        return False

    def _extract_actual_from_news_title(self, title: str) -> Optional[str]:
        """Extract actual result value from news title"""
        try:
            import re
            
            # Look for patterns like "Actual 83.1k", "Actual: 83.1k", "Actual 2.5%"
            actual_patterns = [
                r'actual[:\s]+([^\s\(]+)',  # "Actual 83.1k" or "Actual: 83.1k"
                r'actual[:\s]+([^,\(]+)',   # "Actual 83.1k (Forecast..."
            ]
            
            title_lower = title.lower()
            for pattern in actual_patterns:
                match = re.search(pattern, title_lower)
                if match:
                    actual_value = match.group(1).strip()
                    # Clean up common trailing characters
                    actual_value = actual_value.rstrip('.,;')
                    return actual_value
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract actual from title '{title}': {e}")
            return None

# Global instance
rss_service = RSSService()