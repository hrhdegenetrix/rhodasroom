import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModel, AutoConfig
from flask import Flask, request, jsonify, send_file
import faiss
import numpy as np
import json
from datetime import datetime
from uuid import uuid4
from FlagEmbedding import BGEM3FlagModel

app = Flask(__name__)

directory_path="D:\\Models\\Models\\Cache\\models--BAAI--bge-m3\\snapshots\\50f9396f75618b3389c1fd1068a1ff58dc7b5b26"
print(f"Directory path loaded!")

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
# Model loading from local directory

model_path = directory_path  # Adjust if your structure differs
model = BGEM3FlagModel(model_path, use_fp16=True)

import random

def generate_random_id():
    # Generate a random integer with 12 digits (you can adjust the number of digits as needed)
    random_part = random.randint(10**3, 10**4 - 1)
   
    # Get the current date in the format 'MM_DD_YYYY'
    date_part = datetime.now().strftime('%m%d%Y%H%M%S')
   
    # Combine the random integer and the date
    random_id = f"{random_part}{date_part}"
   
    return random_id

def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)

dimension=768

def create_faiss_index(dimension, index_name):
    """Creates a new Faiss index and saves it to disk."""
    base_index = faiss.IndexFlatL2(dimension)  # Most common index type for embeddings
    index = faiss.IndexIDMap(base_index)
    index_path = f"{index_name}.index"
    faiss.write_index(index, index_path) 
    return index_path

def load_faiss_index(index_path):
    """Loads an existing Faiss index from disk."""
    return faiss.read_index(index_path)

import logging
import traceback

def add_vectors_to_index(index, embeddings, uuid, index_path):
        """Adds vectors and optional metadata to a Faiss index."""
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

def search_index(index, query_vector, k=5):
    print(f"//index at start of search_index: {index}")
    print(f"//query vector at start of `search_index`: {query_vector}")
    query_vector = query_vector.astype('float32')
    try:
        result = index.search(query_vector, k)  # Ensure dtype is float32
        print(f"//Result from index.search: {result}")
        distances, indices = result
        return distances.flatten().tolist(), indices.flatten().tolist()
    except Exception as e:
        print(f"Error in search_index: {e}")
        print(f"Result type: {type(result)} - Result value: {result}")
        return [], []

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

@app.route('/pureembed', methods=['POST'])
def get_embedding():
    try:
        # Get data from the request
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']
        
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        
        # Return the embeddings as JSON response
        return jsonify({'embedding': embeddings.tolist(), 'uuid': unique_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\conversational_memory.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'Z:/MigratedChatMemory/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/testsearch', methods=['POST'])
def test_search():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\test_memory.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'TestMemory/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/notesearch', methods=['POST'])
def search_notes_index():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\notes_index.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'Z:/Notes/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/booksearch', methods=['POST'])
def search_book_text():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\literary_memory.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'Z:/MigratedBookMemory/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/journalsearch', methods=['POST'])
def search_journal_text():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\journal_index.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'Z:/JournalEntries/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/naisearch', methods=['POST'])
def search_nai_text():
    try:
        data = request.get_json(force=True)
        print(f"Data received!")
        text = data['text']
        print(f"Text extracted!")
       
        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        query_vector = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        print(f"//Query Vector: {query_vector}")
        index = load_faiss_index('Z:\\novelai_memory.index')
        print(f'//Index: {index}')
        distances, uuids = search_index(index, query_vector)  # Now capturing distances as well, even if not used later
        print(f"//Distances: {distances}\n//uuids: {uuids}")
        # Fetch the JSON data for each UUID
        results = []
        for uuid in uuids:
            json_path = f'Z:/MigratedNAIMemory/{uuid}.json'
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    results.append(data)
            else:
                print(f"JSON for UUID {uuid} not found.")

        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/embed', methods=['POST'])
def embed_text():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\conversational_memory.index'
        index = load_faiss_index(index_path)

        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/bookembed', methods=['POST'])
def embed_book_text():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\literary_memory.index'
        index = load_faiss_index(index_path)
        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        save_json(f'Z:/MigratedBookMemory/{unique_id}.json', conversation_metadata)
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/testembed', methods=['POST'])
def embed_test_text():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\test_memory.index'
        index = load_faiss_index(index_path)
        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/notesembed', methods=['POST'])
def embed_notes():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\notes_index.index'
        index = load_faiss_index(index_path)
        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})


@app.route('/naiembed', methods=['POST'])
def embed_nai_text():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        text = data['text']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\novelai_memory.index'
        index = load_faiss_index(index_path)
        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/journalembed', methods=['POST'])
def embed_journal_text():
    try:
        # Data extraction (remains the same)
        data = request.get_json(force=True)
        date = data['date']
        journal_entry = data['journal_entry']
        long_term_goal = data['long_term_goal']
        sentiment = data['sentiment']
        tags = data['tags']
        unique_id = data['uuid']

        # Encoding
        embeddings = model.encode(
            [text],  # Embed single text at a time
            batch_size=12,  
            max_length=8192,
        )['dense_vecs']
        embeddings = torch.from_numpy(embeddings)
        embeddings = embeddings.type(torch.float32)    
        text_embedding_dim = 768  # Change this to the desired dimension size
        print(text_embedding_dim)
        embeddings = F.normalize(embeddings[:, :text_embedding_dim], p=2, dim=1).numpy()
        # Specify the path to your index
        index_path = 'Z:\\journal_index.index'
        index = load_faiss_index(index_path)
        # Adjusted call to add_vectors_to_index, now including index_path
        #uuid = np.array([data['uuid']], dtype='float32')  # Ensure UUID is an integer array
        add_vectors_to_index(index, embeddings, unique_id, index_path)
        print(f"Back in main program now!")
        print(f"Upserted vector!")
        # Return the embeddings as JSON
        return jsonify({'embedding': embeddings.tolist()})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/delete', methods=['POST'])
def delete_vector_by_id():
    try:
        data = request.get_json(force=True)
        unique_id = data.get('unique_id')
        index_name = data.get('index_name')
        # Convert unique_id to bytes to perform the search in the index
        unique_id_bytes = unique_id.encode('utf-8')  # ensure unique_id is converted to str

        # Load the specified Faiss index
        index_path = f"{index_name}.index"
        index = faiss.read_index(index_path)

        # Find the ID of the vector to delete
        id_to_delete = -1
        if isinstance(index.id_map, faiss.IndexIDMap):
            id_to_delete = index.id_map.search_single(unique_id_bytes)[1]
        else:
            raise RuntimeError("Unexpected id_map type in Faiss index. Expecting faiss.IndexIDMap.")

        if id_to_delete != -1:
            # Remove the vector from the index
            index.remove_ids(np.array([id_to_delete]))
            faiss.write_index(index, index_path)
            return jsonify({"success": True, "message": "Vector deleted successfully"})
        else:
            return jsonify({"success": False, "message":"Vector not found in the index."})
    except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

#=====IMAGE EMBEDDING ETC========#

from transformers import ViTFeatureExtractor, ViTModel
from PIL import Image
import numpy as np

file_path = "D:\\Models\\Models\\Cache\\models--google--vit-base-patch16-224\\snapshots\\3f49326eb077187dfe1c2a2bb15fbd74e6ab91e3"

# Initialize the feature extractor and model
feature_extractor = ViTFeatureExtractor.from_pretrained(file_path)
vit_model = ViTModel.from_pretrained(file_path)

# @app.route('/visual', methods=['POST'])
# # Function to generate embeddings
# def generate_embedding(image_path):
#     try:
#         # Data extraction (remains the same)
#         data = request.get_json(force=True)
#         image = data['image']

#         image = Image.open(image_path)
#         inputs = feature_extractor(images=image, return_tensors="pt")
#         outputs = vit_model(**inputs)
#         outputs.last_hidden_state[:,0,:].detach().numpy()

# image_path = "C:\\Users\\magda\\Downloads\\test.png"
# embedding = generate_embedding(image_path)
# print(embedding)

if __name__ == '__main__':
    #index_name = 'test_memory'
    #create_faiss_index(768, index_name)
    app.run(debug=True, host='192.168.1.5')  # Remember to remove debug=True for production
