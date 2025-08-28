import traceback
import os
import json
import inspect
import re
from datetime import datetime
from pathlib import Path

def if_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Original console output (backwards compatibility)
            print(f"An error occurred in '{func.__name__}': {e}")
            traceback.print_exc()
            
            # Generate and save comprehensive error information
            error_info = generate_error_info(func, e, args, kwargs)
            
            # Save to traditional error log
            save_to_error_log(error_info)
            
            # Generate and save debugging prompt
            debug_prompt = generate_debug_prompt(error_info)
            save_debug_prompt(debug_prompt, error_info)
            
            # Optionally, re-raise the exception if you don't want to suppress it
            # raise
    return wrapper

def generate_error_info(func, exception, args, kwargs):
    """Collect comprehensive error information"""
    tb = traceback.extract_tb(exception.__traceback__)
    
    # Get the error location
    if tb:
        error_frame = tb[-1]
        error_file = error_frame.filename
        error_line = error_frame.lineno
        error_function = error_frame.name
    else:
        error_file = inspect.getfile(func)
        error_line = "Unknown"
        error_function = func.__name__
    
    # Get source code context if possible
    code_context = []
    try:
        with open(error_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if isinstance(error_line, int) and error_line > 0:
                start = max(0, error_line - 6)
                end = min(len(lines), error_line + 5)
                for i in range(start, end):
                    prefix = ">>> " if i == error_line - 1 else "    "
                    code_context.append(f"{prefix}[{i+1:4d}]: {lines[i].rstrip()}")
    except:
        code_context = ["Could not retrieve code context"]
    
    # Get module information
    module = inspect.getmodule(func)
    module_name = module.__name__ if module else "Unknown"
    module_file = module.__file__ if module else "Unknown"
    
    # Format arguments
    formatted_args = []
    for i, arg in enumerate(args):
        try:
            arg_str = repr(arg)
            if len(arg_str) > 200:
                arg_str = arg_str[:200] + "..."
            formatted_args.append(f"  args[{i}]: {arg_str}")
        except:
            formatted_args.append(f"  args[{i}]: <unprintable>")
    
    formatted_kwargs = []
    for key, value in kwargs.items():
        try:
            val_str = repr(value)
            if len(val_str) > 200:
                val_str = val_str[:200] + "..."
            formatted_kwargs.append(f"  {key}: {val_str}")
        except:
            formatted_kwargs.append(f"  {key}: <unprintable>")
    
    # Get all files involved in the traceback
    involved_files = list(set([frame.filename for frame in tb if frame.filename]))
    
    return {
        "timestamp": datetime.now().isoformat(),
        "function_name": func.__name__,
        "module_name": module_name,
        "module_file": module_file,
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "error_file": error_file,
        "error_line": error_line,
        "error_function": error_function,
        "args": formatted_args,
        "kwargs": formatted_kwargs,
        "traceback": traceback.format_exc(),
        "code_context": code_context,
        "involved_files": involved_files
    }

def save_to_error_log(error_info):
    """Save error to traditional error log file"""
    # Detect if we're running in WSL or Windows
    import platform
    if platform.system() == "Linux":
        # Running in WSL
        error_dir = Path("Errors")
    else:
        # Running in Windows
        error_dir = Path("Errors")
    
    error_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = error_dir / "errors.log"
    
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"\n{'='*60}\n")
        f.write(f"Timestamp: {error_info['timestamp']}\n")
        f.write(f"Function: {error_info['function_name']} in {error_info['module_name']}\n")
        f.write(f"Error: {error_info['error_type']}: {error_info['error_message']}\n")
        f.write(f"Location: {error_info['error_file']}:{error_info['error_line']}\n")
        f.write(f"Traceback:\n{error_info['traceback']}\n")

def windows_to_linux_path(win_path):
    """Convert Windows path to Linux path for WSL"""
    if isinstance(win_path, str):
        # Convert V:/ or v:/ to /mnt/v/
        if win_path.startswith(('V:/', 'v:/', 'V:\\', 'v:\\')):
            # Replace V:/ with /mnt/v/ and fix backslashes
            linux_path = win_path.replace('V:/', '/mnt/v/').replace('v:/', '/mnt/v/')
            linux_path = linux_path.replace('V:\\', '/mnt/v/').replace('v:\\', '/mnt/v/')
            linux_path = linux_path.replace('\\', '/')
            return linux_path
    return win_path

def convert_traceback_paths(traceback_str):
    """Convert Windows paths in traceback to Linux paths"""
    lines = traceback_str.split('\n')
    converted_lines = []
    for line in lines:
        # Look for File "V:/ or File "v:/ patterns
        if 'File "' in line:
            # Extract the path between quotes
            match = re.search(r'File "([^"]+)"', line)
            if match:
                original_path = match.group(1)
                linux_path = windows_to_linux_path(original_path)
                line = line.replace(f'"{original_path}"', f'"{linux_path}"')
        converted_lines.append(line)
    return '\n'.join(converted_lines)

def generate_debug_prompt(error_info):
    """Generate a comprehensive debugging prompt for Claude"""
    # Convert paths to Linux format for Claude
    linux_error_file = windows_to_linux_path(error_info['error_file'])
    linux_module_file = windows_to_linux_path(error_info['module_file'])
    linux_involved_files = [windows_to_linux_path(f) for f in error_info['involved_files']]
    linux_traceback = convert_traceback_paths(error_info['traceback'])
    
    # Check if there's a file path in the arguments (common for file operations)
    file_being_processed = None
    if error_info['args']:
        for arg in error_info['args']:
            # Look for file paths in arguments
            if any(indicator in arg for indicator in ['/', '\\', '.json', '.txt', '.py', '.env', '.xml', '.yaml', '.yml']):
                # Extract the file path from the argument with error handling
                try:
                    parts = arg.split(': ', 1)
                    if len(parts) > 1:
                        file_path_match = parts[1].strip().strip("'\"")
                        file_being_processed = windows_to_linux_path(file_path_match)
                        break
                except (IndexError, AttributeError):
                    # If parsing fails, continue to next argument
                    continue
            # Also check for file objects
            elif '<_io.TextIOWrapper' in arg and 'name=' in arg:
                # Extract filename from file object representation
                import re
                match = re.search(r"name='([^']+)'", arg)
                if match:
                    file_being_processed = windows_to_linux_path(match.group(1))
                    break
    
    prompt = f"""=== DEBUGGING PROMPT FOR CLAUDE ===
Generated: {error_info['timestamp']}
System: Rhoda's Interface

{"FILE BEING PROCESSED: " + file_being_processed + chr(10) + "=" * 50 + chr(10) if file_being_processed else ""}

ERROR SUMMARY:
--------------
Function: {error_info['module_name']}.{error_info['function_name']}
Error Type: {error_info['error_type']}
Error Message: {error_info['error_message']}

SOURCE LOCATION:
----------------
File: {linux_error_file}
Line: {error_info['error_line']}
Function: {error_info['error_function']}

FUNCTION ARGUMENTS:
-------------------
Arguments:
{chr(10).join(error_info['args']) if error_info['args'] else '  (none)'}

Keyword Arguments:
{chr(10).join(error_info['kwargs']) if error_info['kwargs'] else '  (none)'}

CODE CONTEXT:
-------------
{chr(10).join(error_info['code_context'])}

FULL TRACEBACK:
---------------
{linux_traceback}

FILES INVOLVED:
---------------
{chr(10).join(f'- {f}' for f in linux_involved_files)}

DEBUGGING REQUEST:
------------------
Please help debug this error in Rhoda's interface. The error occurred in the {error_info['function_name']} function.
Key points to investigate:
1. Why did this error occur?
2. What's the root cause?
3. How can we fix it?
4. Are there any similar issues that might occur elsewhere?

Please provide a solution that maintains backwards compatibility and follows the existing code patterns in the project.
"""
    return prompt

def save_debug_prompt(prompt, error_info):
    """Save the debugging prompt to a file"""
    # Detect if we're running in WSL or Windows
    import platform
    if platform.system() == "Linux":
        # Running in WSL
        debug_dir = Path("Errors/debug_prompts")
    else:
        # Running in Windows
        debug_dir = Path("Errors/debug_prompts")
    
    debug_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with timestamp and function name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_func_name = error_info['function_name'].replace('/', '_').replace('\\', '_')
    filename = f"{timestamp}_{safe_func_name}.txt"
    
    prompt_file = debug_dir / filename
    
    # Save the prompt
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    # Update the prompt history index
    history_file = debug_dir / "prompt_history.json"
    
    history_entry = {
        "timestamp": error_info['timestamp'],
        "filename": filename,
        "function": error_info['function_name'],
        "error_type": error_info['error_type'],
        "error_message": error_info['error_message'][:100]  # Truncate for index
    }
    
    # Load existing history or create new
    history = []
    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
    
    # Add new entry and limit to last 100 entries
    history.append(history_entry)
    history = history[-100:]
    
    # Save updated history
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2)
    
    print(f"Debug prompt saved to: {prompt_file}")