#!/usr/bin/env python3
"""
Migration script to convert JSON-based schedule data to SQL.
This script reads planner.json and daily_schedule.json and inserts the data into SQL tables.
"""

import json
import database
from datetime import datetime

def migrate_planner_events():
    """Migrate planner.json events to SQL"""
    try:
        with open('planner.json', 'r') as f:
            planner_data = json.load(f)
        
        events = planner_data.get('schedule', [])
        migrated_count = 0
        
        for event in events:
            # Prepare event data for SQL
            event_data = {
                'date': event.get('date'),
                'time': event.get('time'),
                'event_name': event.get('event_name'),
                'event_notes': event.get('event_notes', ''),
                'special_occasion': event.get('special_occasion', False),
                'location': event.get('location', ''),
            }
            
            # Add optional fields
            if 'event_end' in event:
                event_data['event_end'] = event['event_end']
            
            if 'people_involved' in event:
                event_data['people_involved'] = event['people_involved']
            
            # Insert into database
            event_id = database.add_planner_event(event_data)
            if event_id:
                migrated_count += 1
                print(f"Migrated event: {event['event_name']} on {event['date']}")
        
        print(f"Successfully migrated {migrated_count} planner events")
        return migrated_count
    
    except FileNotFoundError:
        print("planner.json not found - skipping planner migration")
        return 0
    except Exception as e:
        print(f"Error migrating planner events: {e}")
        return 0

def migrate_daily_schedule():
    """Migrate daily_schedule.json events to SQL"""
    try:
        with open('daily_schedule.json', 'r') as f:
            daily_data = json.load(f)
        
        migrated_count = 0
        
        for day_of_week, events in daily_data.items():
            for event in events:
                # Prepare event data for SQL
                event_data = {
                    'day_of_week': day_of_week,
                    'event_name': event.get('event_name'),
                    'event_notes': event.get('event_notes', ''),
                    'start_time': event.get('start_time'),
                    'location': event.get('location', ''),
                }
                
                # Add optional fields
                if 'event_end' in event:
                    event_data['event_end'] = event['event_end']
                
                # Insert into database
                event_id = database.add_daily_event(event_data)
                if event_id:
                    migrated_count += 1
                    print(f"Migrated daily event: {event['event_name']} on {day_of_week}")
        
        print(f"Successfully migrated {migrated_count} daily schedule events")
        return migrated_count
    
    except FileNotFoundError:
        print("daily_schedule.json not found - skipping daily schedule migration")
        return 0
    except Exception as e:
        print(f"Error migrating daily schedule: {e}")
        return 0

def verify_migration():
    """Verify that the migration was successful"""
    print("\nVerifying migration...")
    
    # Check planner events
    planner_events = database.get_planner_events()
    print(f"Total planner events in database: {len(planner_events)}")
    
    # Check daily schedule
    daily_events = database.get_daily_schedule()
    print(f"Total daily schedule events in database: {len(daily_events)}")
    
    # Show a sample of migrated data
    if planner_events:
        print("\nSample planner event:")
        event = planner_events[0]
        print(f"  - {event['event_name']} on {event['date']} at {event['time']}")
    
    if daily_events:
        print("\nSample daily event:")
        event = daily_events[0]
        print(f"  - {event['event_name']} on {event['day_of_week']} at {event['start_time']}")

def main():
    """Main migration function"""
    print("Starting schedule data migration to SQL...")
    print("=" * 50)
    
    # Migrate planner events
    print("\nMigrating planner events...")
    planner_count = migrate_planner_events()
    
    # Migrate daily schedule
    print("\nMigrating daily schedule...")
    daily_count = migrate_daily_schedule()
    
    # Verify migration
    verify_migration()
    
    print("\n" + "=" * 50)
    print("Migration complete!")
    print(f"Total events migrated: {planner_count + daily_count}")

if __name__ == "__main__":
    main()