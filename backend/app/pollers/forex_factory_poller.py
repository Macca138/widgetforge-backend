"""
Forex Factory Calendar Poller - Standalone Process
This script runs as a separate process to update Forex Factory calendar data
"""
import requests
import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ForexFactoryPoller:
    def __init__(self):
        # Configuration
        self.ff_calendar_url = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
        self.weekly_update_interval = 604800  # Weekly update (7 days * 24 hours * 60 minutes * 60 seconds)
        self.actual_update_interval = 60      # Update actuals every minute
        self.retry_interval = 300            # Retry after 5 minutes on failure
        self.last_weekly_update = None
        
        # Data directories (same as services expect)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.backup_dir = self.data_dir / "backups"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Load last weekly update time from metadata
        self.load_last_weekly_update()
        
        logger.info("Forex Factory Calendar Poller initialized")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Weekly update interval: {self.weekly_update_interval} seconds (7 days)")
        logger.info(f"Actual update interval: {self.actual_update_interval} seconds (1 minute)")
        logger.info(f"Last weekly update: {self.last_weekly_update}")
        
    def load_last_weekly_update(self):
        """Load the last weekly update time from metadata"""
        try:
            metadata_file = self.data_dir / "ff_calendar_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    last_weekly_str = metadata.get('last_weekly_update')
                    if last_weekly_str:
                        self.last_weekly_update = datetime.fromisoformat(last_weekly_str)
                        logger.info(f"Loaded last weekly update time: {self.last_weekly_update}")
                    else:
                        logger.info("No last weekly update time found in metadata")
            else:
                logger.info("No metadata file found, will perform initial weekly update")
        except Exception as e:
            logger.warning(f"Error loading last weekly update time: {e}")
    
    def save_last_weekly_update(self):
        """Save the last weekly update time to metadata"""
        try:
            metadata_file = self.data_dir / "ff_calendar_metadata.json"
            metadata = {}
            
            # Load existing metadata if it exists
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            
            # Update with last weekly update time
            metadata['last_weekly_update'] = self.last_weekly_update.isoformat()
            
            # Save back to file
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Saved last weekly update time: {self.last_weekly_update}")
            
        except Exception as e:
            logger.warning(f"Error saving last weekly update time: {e}")
    
    def backup_existing_file(self):
        """Backup existing calendar file if it exists"""
        try:
            current_file = self.data_dir / "ff_calendar_current.json"
            if current_file.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"ff_calendar_backup_{timestamp}.json"
                
                # Read and write to create backup
                with open(current_file, 'r', encoding='utf-8') as src:
                    data = src.read()
                with open(backup_file, 'w', encoding='utf-8') as dst:
                    dst.write(data)
                    
                logger.info(f"Backed up existing calendar to: {backup_file.name}")
                
        except Exception as e:
            logger.warning(f"Failed to backup existing file: {e}")
    
    def download_calendar_data(self):
        """Download calendar data from Forex Factory JSON endpoint"""
        try:
            logger.info(f"Downloading calendar data from: {self.ff_calendar_url}")
            
            response = requests.get(self.ff_calendar_url, timeout=30)
            response.raise_for_status()
            
            # Validate JSON
            calendar_data = response.json()
            
            if not calendar_data:
                raise ValueError("Empty calendar data received")
                
            logger.info(f"Successfully downloaded {len(calendar_data)} calendar events")
            return calendar_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error downloading calendar data: {e}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading calendar data: {e}")
            raise
    
    def save_calendar_data(self, data):
        """Save calendar data to local files"""
        try:
            # Save main current file
            current_file = self.data_dir / "ff_calendar_current.json"
            
            with open(current_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Also save with timestamp for historical reference
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_file = self.data_dir / f"ff_calendar_{timestamp}.json"
            
            with open(timestamped_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Calendar data saved to: {current_file.name}")
            logger.info(f"Timestamped copy saved to: {timestamped_file.name}")
            
            # Update metadata
            metadata = {
                "last_updated": datetime.now().isoformat(),
                "total_events": len(data),
                "source_url": self.ff_calendar_url,
                "file_size_bytes": current_file.stat().st_size
            }
            
            metadata_file = self.data_dir / "ff_calendar_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Metadata updated: {metadata}")
            
        except Exception as e:
            logger.error(f"Error saving calendar data: {e}")
            raise
    
    def cleanup_old_files(self):
        """Clean up old backup and timestamped files (keep last 10)"""
        try:
            # Clean up backup files
            backup_files = list(self.backup_dir.glob("ff_calendar_backup_*.json"))
            if len(backup_files) > 10:
                backup_files.sort(key=lambda x: x.stat().st_mtime)
                for old_file in backup_files[:-10]:
                    old_file.unlink()
                    logger.info(f"Cleaned up old backup: {old_file.name}")
            
            # Clean up timestamped files
            timestamped_files = list(self.data_dir.glob("ff_calendar_2*.json"))
            if len(timestamped_files) > 10:
                timestamped_files.sort(key=lambda x: x.stat().st_mtime)
                for old_file in timestamped_files[:-10]:
                    old_file.unlink()
                    logger.info(f"Cleaned up old timestamped file: {old_file.name}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def is_sunday(self):
        """Check if today is Sunday (start of trading week)"""
        return datetime.now().weekday() == 6  # 6 = Sunday
    
    def should_update_weekly(self):
        """Check if we should do a weekly calendar structure update"""
        # Update on Sunday, but only after 18:00 to allow Forex Factory to publish new data
        if self.is_sunday():
            current_hour = datetime.now().hour
            if current_hour >= 18:  # Only update after 18:00 on Sunday
                return True
        
        # Check if we've never done a weekly update
        if self.last_weekly_update is None:
            return True
            
        # Check if it's been more than a week since last update
        time_since_last = datetime.now() - self.last_weekly_update
        if time_since_last.total_seconds() > self.weekly_update_interval:
            return True
            
        return False
    
    def validate_calendar_data(self, calendar_data):
        """Validate that calendar data contains current week's events"""
        try:
            if not calendar_data:
                logger.warning("Calendar data is empty")
                return False
                
            # Check if we have events for the current week
            from datetime import datetime, timedelta
            now = datetime.now()
            week_start = now - timedelta(days=now.weekday())  # Monday of current week
            week_end = week_start + timedelta(days=6)  # Sunday of current week
            
            current_week_events = 0
            for event in calendar_data:
                event_date_str = event.get('date', '')
                if event_date_str:
                    try:
                        # Parse the date (adjust format as needed)
                        event_date = datetime.fromisoformat(event_date_str.replace('Z', '+00:00'))
                        if week_start <= event_date.replace(tzinfo=None) <= week_end:
                            current_week_events += 1
                    except:
                        continue
            
            logger.info(f"Found {current_week_events} events for current week")
            
            # We expect at least some events for the current week
            if current_week_events < 5:  # Minimum threshold
                logger.warning(f"Only {current_week_events} events found for current week, data might be stale")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating calendar data: {e}")
            return False

    def update_calendar_structure(self):
        """Weekly update - Download new calendar structure from Forex Factory"""
        try:
            logger.info("Performing weekly calendar structure update...")
            
            # Backup existing data
            self.backup_existing_file()
            
            # Download new data
            calendar_data = self.download_calendar_data()
            
            # Validate the data is current
            if not self.validate_calendar_data(calendar_data):
                logger.warning("Calendar data validation failed, may be stale data")
                # Continue anyway but log the warning
            
            # Save new data
            self.save_calendar_data(calendar_data)
            
            # Cleanup old files
            self.cleanup_old_files()
            
            # Update the last weekly update time
            self.last_weekly_update = datetime.now()
            self.save_last_weekly_update()
            
            logger.info("Weekly calendar structure update completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Weekly calendar structure update failed: {e}")
            return False
    
    def update_actual_results(self):
        """Frequent update - Update actual results for existing events"""
        try:
            logger.info("Updating actual results from calendar...")
            
            # Download fresh calendar data to get updated actuals
            calendar_data = self.download_calendar_data()
            
            # Load existing calendar structure
            current_file = self.data_dir / "ff_calendar_current.json"
            if not current_file.exists():
                logger.warning("No existing calendar structure found, performing full update")
                return self.update_calendar_structure()
            
            # For now, just update the current file with fresh data
            # In the future, we could be smarter about only updating actuals
            with open(current_file, 'w', encoding='utf-8') as f:
                json.dump(calendar_data, f, indent=2, ensure_ascii=False)
            
            logger.info("Actual results update completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Actual results update failed: {e}")
            return False
    
    def run(self):
        """Main polling loop with dual update schedule"""
        logger.info("Starting Forex Factory Calendar Poller...")
        logger.info("Schedule: Weekly structure updates on Sunday, actual results every minute")
        
        # Initial update - check if we need a weekly update first
        if self.should_update_weekly():
            logger.info("Performing initial weekly calendar structure update...")
            success = self.update_calendar_structure()
            if not success:
                logger.warning("Initial weekly update failed, will retry in normal cycle")
        else:
            logger.info("Performing initial actual results update...")
            success = self.update_actual_results()
            if not success:
                logger.warning("Initial actual results update failed, will retry in normal cycle")
        
        # Main polling loop
        while True:
            try:
                logger.info(f"Waiting {self.actual_update_interval} seconds until next update...")
                time.sleep(self.actual_update_interval)
                
                # Check if we need a weekly structure update
                if self.should_update_weekly():
                    logger.info("Starting weekly calendar structure update...")
                    success = self.update_calendar_structure()
                    if not success:
                        logger.warning(f"Weekly update failed, will retry in {self.retry_interval} seconds")
                        time.sleep(self.retry_interval)
                else:
                    # Regular actual results update
                    logger.info("Starting actual results update...")
                    success = self.update_actual_results()
                    if not success:
                        logger.warning(f"Actual results update failed, will retry in {self.retry_interval} seconds")
                        time.sleep(self.retry_interval)
                
            except KeyboardInterrupt:
                logger.info("Received shutdown signal, stopping poller...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}")
                logger.info(f"Continuing after {self.retry_interval} seconds...")
                time.sleep(self.retry_interval)
        
        logger.info("Forex Factory Calendar Poller stopped")

def main():
    """Entry point for the poller"""
    try:
        poller = ForexFactoryPoller()
        poller.run()
    except Exception as e:
        logger.error(f"Failed to start Forex Factory Calendar Poller: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()