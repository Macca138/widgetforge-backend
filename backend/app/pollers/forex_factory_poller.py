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
        self.update_interval = 3600  # Update every hour (3600 seconds)
        self.retry_interval = 300    # Retry after 5 minutes on failure
        
        # Data directories (same as services expect)
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.backup_dir = self.data_dir / "backups"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info("Forex Factory Calendar Poller initialized")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Update interval: {self.update_interval} seconds")
        
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
    
    def update_calendar(self):
        """Single update cycle"""
        try:
            # Backup existing data
            self.backup_existing_file()
            
            # Download new data
            calendar_data = self.download_calendar_data()
            
            # Save new data
            self.save_calendar_data(calendar_data)
            
            # Cleanup old files
            self.cleanup_old_files()
            
            logger.info("Calendar update completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Calendar update failed: {e}")
            return False
    
    def run(self):
        """Main polling loop"""
        logger.info("Starting Forex Factory Calendar Poller...")
        logger.info(f"Will update every {self.update_interval} seconds")
        
        # Initial update
        logger.info("Performing initial calendar update...")
        success = self.update_calendar()
        
        if not success:
            logger.warning("Initial update failed, will retry in normal cycle")
        
        # Main polling loop
        while True:
            try:
                logger.info(f"Waiting {self.update_interval} seconds until next update...")
                time.sleep(self.update_interval)
                
                logger.info("Starting scheduled calendar update...")
                success = self.update_calendar()
                
                if not success:
                    logger.warning(f"Update failed, will retry in {self.retry_interval} seconds")
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