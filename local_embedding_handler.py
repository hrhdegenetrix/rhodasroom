#!/usr/bin/env python3
"""
Local embedding handler for Rhoda's memory system.
This splits the embedding generation (on GPU server) from index storage (local).
"""

import numpy as np
import faiss
import torch
import torch.nn.functional as F
import logging
import traceback

# Local index path for Rhoda's memories
INDEX_PATH = 'Memory/conversational_memory.index'

def get_embedding_from_server(text, unique_id):
    """
    First part: Get embedding from GPU server
    (This would be called on the GPU server)
    
    Returns the embedding vector without saving to index
    """
    # This is the code from the GPU server, modified to just return embedding
    # In actual use, this runs on the GPU server
    
    # Encoding (from the original function)
    embeddings = model.encode(
        [text],  # Embed single text at a time
        batch_size=12,  
        max_length=8192,
    )['dense_vecs']
    
    embeddings = torch.from_numpy(embeddings)
    embeddings = embeddings.type(torch.float32)    
    text_embedding_dim = 768  # Change this to the desired dimension size
    embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
    
    # Return the embeddings instead of adding to index
    return {'embedding': embeddings.tolist(), 'uuid': unique_id}

def add_vectors_to_index(index, embeddings, uuid, index_path):
    """
    Adds vectors and optional metadata to a Faiss index.
    (Copied from the embedding app as requested)
    """
    logger = logging.getLogger(__name__)
    
    print(f"//Index from add_vectors_to_index: {index}")
    print(f"//Embeddings from add_vectors_to_index: {embeddings}")
    print(f"//Metadata from add_vectors_to_index: {uuid}")
    
    try:
        if not isinstance(uuid, np.ndarray):
            uuid = np.array([uuid])
        index.add_with_ids(embeddings, uuid)  # Metadata could be your JSON IDs
    except Exception as e:
        logger.error(f"Error at add_with_ids: {e}", exc_info=True)
        traceback.print_exc()
        raise e
    
    try:    
        faiss.write_index(index, index_path)
    except Exception as e:
        logger.error(f"Error at write_index: {e}", exc_info=True)
        traceback.print_exc()
        raise e

def load_faiss_index(index_path):
    """
    Load existing FAISS index or create a new one
    """
    import os
    
    if os.path.exists(index_path):
        # Load existing index
        index = faiss.read_index(index_path)
        print(f"Loaded existing index from {index_path}")
    else:
        # Create new index
        text_embedding_dim = 768
        index = faiss.IndexFlatL2(text_embedding_dim)
        index = faiss.IndexIDMap(index)
        print(f"Created new index at {index_path}")
    
    return index

def store_embedding_locally(embedding_data):
    """
    Second part: Store embedding in local index
    (This runs on Rhoda's local machine)
    
    Takes the embedding returned from the server and stores it locally
    """
    embeddings = np.array(embedding_data['embedding'], dtype='float32')
    
    # Handle nested list structure from server
    if embeddings.ndim == 2 and embeddings.shape[0] == 1:
        embeddings = embeddings.reshape(1, -1)  # Ensure proper shape for FAISS
    elif embeddings.ndim == 1:
        embeddings = embeddings.reshape(1, -1)  # Convert 1D to 2D for FAISS
    
    uuid_str = embedding_data['uuid']
    
    # Convert string UUID to integer for FAISS
    # Use the numeric UUID directly if it's already numeric, otherwise generate one
    try:
        uuid = int(uuid_str)
    except (ValueError, TypeError):
        # For non-numeric UUIDs, we shouldn't store them in the index
        print(f"Warning: Non-numeric UUID {uuid_str} cannot be stored in FAISS index")
        return False
    
    # Load the local index
    index = load_faiss_index(INDEX_PATH)
    
    # Add the embedding to the local index
    add_vectors_to_index(index, embeddings, uuid, INDEX_PATH)
    
    print(f"Stored embedding for UUID {uuid} in local index")
    return True

def search_index(index, query_vector, k=5):
    """
    Search the FAISS index for k nearest neighbors
    """
    distances, indices = index.search(query_vector, k)
    return distances, indices

def search_local_index(embedding_data, k=5):
    """
    Second part of search: Use embedding to search local index
    (This runs on Rhoda's local machine)
    
    Takes the embedding returned from the server and searches the local index
    """
    import os
    import json
    
    # Convert embedding to numpy array
    query_vector = np.array(embedding_data['embedding'], dtype='float32')
    
    # Handle nested list structure from server
    if query_vector.ndim == 2 and query_vector.shape[0] == 1:
        query_vector = query_vector  # Already in correct shape for FAISS search
    elif query_vector.ndim == 1:
        query_vector = query_vector.reshape(1, -1)  # Convert 1D to 2D for FAISS
    elif query_vector.ndim == 2 and query_vector.shape[1] == 1:
        # If it's [[val], [val], ...] reshape to [1, 768]
        query_vector = query_vector.flatten().reshape(1, -1)
    
    # Load the local index
    index = load_faiss_index(INDEX_PATH)
    print(f'//Index: {index}')
    
    # Search the index
    distances, uuids = search_index(index, query_vector, k)
    print(f"//Distances: {distances}\n//uuids: {uuids}")
    
    # Fetch the JSON data for each UUID
    results = []
    for uuid in uuids[0]:  # uuids is a 2D array, we need the first row
        if uuid == -1:
            # -1 indicates no match found
            continue
        json_path = f'Memory/JSONs/{uuid}.json'  # Use cross-platform path format
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as json_file:
                data = json.load(json_file)
                results.append(data)
        else:
            print(f"JSON for UUID {uuid} not found.")
    
    return results if results else []

# Example usage for the complete flow:
# 
# FOR UPSERT:
# 1. On GPU server: embedding_data = get_embedding_from_server(text, unique_id)
# 2. Send embedding_data back to local machine
# 3. On local machine: store_embedding_locally(embedding_data)
#
# FOR SEARCH:
# 1. On GPU server: embedding_data = get_embedding_from_server(search_text, 'search_query')
# 2. Send embedding_data back to local machine
# 3. On local machine: results = search_local_index(embedding_data, k=5)