import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import feedparser
import requests
from .cache_service import cache

logger = logging.getLogger(__name__)

class RSSService:
    """Service for fetching and parsing RSS feeds with caching"""
    
    def __init__(self):
        self.financial_juice_url = "https://www.financialjuice.com/feed.ashx?xy=rss"
        self.cache_ttl = 300  # 5 minutes cache for frequent updates
        
    def fetch_financial_juice_news(self, max_items: int = 50) -> List[Dict]:
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
                # Clean the title by removing "FinancialJuice:" prefix
                title = entry.get('title', '')
                if title.startswith('FinancialJuice:'):
                    title = title.replace('FinancialJuice:', '').strip()
                
                news_item = {
                    'title': title,
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': self._parse_date(entry.get('published', '')),
                    'published_raw': entry.get('published', ''),
                    'guid': entry.get('guid', ''),
                    'author': 'Financial Juice',
                    'source': 'Financial Juice',
                    'is_high_impact': self._is_high_impact_news(title),
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
            import email.utils
            parsed_tuple = email.utils.parsedate_tz(date_str)
            if parsed_tuple:
                timestamp = email.utils.mktime_tz(parsed_tuple)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
            
        return None
    
    def _is_high_impact_news(self, title: str) -> bool:
        """
        Determine if news is high impact based on title keywords
        """
        high_impact_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'ppi', 'core cpi', 'core pce',
            'gdp', 'employment', 'unemployment', 'nonfarm', 'non-farm', 'payroll', 'jobless claims',
            'central bank', 'ecb', 'boe', 'boj', 'fomc', 'rate decision', 'fed minutes',
            'retail sales', 'durable goods', 'consumer confidence', 'pmi', 'ism',
            'producer price', 'manufacturing', 'trade balance', 'building permits',
            'earnings', 'crash', 'surge', 'plunge', 'soars', 'tumbles',
            'recession', 'crisis', 'emergency', 'breaking', 'urgent', 'beige book'
        ]
        
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in high_impact_keywords)
    
    def _get_time_ago(self, date_str: str) -> str:
        """Get human-readable time ago string"""
        parsed_date = self._parse_date(date_str)
        if not parsed_date:
            return "Just now"
            
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
    
    def get_recent_high_impact_news(self) -> Optional[Dict]:
        """
        Get the most recent high-impact news item from today for pinned display
        
        Returns:
            Most recent high-impact news item or None
        """
        cache_key = "recent_high_impact_news"
        
        # Try cache first (shorter TTL for pinned news)
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            # Get all news items for today
            news_items = self.fetch_financial_juice_news(max_items=50)
            
            today = datetime.now(timezone.utc).date()
            recent_high_impact = None
            latest_timestamp = 0
            
            for item in news_items:
                # Check if item is high impact
                if item.get('is_high_impact'):
                    # Check if item is from today
                    pub_date = self._parse_date(item.get('pub_date', ''))
                    if pub_date and pub_date.date() == today:
                        timestamp = int(pub_date.timestamp())
                        if timestamp > latest_timestamp:
                            latest_timestamp = timestamp
                            recent_high_impact = item
            
            # Cache for 15 minutes
            if recent_high_impact:
                cache.set(cache_key, recent_high_impact, expire=900)
                
            return recent_high_impact
            
        except Exception as e:
            logger.error(f"Failed to get recent high-impact news: {e}")
            return None
    
    def get_todays_high_impact_summary(self) -> Dict:
        """
        Get summary of today's high-impact news for dashboard display
        
        Returns:
            Summary with count and most recent high-impact item
        """
        cache_key = "todays_high_impact_summary"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            news_items = self.fetch_financial_juice_news(max_items=50)
            
            today = datetime.now(timezone.utc).date()
            todays_high_impact = []
            
            for item in news_items:
                if item.get('is_high_impact'):
                    pub_date = self._parse_date(item.get('pub_date', ''))
                    if pub_date and pub_date.date() == today:
                        todays_high_impact.append(item)
            
            # Sort by publication date (most recent first)
            todays_high_impact.sort(key=lambda x: self._parse_date(x.get('pub_date', '')) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
            
            summary = {
                'count': len(todays_high_impact),
                'most_recent': todays_high_impact[0] if todays_high_impact else None,
                'all_items': todays_high_impact[:5],  # Top 5 for display
                'last_updated': datetime.now().isoformat()
            }
            
            # Cache for 10 minutes
            cache.set(cache_key, summary, expire=600)
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get today's high-impact summary: {e}")
            return {
                'count': 0,
                'most_recent': None,
                'all_items': [],
                'error': str(e)
            }
    
    def cross_reference_with_calendar(self, news_items: List[Dict], calendar_events: List[Dict]) -> List[Dict]:
        """
        Cross-reference news items with calendar events to add actual results
        
        Args:
            news_items: List of news items from RSS
            calendar_events: List of calendar events from Forex Factory
            
        Returns:
            Enhanced news items with calendar event data when matched
        """
        try:
            enhanced_news = []
            
            for news_item in news_items:
                enhanced_item = news_item.copy()
                
                # Try to match news with calendar events
                news_title_lower = news_item['title'].lower()
                
                for event in calendar_events:
                    event_title_lower = event.get('title', '').lower()
                    event_country = event.get('country', '').lower()
                    
                    # Check for keyword matches between news and events
                    if self._is_news_event_match(news_title_lower, event_title_lower, event_country):
                        # Try to extract actual results from news title
                        actual_result = self._extract_actual_from_news_title(news_item['title'])
                        
                        enhanced_item['related_event'] = {
                            'title': event.get('title', ''),
                            'country': event.get('country', ''),
                            'impact': event.get('impact', ''),
                            'forecast': event.get('forecast', ''),
                            'previous': event.get('previous', ''),
                            'time_until': event.get('time_until', ''),
                            'actual': actual_result  # Add extracted actual result
                        }
                        # Mark as high impact if the related event is high impact
                        if event.get('impact', '').lower() == 'high':
                            enhanced_item['is_high_impact'] = True
                        break
                
                enhanced_news.append(enhanced_item)
            
            return enhanced_news
            
        except Exception as e:
            logger.error(f"Failed to cross-reference news with calendar: {e}")
            return news_items
    
    def _is_news_event_match(self, news_title: str, event_title: str, event_country: str) -> bool:
        """
        Determine if a news item matches a calendar event
        
        Args:
            news_title: Lowercase news title
            event_title: Lowercase event title
            event_country: Lowercase country code
            
        Returns:
            True if they likely refer to the same economic event
        """
        # Common economic indicators and their variations
        economic_mappings = {
            'unemployment': ['unemployment', 'jobless', 'employment', 'employment change', 'jobs'],
            'inflation': ['inflation', 'cpi', 'consumer price', 'price index', 'ppi', 'producer price', 'producer price index', 'core cpi', 'core inflation', 'core pce', 'pce index'],
            'gdp': ['gdp', 'gross domestic product', 'economic growth'],
            'interest rate': ['interest rate', 'rate decision', 'fed rate', 'federal rate', 'rate', 'fomc decision', 'fed meeting'],
            'retail sales': ['retail sales', 'consumer spending', 'retail sales ex auto', 'core retail sales'],
            'manufacturing': ['manufacturing', 'factory', 'industrial', 'pmi', 'ism manufacturing', 'manufacturing pmi', 'business confidence', 'manufacturing confidence'],
            'employment': ['employment', 'jobs', 'payroll', 'nonfarm', 'non-farm', 'employment change', 'jobless claims', 'initial claims', 'initial jobless claims', 'weekly claims', 'continuing claims'],
            'trade': ['trade', 'exports', 'imports', 'trade balance'],
            'housing': ['housing', 'home sales', 'mortgage', 'building permits', 'new home sales', 'existing home sales', 'pending home sales'],
            'central bank': ['fed', 'ecb', 'boe', 'boj', 'central bank', 'fomc', 'fed minutes', 'fomc minutes', 'fed speak', 'powell', 'yellen', 'fed chair'],
            'earnings': ['earnings', 'wages', 'income', 'average hourly earnings'],
            'consumer confidence': ['consumer confidence', 'confidence index', 'consumer sentiment', 'university of michigan'],
            'durable goods': ['durable goods', 'durable goods orders', 'capital goods'],
            'services': ['services', 'services pmi', 'ism services', 'composite pmi'],
            'economic surveys': ['beige book', 'tankan', 'zew', 'ifo', 'economic sentiment'],
            'economic data': ['economic', 'data', 'statistics', 'report']
        }
        
        # Check for currency mentions
        currency_codes = ['usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'nzd']
        if event_country in currency_codes and event_country in news_title:
            # Check if they share common economic terms
            for category, terms in economic_mappings.items():
                if any(term in event_title for term in terms) and any(term in news_title for term in terms):
                    return True
        
        # Direct title matching (for exact or very similar titles)
        if event_title and len(event_title) > 10:
            # Remove common words and check similarity
            event_words = set(event_title.split())
            news_words = set(news_title.split())
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            
            event_words = event_words - common_words
            news_words = news_words - common_words
            
            if len(event_words) > 2 and len(news_words) > 2:
                overlap = len(event_words.intersection(news_words))
                if overlap >= 2:  # At least 2 significant words match
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