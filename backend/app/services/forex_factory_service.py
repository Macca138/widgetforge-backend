import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
import os
from .cache_service import cache

logger = logging.getLogger(__name__)

class ForexFactoryService:
    def __init__(self):
        self.cache_ttl = 3600  # 1 hour cache for calendar data
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", ".cache")
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_latest_calendar_data(self) -> Optional[List[Dict]]:
        """Load the most recent Forex Factory calendar JSON file"""
        try:
            # Look for the most recent JSON file in data directory
            json_files = [f for f in os.listdir(self.data_dir) if f.startswith('ff_calendar') and f.endswith('.json')]
            
            if not json_files:
                logger.warning("No Forex Factory calendar files found in data directory")
                return None
            
            # Get the most recent file
            latest_file = max(json_files, key=lambda x: os.path.getctime(os.path.join(self.data_dir, x)))
            file_path = os.path.join(self.data_dir, latest_file)
            
            logger.info(f"Loading calendar data from: {latest_file}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to load calendar data: {e}")
            return None
    
    def parse_event_date(self, date_str: str) -> Optional[datetime]:
        """Parse ISO date string to datetime object"""
        try:
            # Parse ISO format: "2025-07-08T00:30:00-04:00"
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return None
    
    def calculate_time_until(self, event_date: datetime) -> str:
        """Calculate human-readable time until event"""
        try:
            now = datetime.now(timezone.utc)
            
            # Convert event_date to UTC if it has timezone info
            if event_date.tzinfo:
                event_utc = event_date.astimezone(timezone.utc)
            else:
                event_utc = event_date.replace(tzinfo=timezone.utc)
            
            delta = event_utc - now
            
            if delta.total_seconds() < 0:
                # Event has passed
                abs_delta = abs(delta.total_seconds())
                if abs_delta < 3600:  # Less than 1 hour ago
                    minutes = int(abs_delta // 60)
                    return f"{minutes}m ago"
                elif abs_delta < 86400:  # Less than 1 day ago
                    hours = int(abs_delta // 3600)
                    return f"{hours}h ago"
                else:
                    days = int(abs_delta // 86400)
                    return f"{days}d ago"
            else:
                # Event is upcoming
                total_seconds = delta.total_seconds()
                if total_seconds < 3600:  # Less than 1 hour
                    minutes = int(total_seconds // 60)
                    return f"in {minutes}m"
                elif total_seconds < 86400:  # Less than 1 day
                    hours = int(total_seconds // 3600)
                    return f"in {hours}h"
                else:
                    days = int(total_seconds // 86400)
                    return f"in {days}d"
                    
        except Exception as e:
            logger.warning(f"Failed to calculate time until event: {e}")
            return "Recent"
    
    def get_upcoming_events(self, max_events: int = 20, impact_filter: Optional[str] = None) -> List[Dict]:
        """Get upcoming economic calendar events"""
        cache_key = f"ff_upcoming_events_{max_events}_{impact_filter}"
        
        try:
            # Try cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Load calendar data
            calendar_data = self.load_latest_calendar_data()
            if not calendar_data:
                return []
            
            now = datetime.now(timezone.utc)
            upcoming_events = []
            
            for event in calendar_data:
                event_date = self.parse_event_date(event.get('date', ''))
                if not event_date:
                    continue
                
                # Convert to UTC for comparison
                if event_date.tzinfo:
                    event_utc = event_date.astimezone(timezone.utc)
                else:
                    event_utc = event_date.replace(tzinfo=timezone.utc)
                
                # Only include future events
                if event_utc > now:
                    # Apply impact filter if specified
                    if impact_filter and event.get('impact', '').lower() != impact_filter.lower():
                        continue
                    
                    processed_event = {
                        'title': event.get('title', 'Economic Event'),
                        'country': event.get('country', 'GLOBAL'),
                        'date': event.get('date', ''),
                        'impact': event.get('impact', 'Low'),
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', ''),
                        'time_until': self.calculate_time_until(event_date),
                        'timestamp': int(event_utc.timestamp())
                    }
                    upcoming_events.append(processed_event)
            
            # Sort by date
            upcoming_events.sort(key=lambda x: x['timestamp'])
            
            # Limit results
            result = upcoming_events[:max_events]
            
            # Cache for 1 hour
            cache.set(cache_key, result, expire=self.cache_ttl)
            
            logger.info(f"Returned {len(result)} upcoming events")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get upcoming events: {e}")
            return []
    
    def get_high_impact_events(self, max_events: int = 10) -> List[Dict]:
        """Get upcoming high-impact events specifically"""
        return self.get_upcoming_events(max_events=max_events, impact_filter="High")
    
    def enhance_events_with_rss_results(self, events: List[Dict], rss_news: List[Dict]) -> List[Dict]:
        """Enhance Forex Factory events with actual results from RSS news"""
        enhanced_events = []
        
        for event in events:
            enhanced_event = event.copy()
            
            # Look for matching news in RSS feed
            for news_item in rss_news:
                news_title = news_item.get('title', '').lower()
                event_title = event.get('title', '').lower()
                event_country = event.get('country', '').lower()
                
                # Check if this news item matches this economic event (more specific matching)
                if self._is_specific_news_event_match(news_title, event_title, event_country):
                    # Extract actual result from news title
                    actual_result = self._extract_actual_from_news_title(news_item.get('title', ''))
                    if actual_result:
                        enhanced_event['actual'] = actual_result
                        enhanced_event['actual_source'] = 'RSS'
                        enhanced_event['matched_news'] = news_item.get('title', '')  # For debugging
                        break
            
            enhanced_events.append(enhanced_event)
        
        return enhanced_events
    
    def _is_specific_news_event_match(self, news_title: str, event_title: str, event_country: str) -> bool:
        """More specific matching to ensure correct news matches correct event"""
        # Check for country/currency mentions first
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
        
        # More specific economic indicator matching
        specific_mappings = {
            'employment change': ['employment change'],
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
        
        # Check for exact or very close indicator matches
        for indicator, terms in specific_mappings.items():
            if indicator in event_title:
                # Require the specific term to be in news title too
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

    def get_recent_past_events(self, max_events: int = 10, impact_filter: Optional[str] = None) -> List[Dict]:
        """Get recent past events that have already occurred with actual results"""
        cache_key = f"ff_recent_past_events_{max_events}_{impact_filter}"
        
        try:
            # Try cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Load calendar data
            calendar_data = self.load_latest_calendar_data()
            if not calendar_data:
                return []
            
            now = datetime.now(timezone.utc)
            past_events = []
            
            for event in calendar_data:
                event_date = self.parse_event_date(event.get('date', ''))
                if not event_date:
                    continue
                
                # Convert to UTC for comparison
                if event_date.tzinfo:
                    event_utc = event_date.astimezone(timezone.utc)
                else:
                    event_utc = event_date.replace(tzinfo=timezone.utc)
                
                # Only include past events from the last 24 hours
                time_diff = now - event_utc
                if time_diff.total_seconds() > 0 and time_diff.total_seconds() <= 86400:  # Last 24 hours
                    # Apply impact filter if specified
                    if impact_filter and event.get('impact', '').lower() != impact_filter.lower():
                        continue
                    
                    processed_event = {
                        'title': event.get('title', 'Economic Event'),
                        'country': event.get('country', 'GLOBAL'),
                        'date': event.get('date', ''),
                        'impact': event.get('impact', 'Low'),
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', ''),
                        'actual': event.get('actual', ''),  # Show actual results if available
                        'time_until': self.calculate_time_until(event_date),
                        'timestamp': int(event_utc.timestamp()),
                        'status': 'completed'  # Mark as completed event
                    }
                    past_events.append(processed_event)
            
            # Sort by date (most recent first)
            past_events.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Limit results
            result = past_events[:max_events]
            
            # Cache for 30 minutes
            cache.set(cache_key, result, expire=1800)
            
            logger.info(f"Returned {len(result)} recent past events")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent past events: {e}")
            return []
    
    def get_todays_events(self, impact_filter: Optional[str] = None) -> List[Dict]:
        """Get today's economic events"""
        cache_key = f"ff_todays_events_{impact_filter}"
        
        try:
            # Try cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Load calendar data
            calendar_data = self.load_latest_calendar_data()
            if not calendar_data:
                return []
            
            today = datetime.now(timezone.utc).date()
            todays_events = []
            
            for event in calendar_data:
                event_date = self.parse_event_date(event.get('date', ''))
                if not event_date:
                    continue
                
                # Convert to UTC for comparison
                if event_date.tzinfo:
                    event_utc = event_date.astimezone(timezone.utc)
                else:
                    event_utc = event_date.replace(tzinfo=timezone.utc)
                
                # Check if event is today
                if event_utc.date() == today:
                    # Apply impact filter if specified
                    if impact_filter and event.get('impact', '').lower() != impact_filter.lower():
                        continue
                    
                    processed_event = {
                        'title': event.get('title', 'Economic Event'),
                        'country': event.get('country', 'GLOBAL'),
                        'date': event.get('date', ''),
                        'impact': event.get('impact', 'Low'),
                        'forecast': event.get('forecast', ''),
                        'previous': event.get('previous', ''),
                        'time_until': self.calculate_time_until(event_date),
                        'timestamp': int(event_utc.timestamp())
                    }
                    todays_events.append(processed_event)
            
            # Sort by time
            todays_events.sort(key=lambda x: x['timestamp'])
            
            # Cache for 30 minutes
            cache.set(cache_key, todays_events, expire=1800)
            
            logger.info(f"Returned {len(todays_events)} events for today")
            return todays_events
            
        except Exception as e:
            logger.error(f"Failed to get today's events: {e}")
            return []

# Create singleton instance
forex_factory_service = ForexFactoryService()