#!/usr/bin/env python3
"""
Compatibility layer for knowledgebase system.
This ensures backward compatibility while transitioning from lorebook JSON to SQL.
"""

import json
import os
import database
from datetime import datetime

def ensure_lorebook_compatibility(persona="Rhoda"):
    """
    Create lorebook JSON file from SQL data for backward compatibility.
    This function can be called periodically to sync SQL data to lorebook files.
    """
    
    file_path = f"{persona}_knowledgebase.lorebook"
    
    try:
        # Get data from SQL
        categories = database.get_kb_categories(enabled_only=False)
        entries = database.get_kb_entries(enabled_only=False)
        
        # Build lorebook structure
        lorebook = {
            "categories": [],
            "entries": []
        }
        
        # Convert categories to lorebook format
        for category in categories:
            lorebook_cat = {
                "id": category['id'],
                "name": category['name'],
                "enabled": bool(category['enabled']),
                "createSubcontext": bool(category.get('create_subcontext', False)),
                "order": category.get('order_index', 0),
                "categoryBiasGroups": [{
                    "bias": 0,
                    "enabled": True,
                    "ensureSequenceFinish": False,
                    "generateOnce": True,
                    "phrases": [],
                    "whenInactive": False
                }]
            }
            
            # Add subcontext settings if present
            if category.get('subcontext_settings'):
                if isinstance(category['subcontext_settings'], str):
                    import json as json_module
                    try:
                        lorebook_cat['subcontextSettings'] = json_module.loads(category['subcontext_settings'])
                    except:
                        pass
                else:
                    lorebook_cat['subcontextSettings'] = category['subcontext_settings']
            
            # Add default category settings
            lorebook_cat['categoryDefaults'] = {
                "category": "",
                "contextConfig": {
                    "budgetPriority": 400,
                    "insertionPosition": -1,
                    "insertionType": "newline",
                    "maximumTrimType": "sentence",
                    "prefix": "",
                    "reservedTokens": 0,
                    "suffix": "\n",
                    "tokenBudget": 1,
                    "trimDirection": "trimBottom"
                },
                "displayName": "New Lorebook Entry",
                "enabled": True,
                "forceActivation": False,
                "id": "",
                "keyRelative": False,
                "keys": [],
                "lastUpdatedAt": int(datetime.now().timestamp() * 1000),
                "loreBiasGroups": [{
                    "bias": 0,
                    "enabled": True,
                    "ensureSequenceFinish": False,
                    "generateOnce": True,
                    "phrases": [],
                    "whenInactive": False
                }],
                "nonStoryActivatable": False,
                "searchRange": 1000,
                "text": ""
            }
            
            lorebook["categories"].append(lorebook_cat)
        
        # Convert entries to lorebook format
        for entry in entries:
            # Parse JSON fields
            keys = entry.get('keys', [])
            if isinstance(keys, str):
                import json as json_module
                try:
                    keys = json_module.loads(keys)
                except:
                    keys = []
            
            context_config = entry.get('context_config')
            if isinstance(context_config, str):
                import json as json_module
                try:
                    context_config = json_module.loads(context_config)
                except:
                    context_config = {}
            elif not context_config:
                context_config = {}
            
            # Merge with defaults if needed
            if not context_config:
                context_config = {
                    "prefix": "",
                    "suffix": "\n",
                    "tokenBudget": entry.get('token_budget', 250),
                    "reservedTokens": 0,
                    "budgetPriority": entry.get('budget_priority', 400),
                    "trimDirection": "trimBottom",
                    "insertionType": "newline",
                    "maximumTrimType": "sentence",
                    "insertionPosition": -1
                }
            
            lore_bias = entry.get('lore_bias_groups')
            if isinstance(lore_bias, str):
                import json as json_module
                try:
                    lore_bias = json_module.loads(lore_bias)
                except:
                    lore_bias = []
            elif not lore_bias:
                lore_bias = [{
                    "phrases": [],
                    "ensureSequenceFinish": False,
                    "generateOnce": True,
                    "bias": 0,
                    "enabled": True,
                    "whenInactive": False
                }]
            
            lorebook_entry = {
                "text": entry.get('text_content', ''),
                "contextConfig": context_config,
                "lastUpdatedAt": entry.get('last_updated_at', int(datetime.now().timestamp() * 1000)),
                "displayName": entry.get('display_name', ''),
                "id": entry.get('id', ''),
                "keys": keys,
                "searchRange": entry.get('search_range', 1000),
                "enabled": bool(entry.get('enabled', True)),
                "forceActivation": bool(entry.get('force_activation', False)),
                "keyRelative": bool(entry.get('key_relative', False)),
                "nonStoryActivatable": bool(entry.get('non_story_activatable', False)),
                "category": entry.get('category_id', ''),
                "loreBiasGroups": lore_bias
            }
            
            lorebook["entries"].append(lorebook_entry)
        
        # Write to lorebook file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lorebook, f, indent=2, ensure_ascii=False)
        
        print(f"Synced {len(categories)} categories and {len(entries)} entries to {file_path}")
        return True
    
    except Exception as e:
        print(f"Error syncing lorebook: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_data_source():
    """
    Check if we should use SQL or lorebook JSON as the data source.
    Returns 'sql' if database tables exist and have data, otherwise 'lorebook'.
    """
    try:
        # Check if we have data in SQL tables
        categories = database.get_kb_categories(enabled_only=False)
        entries = database.get_kb_entries(enabled_only=False)
        
        if categories or entries:
            return 'sql'
    except:
        pass
    
    # Check if lorebook files exist
    if os.path.exists('Rhoda_knowledgebase.lorebook'):
        return 'lorebook'
    
    return 'sql'  # Default to SQL

def migrate_if_needed():
    """
    Check if migration from lorebook to SQL is needed and perform it.
    """
    data_source = check_data_source()
    
    if data_source == 'lorebook':
        print("Lorebook files detected. Consider running migration to SQL.")
    else:
        print("Using SQL database for knowledgebase data.")

if __name__ == "__main__":
    # Test compatibility functions
    print("Checking data source...")
    source = check_data_source()
    print(f"Data source: {source}")
    
    if source == 'sql':
        print("\nCreating lorebook backup for compatibility...")
        ensure_lorebook_compatibility("Rhoda")
        
        # Check if Harry exists
        if os.path.exists("Harry_knowledgebase.lorebook.migration_backup"):
            print("\nCreating Harry's lorebook backup...")
            ensure_lorebook_compatibility("Harry")
    
    migrate_if_needed()