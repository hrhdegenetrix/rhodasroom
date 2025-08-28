#!/usr/bin/env python3
"""
Compatibility layer for schedule system.
This ensures backward compatibility while transitioning from JSON to SQL.
"""

import json
import os
import database
from datetime import datetime

def ensure_json_compatibility():
    """
    Create JSON files from SQL data for backward compatibility.
    This function can be called periodically to sync SQL data to JSON files.
    """
    
    # Sync planner.json
    try:
        events = database.get_planner_events()
        planner_data = {'schedule': []}
        
        for event in events:
            # Convert SQL format to JSON format
            json_event = {
                'date': event['date'],
                'time': event['time'],
                'event_name': event['event_name'],
                'event_notes': event.get('event_notes', ''),
                'special_occasion': bool(event.get('special_occasion', False)),
                'location': event.get('location', '')
            }
            
            if event.get('event_end'):
                json_event['event_end'] = event['event_end']
            
            if event.get('people_involved'):
                import json as json_module
                try:
                    json_event['people_involved'] = json_module.loads(event['people_involved'])
                except:
                    pass
            
            planner_data['schedule'].append(json_event)
        
        # Write to planner.json
        with open('planner.json', 'w') as f:
            json.dump(planner_data, f, indent=2)
        
        print(f"Synced {len(events)} events to planner.json")
    
    except Exception as e:
        print(f"Error syncing planner.json: {e}")
    
    # Sync daily_schedule.json
    try:
        all_events = database.get_daily_schedule()
        daily_data = {}
        
        for event in all_events:
            day = event['day_of_week']
            if day not in daily_data:
                daily_data[day] = []
            
            json_event = {
                'event_name': event['event_name'],
                'event_notes': event.get('event_notes', ''),
                'start_time': event['start_time'],
                'location': event.get('location', '')
            }
            
            if event.get('event_end'):
                json_event['event_end'] = event['event_end']
            
            daily_data[day].append(json_event)
        
        # Write to daily_schedule.json
        with open('daily_schedule.json', 'w') as f:
            json.dump(daily_data, f, indent=2)
        
        print(f"Synced {len(all_events)} daily events to daily_schedule.json")
    
    except Exception as e:
        print(f"Error syncing daily_schedule.json: {e}")

def check_data_source():
    """
    Check if we should use SQL or JSON as the data source.
    Returns 'sql' if database tables exist and have data, otherwise 'json'.
    """
    try:
        # Check if we have data in SQL tables
        planner_events = database.get_planner_events()
        daily_events = database.get_daily_schedule()
        
        if planner_events or daily_events:
            return 'sql'
    except:
        pass
    
    # Check if JSON files exist
    if os.path.exists('planner.json') or os.path.exists('daily_schedule.json'):
        return 'json'
    
    return 'sql'  # Default to SQL

def migrate_if_needed():
    """
    Check if migration from JSON to SQL is needed and perform it.
    """
    data_source = check_data_source()
    
    if data_source == 'json':
        print("JSON files detected. Consider running migration to SQL.")
        # Could auto-migrate here if desired
    else:
        print("Using SQL database for schedule data.")

if __name__ == "__main__":
    # Test compatibility functions
    print("Checking data source...")
    source = check_data_source()
    print(f"Data source: {source}")
    
    if source == 'sql':
        print("\nCreating JSON backups for compatibility...")
        ensure_json_compatibility()
    
    migrate_if_needed()