#!/usr/bin/env python3
"""
Migration script to convert lorebook knowledgebase data to SQL.
This script reads .lorebook files and inserts the data into SQL tables.
"""

import json
import database
import os
from datetime import datetime

def migrate_lorebook_to_sql(persona="Rhoda"):
    """Migrate a lorebook file to SQL database"""
    file_path = f"{persona}_knowledgebase.lorebook"
    
    if not os.path.exists(file_path):
        print(f"Lorebook file not found: {file_path}")
        return 0, 0
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lorebook_data = json.load(f)
        
        categories_migrated = 0
        entries_migrated = 0
        
        # Migrate categories
        categories = lorebook_data.get('categories', [])
        category_map = {}  # Map old IDs to ensure consistency
        
        for idx, category in enumerate(categories):
            category_data = {
                'id': category.get('id'),
                'name': category.get('name', f'Category {idx+1}'),
                'enabled': category.get('enabled', True),
                'create_subcontext': category.get('createSubcontext', False),
                'order_index': idx
            }
            
            # Add subcontext settings if present
            if 'subcontextSettings' in category:
                category_data['subcontext_settings'] = category['subcontextSettings']
            
            # Store in database
            database.add_kb_category(category_data)
            category_map[category['id']] = category['id']
            categories_migrated += 1
            print(f"Migrated category: {category_data['name']}")
        
        # Migrate entries
        entries = lorebook_data.get('entries', [])
        
        for entry in entries:
            # Prepare entry data for SQL
            entry_data = {
                'id': entry.get('id'),
                'display_name': entry.get('displayName', 'Unnamed Entry'),
                'text_content': entry.get('text', ''),
                'keys': entry.get('keys', []),
                'enabled': entry.get('enabled', True),
                'force_activation': entry.get('forceActivation', False),
                'key_relative': entry.get('keyRelative', False),
                'non_story_activatable': entry.get('nonStoryActivatable', False),
                'search_range': entry.get('searchRange', 1000),
                'last_updated_at': entry.get('lastUpdatedAt', int(datetime.now().timestamp() * 1000))
            }
            
            # Map category if present
            if 'category' in entry and entry['category']:
                entry_data['category_id'] = category_map.get(entry['category'], entry['category'])
            
            # Handle context config
            if 'contextConfig' in entry:
                context_config = entry['contextConfig']
                entry_data['token_budget'] = context_config.get('tokenBudget', 250)
                entry_data['budget_priority'] = context_config.get('budgetPriority', 400)
                entry_data['context_config'] = context_config
            
            # Handle lore bias groups
            if 'loreBiasGroups' in entry:
                entry_data['lore_bias_groups'] = entry['loreBiasGroups']
            
            # Insert into database
            result = database.add_kb_entry(entry_data)
            if result:
                entries_migrated += 1
                print(f"Migrated entry: {entry_data['display_name']}")
        
        print(f"\nSuccessfully migrated {categories_migrated} categories and {entries_migrated} entries for {persona}")
        return categories_migrated, entries_migrated
    
    except Exception as e:
        print(f"Error migrating lorebook: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0

def verify_migration(persona="Rhoda"):
    """Verify that the migration was successful"""
    print(f"\nVerifying migration for {persona}...")
    
    # Check categories
    categories = database.get_kb_categories(enabled_only=False)
    print(f"Total categories in database: {len(categories)}")
    
    # Check entries
    entries = database.get_kb_entries(enabled_only=False)
    print(f"Total knowledgebase entries in database: {len(entries)}")
    
    # Check force activation entries
    force_entries = database.get_kb_entries(force_activation=True)
    print(f"Force activation entries: {len(force_entries)}")
    
    # Show sample data
    if categories:
        print("\nSample category:")
        cat = categories[0]
        print(f"  - {cat['name']} (ID: {cat['id'][:8]}..., Enabled: {cat['enabled']})")
    
    if entries:
        print("\nSample entries:")
        for entry in entries[:3]:
            keys_str = ', '.join(entry.get('keys', []))[:50]
            print(f"  - {entry['display_name']} (Keys: {keys_str}...)")

def main():
    """Main migration function"""
    print("Starting knowledgebase migration to SQL...")
    print("=" * 50)
    
    # Migrate Rhoda's knowledgebase
    print("\nMigrating Rhoda's knowledgebase...")
    rhoda_cats, rhoda_entries = migrate_lorebook_to_sql("Rhoda")
    
    # Check if Harry's knowledgebase exists and migrate it
    if os.path.exists("Harry_knowledgebase.lorebook"):
        print("\nMigrating Harry's knowledgebase...")
        harry_cats, harry_entries = migrate_lorebook_to_sql("Harry")
    else:
        print("\nHarry's knowledgebase not found, skipping...")
        harry_cats, harry_entries = 0, 0
    
    # Verify migration
    verify_migration()
    
    print("\n" + "=" * 50)
    print("Migration complete!")
    print(f"Total categories migrated: {rhoda_cats + harry_cats}")
    print(f"Total entries migrated: {rhoda_entries + harry_entries}")

if __name__ == "__main__":
    main()