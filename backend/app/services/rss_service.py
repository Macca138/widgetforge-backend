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
        self.myfxbook_url = "https://www.myfxbook.com/rss/forex-economic-calendar-events"
        
        # Additional RSS sources for better economic data coverage
        self.additional_sources = {
            'MarketWatch': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'Investing.com': 'https://www.investing.com/rss/news_285.rss',
            'ForexLive': 'https://www.forexlive.com/feed/'
        }
        
        self.cache_ttl = 300  # 5 minutes cache for frequent updates
        
    def fetch_financial_juice_news(self, max_items: int = 50) -> List[Dict]:
        """
        Fetch Financial Juice news with caching and archiving
        
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
            
            # Archive economic data releases for longer storage
            self._archive_economic_data_releases(news_items)
            
            logger.info(f"Successfully fetched {len(news_items)} news items")
            return news_items
            
        except requests.RequestException as e:
            logger.error(f"Error fetching RSS feed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
            return []

    def fetch_myfxbook_economic_calendar(self, max_items: int = 50) -> List[Dict]:
        """
        Fetch MyFXBook economic calendar events with caching and archiving
        
        Args:
            max_items: Maximum number of calendar events to return
            
        Returns:
            List of economic calendar events with parsed data
        """
        cache_key = f"myfxbook_economic_calendar_{max_items}"
        
        # Try to get from cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data
            
        try:
            logger.info(f"Fetching MyFXBook economic calendar: {self.myfxbook_url}")
            
            # Fetch RSS feed
            response = requests.get(self.myfxbook_url, timeout=10)
            response.raise_for_status()
            
            # Parse RSS feed
            feed = feedparser.parse(response.content)
            
            calendar_events = []
            for entry in feed.entries[:max_items]:
                # Clean the title
                title = entry.get('title', '')
                
                calendar_event = {
                    'title': title,
                    'link': entry.get('link', ''),
                    'description': entry.get('description', ''),
                    'published': self._parse_date(entry.get('published', '')),
                    'published_raw': entry.get('published', ''),
                    'guid': entry.get('guid', ''),
                    'author': 'MyFXBook',
                    'source': 'MyFXBook Economic Calendar',
                    'is_high_impact': self._is_high_impact_news(title),
                    'time_ago': self._get_time_ago(entry.get('published', '')),
                    'is_economic_data': True  # Mark as economic data
                }
                calendar_events.append(calendar_event)
                
            # Cache the results
            cache.set(cache_key, calendar_events, expire=self.cache_ttl)
            
            # Archive economic data releases for longer storage
            self._archive_economic_data_releases(calendar_events)
            
            logger.info(f"Successfully fetched {len(calendar_events)} MyFXBook calendar events")
            return calendar_events
            
        except requests.RequestException as e:
            logger.error(f"Error fetching MyFXBook RSS feed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing MyFXBook RSS feed: {e}")
            return []

    def fetch_all_economic_news(self, max_items: int = 50) -> List[Dict]:
        """
        Fetch economic news from all sources (Financial Juice + MyFXBook)
        
        Args:
            max_items: Maximum number of items per source
            
        Returns:
            Combined list of news items from all sources
        """
        all_news = []
        
        # Get Financial Juice news
        fj_news = self.fetch_financial_juice_news(max_items)
        all_news.extend(fj_news)
        
        # Get MyFXBook economic calendar
        myfxbook_events = self.fetch_myfxbook_economic_calendar(max_items)
        all_news.extend(myfxbook_events)
        
        # Get from additional sources for better coverage
        additional_news = self.fetch_additional_sources(max_items // 3)
        all_news.extend(additional_news)
        
        # Remove duplicates based on title similarity
        all_news = self._remove_duplicate_news(all_news)
        
        # Sort by publication date (most recent first)
        all_news.sort(key=lambda x: x.get('published') or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        
        return all_news[:max_items]
    
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
            
            # Enhanced patterns to extract actual values from various news title formats
            actual_patterns = [
                # Pattern: "Actual 83.1k" or "Actual: 83.1k"
                r'actual[:\s]+([^\s\(,]+)',
                # Pattern: "2.1% vs 2.0% Expected" or "2.1% vs 2.0% Forecast"
                r'([+-]?\d+\.?\d*%?[kmb]?)\s+vs\s+[+-]?\d+\.?\d*%?[kmb]?\s+(?:expected|forecast|est)',
                # Pattern: "GDP 2.1% (Forecast 2.0%)" or "GDP 2.1% (Est 2.0%)"
                r'([+-]?\d+\.?\d*%?[kmb]?)\s*\((?:forecast|est|expected)[:\s]*[+-]?\d+\.?\d*%?[kmb]?\)',
                # Pattern: "US GDP Growth Rate 2.1%" - extract number before common words
                r'(?:rate|index|sales|change|growth|price|pmi|gdp|cpi|ppi)[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Employment Change 85.2k" - number after indicator
                r'(?:employment|unemployment|retail|manufacturing|trade|building|housing|jobless|consumer|durable|services)[:\s]+(?:change|rate|sales|permits|claims|confidence|goods|pmi)[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "PPI 0.4%" - simple indicator followed by value
                r'(?:ppi|cpi|gdp|pmi)[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Result: 2.1%" or "Result 2.1%"
                r'result[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Comes in at 2.1%"
                r'comes?\s+in\s+at\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Reported 2.1%" or "Reports 2.1%"
                r'reports?\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "rises to 2.1%" or "falls to 2.1%"
                r'(?:rises?|falls?|climbs?|drops?|jumps?)\s+to\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "hits 2.1%" or "reaches 2.1%"
                r'(?:hits?|reaches?)\s+([+-]?\d+\.?\d*%?[kmb]?)',
            ]
            
            title_lower = title.lower()
            for pattern in actual_patterns:
                match = re.search(pattern, title_lower)
                if match:
                    actual_value = match.group(1).strip()
                    # Clean up common trailing characters
                    actual_value = actual_value.rstrip('.,;')
                    # Ensure it's a valid number format
                    if re.match(r'^[+-]?\d+\.?\d*%?[kmb]?$', actual_value):
                        return actual_value
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract actual from title '{title}': {e}")
            return None

    def _archive_economic_data_releases(self, news_items: List[Dict]) -> None:
        """Archive economic data releases for longer-term storage"""
        try:
            from datetime import datetime, date
            
            # Look for news items that contain economic data
            economic_keywords = [
                'cpi', 'ppi', 'gdp', 'employment', 'unemployment', 'nonfarm', 'payroll', 
                'retail sales', 'manufacturing', 'pmi', 'inflation', 'jobless claims',
                'durable goods', 'consumer confidence', 'trade balance', 'building permits',
                'housing starts', 'core cpi', 'core ppi', 'producer price', 'consumer price'
            ]
            
            today = date.today().isoformat()
            archive_key = f"rss_archive_{today}"
            
            # Get existing archive for today
            existing_archive = cache.get(archive_key) or []
            
            # Find new economic data releases
            new_economic_news = []
            for item in news_items:
                title_lower = item['title'].lower()
                
                # Check if this looks like an economic data release
                if any(keyword in title_lower for keyword in economic_keywords):
                    # Check if it has actual data (numbers/percentages)
                    if any(char in item['title'] for char in ['%', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9']):
                        # Check if we haven't already archived this item
                        if not any(archived['guid'] == item['guid'] for archived in existing_archive):
                            item_with_actual = item.copy()
                            # Try to extract actual value
                            actual_value = self._extract_actual_from_news_title(item['title'])
                            if actual_value:
                                item_with_actual['extracted_actual'] = actual_value
                                item_with_actual['archived_at'] = datetime.now().isoformat()
                                new_economic_news.append(item_with_actual)
                                logger.info(f"Archived economic data: {item['title']} -> {actual_value}")
            
            # Add new items to archive
            if new_economic_news:
                existing_archive.extend(new_economic_news)
                # Keep only last 100 items to prevent unlimited growth
                existing_archive = existing_archive[-100:]
                # Cache archive for 24 hours
                cache.set(archive_key, existing_archive, expire=86400)
                logger.info(f"Archived {len(new_economic_news)} new economic data releases")
                
        except Exception as e:
            logger.error(f"Failed to archive economic data: {e}")

    def get_archived_economic_data(self, days_back: int = 7) -> List[Dict]:
        """Get archived economic data releases from the last N days"""
        try:
            from datetime import datetime, date, timedelta
            
            archived_items = []
            
            # Check archives for the last N days
            for i in range(days_back):
                check_date = (date.today() - timedelta(days=i)).isoformat()
                archive_key = f"rss_archive_{check_date}"
                
                day_archive = cache.get(archive_key) or []
                archived_items.extend(day_archive)
            
            # Sort by archived time (most recent first)
            archived_items.sort(key=lambda x: x.get('archived_at', ''), reverse=True)
            
            return archived_items
            
        except Exception as e:
            logger.error(f"Failed to get archived economic data: {e}")
            return []

    def fetch_additional_sources(self, max_items: int = 20) -> List[Dict]:
        """
        Fetch economic news from additional RSS sources
        
        Args:
            max_items: Maximum number of items to return from all additional sources
            
        Returns:
            List of news items from additional sources
        """
        all_additional_news = []
        items_per_source = max(1, max_items // len(self.additional_sources))
        
        for source_name, url in self.additional_sources.items():
            try:
                cache_key = f"additional_rss_{source_name}_{items_per_source}"
                
                # Try cache first
                cached_data = cache.get(cache_key)
                if cached_data:
                    all_additional_news.extend(cached_data)
                    continue
                
                logger.info(f"Fetching {source_name} RSS feed: {url}")
                
                # Fetch RSS feed with proper headers
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                # Parse RSS feed
                import feedparser
                feed = feedparser.parse(response.content)
                
                source_news = []
                for entry in feed.entries[:items_per_source]:
                    # Filter for economic relevance
                    title = entry.get('title', '')
                    if self._is_economic_relevant(title):
                        news_item = {
                            'title': title,
                            'link': entry.get('link', ''),
                            'description': entry.get('description', entry.get('summary', '')),
                            'published': self._parse_date(entry.get('published', '')),
                            'published_raw': entry.get('published', ''),
                            'guid': entry.get('guid', ''),
                            'author': source_name,
                            'source': source_name,
                            'is_high_impact': self._is_high_impact_news(title),
                            'time_ago': self._get_time_ago(entry.get('published', ''))
                        }
                        source_news.append(news_item)
                
                # Cache the results
                cache.set(cache_key, source_news, expire=self.cache_ttl)
                all_additional_news.extend(source_news)
                
                logger.info(f"Successfully fetched {len(source_news)} economic items from {source_name}")
                
            except Exception as e:
                logger.warning(f"Failed to fetch from {source_name}: {e}")
                continue
        
        return all_additional_news[:max_items]

    def _is_economic_relevant(self, title: str) -> bool:
        """
        Check if a news title is economically relevant
        
        Args:
            title: News title to check
            
        Returns:
            True if the title contains economic keywords
        """
        title_lower = title.lower()
        
        # Core economic indicators
        economic_keywords = [
            'gdp', 'inflation', 'cpi', 'ppi', 'employment', 'unemployment', 'jobs', 'payroll',
            'retail sales', 'manufacturing', 'pmi', 'interest rate', 'fed', 'federal reserve',
            'central bank', 'ecb', 'boe', 'boj', 'fomc', 'rate decision', 'monetary policy',
            'consumer confidence', 'consumer spending', 'durable goods', 'trade balance',
            'building permits', 'housing starts', 'jobless claims', 'nonfarm', 'non-farm',
            'producer price', 'consumer price', 'core inflation', 'economic growth',
            'recession', 'beige book', 'earnings', 'ism', 'business confidence',
            'industrial production', 'capacity utilization', 'new home sales',
            'existing home sales', 'pending home sales', 'mortgage rates'
        ]
        
        # Currency and market terms
        market_keywords = [
            'usd', 'eur', 'gbp', 'jpy', 'aud', 'cad', 'chf', 'nzd',
            'dollar', 'euro', 'pound', 'yen', 'forex', 'fx',
            'treasury', 'bond', 'yield', 'stocks', 'market'
        ]
        
        # Economic entities and regions
        entity_keywords = [
            'united states', 'us ', 'usa', 'europe', 'eurozone', 'uk', 'britain',
            'japan', 'china', 'canada', 'australia', 'switzerland', 'new zealand'
        ]
        
        all_keywords = economic_keywords + market_keywords + entity_keywords
        
        return any(keyword in title_lower for keyword in all_keywords)

    def _remove_duplicate_news(self, news_items: List[Dict]) -> List[Dict]:
        """
        Remove duplicate news items based on title similarity
        
        Args:
            news_items: List of news items to deduplicate
            
        Returns:
            List of unique news items
        """
        if not news_items:
            return news_items
        
        unique_items = []
        seen_titles = set()
        
        for item in news_items:
            title = item.get('title', '').lower().strip()
            
            # Create a normalized version for duplicate detection
            # Remove common prefixes and normalize spacing
            normalized_title = title
            for prefix in ['breaking:', 'update:', 'alert:', 'news:', 'forex:', 'fx:']:
                if normalized_title.startswith(prefix):
                    normalized_title = normalized_title[len(prefix):].strip()
            
            # Remove extra whitespace and punctuation
            normalized_title = ' '.join(normalized_title.split())
            normalized_title = normalized_title.rstrip('.,!?;:')
            
            # Check for similarity with existing titles
            is_duplicate = False
            for seen_title in seen_titles:
                # Simple similarity check: if 80% of words match, consider it duplicate
                title_words = set(normalized_title.split())
                seen_words = set(seen_title.split())
                
                if len(title_words) > 0 and len(seen_words) > 0:
                    intersection = len(title_words.intersection(seen_words))
                    union = len(title_words.union(seen_words))
                    similarity = intersection / union if union > 0 else 0
                    
                    if similarity > 0.8:  # 80% similarity threshold
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique_items.append(item)
                seen_titles.add(normalized_title)
        
        return unique_items

# Global instance
rss_service = RSSService()