import subprocess
import json
import os
import sys
import threading
import atexit
import time
import signal
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import wraps
import weakref

# Global variables for process management
_process_pool = None
_thread_pool = None
_shutdown_flag = threading.Event()
_pool_lock = threading.Lock()
_main_thread_id = threading.get_ident()
_shutdown_callbacks = []

# Track if we're in the main thread
def _is_main_thread():
    """Check if we're running in the main thread"""
    return threading.get_ident() == _main_thread_id

def _detect_shutdown():
    """Multiple ways to detect if we're shutting down"""
    # Check our flag first
    if _shutdown_flag.is_set():
        return True
    
    # Check if the main thread is still alive
    try:
        main_thread = threading.main_thread()
        if not main_thread.is_alive():
            return True
    except:
        return True
    
    # Check interpreter state
    try:
        if hasattr(sys, 'is_finalizing') and sys.is_finalizing():
            return True
    except:
        pass
    
    return False

def _signal_handler(signum, frame):
    """Handle shutdown signals"""
    _shutdown_flag.set()
    _cleanup_resources()

def _cleanup_resources():
    """Cleanup function to be called at exit"""
    global _process_pool, _thread_pool
    _shutdown_flag.set()
    
    # Run shutdown callbacks
    for callback in _shutdown_callbacks:
        try:
            callback()
        except:
            pass  # Ignore callback errors
    
    # Cleanup pools
    if _process_pool:
        try:
            _process_pool.shutdown(wait=False, cancel_futures=True)
        except:
            pass
        _process_pool = None
    
    if _thread_pool:
        try:
            _thread_pool.shutdown(wait=False, cancel_futures=True)
        except:
            pass
        _thread_pool = None

# Register cleanup and signal handlers
atexit.register(_cleanup_resources)
try:
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
except (ValueError, OSError):
    # Might not be available on all platforms or in all contexts
    pass

def _get_process_pool():
    """Get or create the process pool safely"""
    global _process_pool
    
    if _detect_shutdown():
        return None
        
    with _pool_lock:
        if _process_pool is None and not _detect_shutdown():
            try:
                _process_pool = ProcessPoolExecutor(max_workers=2)
            except:
                return None
        return _process_pool

def _get_thread_pool():
    """Get or create the thread pool safely"""
    global _thread_pool
    
    if _detect_shutdown():
        return None
        
    with _pool_lock:
        if _thread_pool is None and not _detect_shutdown():
            try:
                _thread_pool = ThreadPoolExecutor(max_workers=3)
            except:
                return None
        return _thread_pool

def _handle_shutdown_gracefully(func):
    """Decorator to handle shutdown gracefully"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _detect_shutdown():
            # Return appropriate empty result based on function type
            function_type = args[1] if len(args) > 1 else kwargs.get('function_type', '')
            return [] if function_type not in ['extract_all', 'combined_context'] else {}
        
        try:
            return func(*args, **kwargs)
        except (RuntimeError, OSError, subprocess.SubprocessError) as e:
            error_msg = str(e).lower()
            if any(keyword in error_msg for keyword in [
                "can't create new thread", 
                "interpreter shutdown",
                "no such file or directory",
                "access denied",
                "resource temporarily unavailable"
            ]):
                # Gracefully handle shutdown/resource scenarios
                function_type = args[1] if len(args) > 1 else kwargs.get('function_type', '')
                return [] if function_type not in ['extract_all', 'combined_context'] else {}
            raise
    return wrapper

def _run_node_script_direct(text, function_type):
    """Run the Node.js script directly without pools"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    js_path = os.path.join(script_dir, 'to_past_tense.js')
    
    if not os.path.exists(js_path):
        return None
    
    try:
        # Use a simpler approach that's less likely to fail during shutdown
        process = subprocess.Popen(
            ['node', js_path, function_type], 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            # Prevent subprocess from inheriting handles that might cause issues
            close_fds=True if os.name != 'nt' else False
        )
        
        stdout, stderr = process.communicate(input=text.encode('utf-8'), timeout=10)
        
        if process.returncode != 0:
            return None
            
        result = stdout.decode('utf-8').strip()
        if not result:
            return None
            
        return json.loads(result)
        
    except Exception:
        return None

def _run_node_script_threaded(text, function_type):
    """Run the Node.js script in a thread pool"""
    try:
        pool = _get_thread_pool()
        if pool and not _detect_shutdown():
            future = pool.submit(_run_node_script_direct, text, function_type)
            return future.result(timeout=15)
    except Exception:
        pass
    return None

def _run_node_script_processed(text, function_type):
    """Run the Node.js script in a process pool"""
    try:
        pool = _get_process_pool()
        if pool and not _detect_shutdown():
            future = pool.submit(_run_node_script_direct, text, function_type)
            return future.result(timeout=15)
    except Exception:
        pass
    return None

@_handle_shutdown_gracefully
def run_compromise(text, function_type):
    """
    Run a compromise.js function on the given text with multiple fallback strategies
    
    Args:
        text (str): The text to process
        function_type (str): The compromise function to run
        
    Returns:
        The result from compromise, or empty list/dict on error
    """
    if not text or not text.strip():
        return [] if function_type not in ['extract_all', 'combined_context'] else {}
    
    # Early shutdown detection
    if _detect_shutdown():
        return [] if function_type not in ['extract_all', 'combined_context'] else {}
    
    # Strategy 1: Try process pool (most isolated)
    if not _detect_shutdown():
        try:
            result = _run_node_script_processed(text, function_type)
            if result is not None:
                return result
        except Exception:
            pass
    
    # Strategy 2: Try thread pool (moderate isolation)
    if not _detect_shutdown():
        try:
            result = _run_node_script_threaded(text, function_type)
            if result is not None:
                return result
        except Exception:
            pass
    
    # Strategy 3: Direct execution (least isolation, but most likely to work)
    if not _detect_shutdown():
        try:
            result = _run_node_script_direct(text, function_type)
            if result is not None:
                return result
        except Exception:
            pass
    
    # All strategies failed or we're shutting down
    return [] if function_type not in ['extract_all', 'combined_context'] else {}

# Add a function to register shutdown callbacks
def register_shutdown_callback(callback):
    """Register a callback to be called during shutdown"""
    _shutdown_callbacks.append(callback)

# Add a function to check if we're shutting down (for external use)
def is_shutting_down():
    """Check if the system is shutting down"""
    return _detect_shutdown()

def ensure_unique(arr):
    """
    Utility function to deduplicate a list while preserving order
    
    Args:
        arr (list): The list to deduplicate
        
    Returns:
        list: Deduplicated list with order preserved
    """
    seen = set()
    return [x for x in arr if not (x in seen or seen.add(x))]

def safe_join(items, separator="\n"):
    """
    Safely join a list of items into a string, handling non-string items
    
    Args:
        items: The items to join (list, str, or other)
        separator: The separator to use (default: newline)
        
    Returns:
        str: Joined string or empty string on error
    """
    # If it's already a string, return it directly
    if isinstance(items, str):
        return items
        
    # If it's a list of strings, join them
    if isinstance(items, list):
        # Convert all items to strings
        str_items = [str(item) if item is not None else "" for item in items]
        return separator.join(str_items)
        
    # If it's None, return empty string
    if items is None:
        return ""
        
    # For any other type, convert to string
    return str(items)

def to_past_tense(text):
    """Convert text to past tense"""
    return run_compromise(text, 'past_tense')

def extract_people(text):
    """Extract people's names from text (returns deduplicated list)"""
    return run_compromise(text, 'people')

def extract_phone_numbers(text):
    """Extract phone numbers from text (returns deduplicated list)"""
    return run_compromise(text, 'phone_numbers')

def extract_locations(text):
    """Extract location names from text (returns deduplicated list)"""
    return run_compromise(text, 'locations')

def extract_dates(text):
    """Extract dates from text"""
    return run_compromise(text, 'dates')

def extract_times(text):
    """Extract times from text"""
    return run_compromise(text, 'times')

def extract_nouns(text):
    """Extract nouns from text (returns deduplicated list)"""
    return run_compromise(text, 'nouns')

def extract_verbs(text):
    """Extract verbs from text (returns deduplicated list)"""
    return run_compromise(text, 'verbs')

def extract_unique_words(text):
    """Extract potentially unique or rare words from text"""
    return run_compromise(text, 'unique_words')

def extract_all(text):
    """Extract multiple types of information at once for efficiency (all lists are deduplicated)"""
    return run_compromise(text, 'extract_all')

def combined_context(text):
    """
    Extract entities with context and return both formatted strings and raw data
    
    Returns a dictionary with two keys:
    - context: Contains pre-formatted strings ready for display/use
    - raw: Contains the raw extracted data for programmatic use
    """
    return run_compromise(text, 'combined_context')

def process_location_memories(location_conglomerate, memory_flow_function):
    """
    Process location memories safely, preventing TypeError when joining strings
    
    Args:
        location_conglomerate: List of locations or single string
        memory_flow_function: Function to process each location
        
    Returns:
        Processed location memories as a string
    """
    # If it's a string, process it directly
    if isinstance(location_conglomerate, str):
        return memory_flow_function(location_conglomerate)
        
    # If it's a list, process each item
    if isinstance(location_conglomerate, list):
        if not location_conglomerate:  # Handle empty list
            return ""
            
        # Process each location individually
        location_memories = []
        for location in location_conglomerate:
            result = memory_flow_function(location)
            # Make sure each result is a string
            location_memories.append(str(result) if result is not None else "")
            
        # Join the results, ensuring they're all strings
        return "\n".join(location_memories)
        
    # If it's None or something else, return empty string
    return ""

# Example usage
if __name__=="__main__":
    test_text = "Duane has invited Maggie and me to attend a few Oregon Shakespeare Festival openings with him this weekend so we could see plays like Fat Ham and The Importance of Being Ernest, plus the usual charity shopping and Mass! Today will be a particularly busy day, as we will have two plays; one at about 1:30, and another in the evening. Luckily, Maggie and I live about a block away from OSF, so we can retreat to our little haven and take a nap after the first play, if needed."
    
    print("Original text:", test_text)
    print("\nRunning tests on individual functions:")
    
    # Test individual functions
    print("\n1. Testing Past tense conversion:")
    past_tense = to_past_tense(test_text)
    print("Past tense:", past_tense)
    
    print("\n2. Testing People extraction (deduplicated):")
    people = extract_people(test_text)
    print("People:", people)
    
    print("\n3. Testing Location extraction (deduplicated):")
    locations = extract_locations(test_text)
    print("Locations:", locations)
    
    print("\n4. Testing Noun extraction (deduplicated):")
    nouns = extract_nouns(test_text)
    print("Nouns:", nouns)
    
    print("\n5. Testing Verb extraction (deduplicated):")
    verbs = extract_verbs(test_text)
    print("Verbs:", verbs)
    
    print("\n6. Testing Unique word extraction:")
    unique_words = extract_unique_words(test_text)
    print("Unique words:", unique_words)
    
    print("\n7. Testing Combined Context extraction:")
    context_data = combined_context(test_text)
    print("Formatted context data:")
    for key, value in context_data['context'].items():
        print(f"  {key}: {value}")
        
    print("\n8. Testing All-in-one extraction (all lists deduplicated):")
    all_data = extract_all(test_text)
    print("All extracted data:")
    for key, value in all_data.items():
        print(f"  {key}: {value}")
        
    print("\n9. Testing safe_join function:")
    # Test with a list of strings
    test_list = ["apple", "banana", "cherry"]
    print(f"  safe_join({test_list}): {safe_join(test_list, ', ')}")
    
    # Test with a list containing a non-string
    test_list_mixed = ["apple", 123, None, ["nested"]]
    print(f"  safe_join(mixed list): {safe_join(test_list_mixed, ', ')}")
    
    # Test with None
    print(f"  safe_join(None): {safe_join(None)}")
    
    # Test with a string
    print(f"  safe_join('hello'): {safe_join('hello')}")
    
    print("\n10. Testing process_location_memories function:")
    # Mock memory flow function
    def mock_memory_flow(text):
        return f"Processed: {text}"
        
    # Test with a list
    test_locations = ["New York", "Los Angeles", "Chicago"]
    print(f"  process_location_memories(list): {process_location_memories(test_locations, mock_memory_flow)}")
    
    # Test with a string
    print(f"  process_location_memories(str): {process_location_memories('Boston', mock_memory_flow)}")
    
    # Test with an empty list
    print(f"  process_location_memories([]): {process_location_memories([], mock_memory_flow)}")
    
    # Test with None
    print(f"  process_location_memories(None): {process_location_memories(None, mock_memory_flow)}")