#!/usr/bin/env python3
"""
Manual trigger for weekly Forex Factory calendar update
Use this script to manually trigger a weekly calendar structure update
"""

import sys
import os
from pathlib import Path

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.pollers.forex_factory_poller import ForexFactoryPoller

def main():
    print("🗓️  Manual Weekly Forex Factory Calendar Update")
    print("=" * 50)
    
    try:
        # Create poller instance
        poller = ForexFactoryPoller()
        
        # Force weekly update
        print("🔄 Starting weekly calendar structure update...")
        success = poller.update_calendar_structure()
        
        if success:
            print("✅ Weekly calendar structure update completed successfully!")
            print(f"📅 Next automatic weekly update will be on Sunday")
            
            # Show some stats
            current_file = poller.data_dir / "ff_calendar_current.json"
            if current_file.exists():
                import json
                with open(current_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"📊 Calendar now contains {len(data)} events")
        else:
            print("❌ Weekly calendar structure update failed!")
            return 1
            
    except Exception as e:
        print(f"💥 Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())