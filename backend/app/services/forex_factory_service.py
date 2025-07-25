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
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)
    
    def load_latest_calendar_data(self) -> Optional[List[Dict]]:
        """Load the most recent Forex Factory calendar JSON file"""
        try:
            # First, try to load the current file (updated by scheduled job)
            current_file = os.path.join(self.data_dir, 'ff_calendar_current.json')
            if os.path.exists(current_file):
                logger.info("Loading calendar data from: ff_calendar_current.json")
                with open(current_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data
            
            # Fallback: Look for the most recent JSON file in data directory
            json_files = [f for f in os.listdir(self.data_dir) if f.startswith('ff_calendar') and f.endswith('.json')]
            
            if not json_files:
                logger.warning("No Forex Factory calendar files found in data directory")
                logger.info("To enable calendar data, run the update script: python update_ff_calendar.py")
                return None
            
            # Get the most recent file
            latest_file = max(json_files, key=lambda x: os.path.getctime(os.path.join(self.data_dir, x)))
            file_path = os.path.join(self.data_dir, latest_file)
            
            logger.info(f"Loading calendar data from fallback file: {latest_file}")
            
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
        """Enhance Forex Factory events with actual results from RSS news and archived data"""
        enhanced_events = []

        # Import RSS service to get archived data
        from .rss_service import rss_service
        
        # Get archived economic data from the last 7 days
        archived_data = rss_service.get_archived_economic_data(days_back=7)
        logger.info(f"Retrieved {len(archived_data)} archived economic data items")
        
        # Combine current RSS news with archived data
        all_news_sources = list(rss_news) + archived_data

        for event in events:
            enhanced_event = event.copy()
            # Only look for RSS results if we don't already have an actual value
            if not enhanced_event.get('actual', '').strip():
                # Look for matching news in all news sources (current + archived)
                for news_item in all_news_sources:
                    news_title = news_item.get('title', '').lower()
                    event_title = event.get('title', '').lower()
                    event_country = event.get('country', '').lower()
                    
                    # Check if this news item matches this economic event (more specific matching)
                    if self._is_specific_news_event_match(news_title, event_title, event_country):
                        # Try to get extracted actual value first (from archive)
                        actual_result = news_item.get('extracted_actual')
                        
                        # If not found in archive, try to extract from title
                        if not actual_result:
                            actual_result = self._extract_actual_from_news_title(news_item.get('title', ''))
                        
                        if actual_result:
                            enhanced_event['actual'] = actual_result
                            enhanced_event['actual_source'] = 'Archived RSS' if 'archived_at' in news_item else 'RSS'
                            enhanced_event['matched_news'] = news_item.get('title', '')  # For debugging
                            if 'archived_at' in news_item:
                                enhanced_event['archived_at'] = news_item['archived_at']
                            logger.info(f"Enhanced {event_title} with actual: {actual_result} from {enhanced_event['actual_source']}")
                            break
            else:
                # Mark that we already had the actual value from the original data
                enhanced_event['actual_source'] = 'Calendar'
            enhanced_events.append(enhanced_event)

        return enhanced_events
    
    def _is_news_event_match(self, news_title: str, event_title: str, event_country: str) -> bool:
        """Check if RSS news matches Forex Factory event"""
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
        
        # Check for currency/country mentions
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
        
        if country_mentioned:
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
    
    def _is_specific_news_event_match(self, news_title: str, event_title: str, event_country: str) -> bool:
        """More specific matching to ensure correct news matches correct event"""
        # Check for country/currency mentions first
        currency_mappings = {
            'usd': ['us', 'usa', 'united states', 'american', 'dollar'],
            'eur': ['eu', 'euro', 'european', 'eurozone'],
            'gbp': ['uk', 'british', 'britain', 'england', 'pound', 'gbp', 'sterling', 'united kingdom'],
            'jpy': ['japan', 'japanese', 'yen'],
            'aud': ['australia', 'australian', 'aussie'],
            'cad': ['canada', 'canadian', 'cad'],
            'chf': ['swiss', 'switzerland', 'franc'],
            'nzd': ['new zealand', 'nz', 'kiwi']
        }
        # Check if news mentions the country/currency (more flexible matching)
        country_mentioned = False
        if event_country in currency_mappings:
            country_terms = currency_mappings[event_country]
            if any(term in news_title for term in country_terms):
                country_mentioned = True

        # Also check if the currency code itself is in the title
        if event_country.upper() in news_title.upper():
            country_mentioned = True

        # More specific economic indicator matching with enhanced patterns
        specific_mappings = {
            'employment change': ['employment change', 'nonfarm', 'non-farm', 'payroll', 'employment', 'jobs'],
            'unemployment rate': ['unemployment rate', 'jobless rate', 'unemployment'],
            'gdp': ['gdp', 'gross domestic product', 'economic growth'],
            'inflation': ['inflation', 'cpi', 'consumer price', 'ppi', 'producer price', 'core cpi', 'core inflation'],
            'interest rate': ['interest rate', 'rate decision', 'fomc', 'fed rate'],
            'retail sales': ['retail sales', 'retail sales ex auto', 'core retail sales'],
            'manufacturing': ['manufacturing', 'pmi', 'ism manufacturing', 'manufacturing pmi'],
            'trade balance': ['trade balance'],
            'building permits': ['building permits'],
            'housing': ['housing', 'home sales', 'new home sales', 'existing home sales'],
            'jobless claims': ['jobless claims', 'initial claims', 'weekly claims'],
            'consumer confidence': ['consumer confidence', 'consumer sentiment'],
            'durable goods': ['durable goods', 'durable goods orders'],
            'services pmi': ['services pmi', 'ism services'],
            'producer price': ['producer price', 'ppi', 'producer prices'],
            'consumer price': ['consumer price', 'cpi', 'consumer prices'],
            'core ppi m/m': ['core ppi', 'core producer price'], 
            'ppi m/m': ['ppi', 'producer price'],
        }

        # Check for exact or very close indicator matches
        for indicator, terms in specific_mappings.items():
            if indicator in event_title:
                # Require the specific term to be in news title too
                if any(term in news_title for term in terms):
                    # If we have both country and indicator match, that's good enough
                    if country_mentioned:
                        return True
                    # Even without explicit country mention, if the indicator is very specific, allow it
                    if indicator in ['producer price', 'consumer price', 'employment change', 'unemployment rate']:
                        return True
        return False
    
    def _extract_actual_from_news_title(self, title: str) -> Optional[str]:
        """Extract actual result value from news title with enhanced patterns and validation"""
        try:
            import re
            
            # Enhanced patterns to extract actual values from various news title formats
            actual_patterns = [
                # Pattern: "Actual 83.1k" or "Actual: 83.1k"
                r'actual[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "2.1% vs 2.0% Expected" or "2.1% vs 2.0% Forecast"
                r'([+-]?\d+\.?\d*%?[kmb]?)\s+vs\.?\s+[+-]?\d+\.?\d*%?[kmb]?\s+(?:expected|forecast|est)',
                # Pattern: "GDP 2.1% (Forecast 2.0%)" or "GDP 2.1% (Est 2.0%)"
                r'([+-]?\d+\.?\d*%?[kmb]?)\s*\((?:forecast|est|expected)[:\s]*[+-]?\d+\.?\d*%?[kmb]?\)',
                # Pattern: "comes in at 2.1%" or "reported at 2.1%"
                r'(?:comes?\s+in\s+at|reported\s+at|arrives?\s+at)\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "rises to 2.1%" or "falls to 2.1%" or "climbs to 2.1%"
                r'(?:rises?\s+to|falls?\s+to|climbs?\s+to|drops?\s+to|jumps?\s+to|slides?\s+to)\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "hits 2.1%" or "reaches 2.1%"
                r'(?:hits?|reaches?|touches?|prints?)\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "shows 2.1%" or "registers 2.1%"
                r'(?:shows?|registers?|posts?|records?)\s+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: PMI specific - "PMI at 52.1" or "PMI 52.1"
                r'pmi\s+(?:at\s+)?([+-]?\d+\.?\d*)',
                # Pattern: "GDP Growth 2.1%" or "CPI Inflation 2.1%"
                r'(?:gdp|cpi|ppi|inflation|growth|unemployment|employment)\s+(?:rate\s+|growth\s+|at\s+)?([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Result: 2.1%" or "Result 2.1%"
                r'result[:\s]+([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "Final reading 2.1%" or "Preliminary 2.1%"
                r'(?:final|preliminary|revised|initial)\s+(?:reading\s+|figure\s+|estimate\s+)?([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: "beats expectations at 2.1%" or "misses forecast at 2.1%"
                r'(?:beats?|misses?)\s+(?:expectations?|forecasts?)\s+(?:at\s+|with\s+)([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: specific economic indicators followed by value
                r'(?:employment|unemployment|retail|manufacturing|trade|building|housing|jobless|consumer|durable|services)\s+(?:change|rate|sales|permits|claims|confidence|goods|index)\s+(?:at\s+|of\s+)?([+-]?\d+\.?\d*%?[kmb]?)',
                # Pattern: general number before vs/v (more flexible)
                r'([+-]?\d+\.?\d*%?[kmb]?)\s+(?:vs\.?|v\.?)\s+[+-]?\d+\.?\d*%?[kmb]?'
            ]

            title_lower = title.lower()
            extracted_values = []
            
            for pattern in actual_patterns:
                matches = re.finditer(pattern, title_lower)
                for match in matches:
                    actual_value = match.group(1).strip()
                    # Clean up common trailing characters
                    actual_value = actual_value.rstrip('.,;:')
                    
                    # Validate the extracted value
                    if self._validate_extracted_value(actual_value, title):
                        extracted_values.append(actual_value)
            
            # Return the first valid value, prioritizing more specific patterns
            if extracted_values:
                # Remove duplicates while preserving order
                seen = set()
                unique_values = []
                for val in extracted_values:
                    if val not in seen:
                        seen.add(val)
                        unique_values.append(val)
                
                return unique_values[0]
            
            return None

        except Exception as e:
            logger.warning(f"Failed to extract actual from title '{title}': {e}")
            return None

    def _validate_extracted_value(self, value: str, title: str) -> bool:
        """
        Validate that an extracted value is reasonable for economic data
        
        Args:
            value: The extracted value to validate
            title: The original title for context
            
        Returns:
            True if the value appears to be a valid economic indicator
        """
        try:
            import re
            
            # Basic format validation
            if not re.match(r'^[+-]?\d+\.?\d*%?[kmb]?$', value, re.IGNORECASE):
                return False
            
            # Extract numeric part
            numeric_match = re.match(r'^([+-]?\d+\.?\d*)', value)
            if not numeric_match:
                return False
            
            numeric_value = float(numeric_match.group(1))
            title_lower = title.lower()
            
            # Context-based validation
            # PMI values should be roughly 0-100
            if 'pmi' in title_lower:
                return 0 <= abs(numeric_value) <= 200  # Allow some flexibility
            
            # Percentage values should be reasonable
            if '%' in value:
                # Most economic percentages are between -50% and +50%
                return -100 <= numeric_value <= 100
            
            # Employment/unemployment numbers with k/m suffixes
            if any(term in title_lower for term in ['employment', 'jobs', 'payroll', 'unemployment', 'jobless']):
                if value.lower().endswith(('k', 'm')):
                    return -10000 <= numeric_value <= 10000  # Reasonable range for employment changes
            
            # GDP values are usually small percentages
            if 'gdp' in title_lower:
                return -20 <= numeric_value <= 20
            
            # Interest rates are usually small percentages
            if any(term in title_lower for term in ['rate', 'fed', 'federal', 'interest']):
                return -10 <= numeric_value <= 25
            
            # Default validation - allow reasonable economic values
            return -1000000 <= numeric_value <= 1000000
            
        except (ValueError, TypeError):
            return False

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
    
    def get_recent_high_impact_event(self) -> Optional[Dict]:
        """Get the most recent high-impact event from today (for pinned display)"""
        cache_key = "ff_recent_high_impact"
        
        try:
            # Try cache first
            cached_data = cache.get(cache_key)
            if cached_data:
                return cached_data
            
            # Load calendar data
            calendar_data = self.load_latest_calendar_data()
            if not calendar_data:
                return None
            
            now = datetime.now(timezone.utc)
            today = now.date()
            recent_high_impact = None
            latest_timestamp = 0
            
            for event in calendar_data:
                # Only high-impact events
                if event.get('impact', '').lower() != 'high':
                    continue
                
                event_date = self.parse_event_date(event.get('date', ''))
                if not event_date:
                    continue
                
                # Convert to UTC
                if event_date.tzinfo:
                    event_utc = event_date.astimezone(timezone.utc)
                else:
                    event_utc = event_date.replace(tzinfo=timezone.utc)
                
                # Only today's events that have already occurred
                if event_utc.date() == today and event_utc <= now:
                    timestamp = int(event_utc.timestamp())
                    if timestamp > latest_timestamp:
                        latest_timestamp = timestamp
                        recent_high_impact = {
                            'title': event.get('title', 'Economic Event'),
                            'country': event.get('country', 'GLOBAL'),
                            'date': event.get('date', ''),
                            'impact': event.get('impact', 'High'),
                            'forecast': event.get('forecast', ''),
                            'previous': event.get('previous', ''),
                            'time_until': self.calculate_time_until(event_date),
                            'timestamp': timestamp
                        }
            
            # Cache for 15 minutes
            if recent_high_impact:
                cache.set(cache_key, recent_high_impact, expire=900)
            
            return recent_high_impact
            
        except Exception as e:
            logger.error(f"Failed to get recent high-impact event: {e}")
            return None
    
    def get_calendar_summary(self) -> Dict:
        """Get summary statistics of the calendar data"""
        try:
            calendar_data = self.load_latest_calendar_data()
            if not calendar_data:
                return {"error": "No calendar data available"}
            
            total_events = len(calendar_data)
            high_impact = len([e for e in calendar_data if e.get('impact') == 'High'])
            medium_impact = len([e for e in calendar_data if e.get('impact') == 'Medium'])
            low_impact = len([e for e in calendar_data if e.get('impact') == 'Low'])
            
            # Get date range
            dates = []
            for event in calendar_data:
                event_date = self.parse_event_date(event.get('date', ''))
                if event_date:
                    dates.append(event_date)
            
            date_range = {}
            if dates:
                dates.sort()
                date_range = {
                    'start': dates[0].strftime('%Y-%m-%d'),
                    'end': dates[-1].strftime('%Y-%m-%d')
                }
            
            return {
                'total_events': total_events,
                'high_impact': high_impact,
                'medium_impact': medium_impact,
                'low_impact': low_impact,
                'date_range': date_range,
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get calendar summary: {e}")
            return {"error": str(e)}

# Create singleton instance
forex_factory_service = ForexFactoryService()