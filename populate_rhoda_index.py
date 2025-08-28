#!/usr/bin/env python3
"""
Script to populate Rhoda's local index with existing memories from JSON files.
This will help establish her initial memory base.
"""

import os
import json
import asyncio
import aiohttp
import sys

sys.path.insert(0, '/mnt/v/Work/Anthropic_Interview')
import local_embedding_handler

async def populate_index_from_json_files():
    """Populate the local index with existing JSON memories"""
    
    json_dir = 'Memory/JSONs'
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print("=" * 60)
    print("POPULATING RHODA'S MEMORY INDEX")
    print("=" * 60)
    
    # Get list of JSON files
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json')]
    print(f"Found {len(json_files)} JSON memory files")
    print("-" * 60)
    
    for json_file in json_files:
        json_path = os.path.join(json_dir, json_file)
        uuid_str = json_file.replace('.json', '')
        
        try:
            # Check if UUID is numeric (required for FAISS)
            uuid = int(uuid_str)
            
            # Load the JSON content
            with open(json_path, 'r', encoding='utf-8') as f:
                memory_data = json.load(f)
            
            # Get the text to embed (usually the 'message' field)
            text = memory_data.get('message', '')
            if not text:
                print(f"⚠️  Skipping {uuid_str}: No message content")
                skip_count += 1
                continue
            
            # Get embedding from the server
            url = 'http://100.121.217.56:5001/pureembed'
            data = {
                'text': text,
                'uuid': uuid_str
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        embedding_data = await response.json()
                        
                        # Store in local index
                        success = local_embedding_handler.store_embedding_locally(embedding_data)
                        if success:
                            print(f"✓ Added {uuid_str}: {text[:50]}...")
                            success_count += 1
                        else:
                            print(f"✗ Failed to store {uuid_str}")
                            error_count += 1
                    else:
                        print(f"✗ Failed to get embedding for {uuid_str}")
                        error_count += 1
                        
        except ValueError:
            print(f"⚠️  Skipping {uuid_str}: Non-numeric UUID")
            skip_count += 1
        except Exception as e:
            print(f"✗ Error processing {uuid_str}: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print("POPULATION COMPLETE")
    print("=" * 60)
    print(f"✓ Successfully added: {success_count} memories")
    print(f"⚠️  Skipped: {skip_count} files")
    print(f"✗ Errors: {error_count} files")
    
    if success_count > 0:
        print("\n🎉 Rhoda's memory index has been populated!")
        print("She should now be able to search her memories.")
    else:
        print("\n⚠️  No memories were added to the index.")
        print("Please check the errors above.")

if __name__ == "__main__":
    print("\nThis script will populate Rhoda's local memory index.")
    print("It will process existing JSON memory files and create embeddings.")
    response = input("\nDo you want to proceed? (y/n): ")
    
    if response.lower() == 'y':
        asyncio.run(populate_index_from_json_files())
    else:
        print("Population cancelled.")