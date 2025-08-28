import sqlite3
from datetime import datetime
import os
import threading

# Database file path
DB_PATH = 'fellowship_demo.db'
db_lock = threading.Lock()

def init_db():
    """Initialize the SQLite database with users table"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                access_date TIMESTAMP NOT NULL,
                last_active TIMESTAMP,
                last_message_time TIMESTAMP,
                session_count INTEGER DEFAULT 1,
                user_notes TEXT,
                timeout_until TIMESTAMP
            )
        ''')
        
        # Create index on username for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_username 
            ON users(username)
        ''')
        
        # Add new columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_message_time TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN user_notes TEXT')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN timeout_until TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        # Create planner_events table for one-time scheduled events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planner_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                event_end TEXT,
                event_name TEXT NOT NULL,
                event_notes TEXT,
                special_occasion BOOLEAN DEFAULT 0,
                location TEXT,
                people_involved TEXT,  -- JSON array stored as text
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on date and time for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_planner_date_time 
            ON planner_events(date, time)
        ''')
        
        # Create daily_schedule table for recurring events
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week TEXT NOT NULL,
                event_name TEXT NOT NULL,
                event_notes TEXT,
                start_time TEXT NOT NULL,
                event_end TEXT,
                location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on day_of_week for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_daily_day 
            ON daily_schedule(day_of_week)
        ''')
        
        # Create reminders table for notebook functionality
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_date TEXT,
                reminder_time TEXT,
                reminder_end TEXT,
                reminder_location TEXT,
                note TEXT NOT NULL,
                subject TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create index on reminder_date for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_reminder_date 
            ON reminders(reminder_date)
        ''')
        
        # Create knowledgebase categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kb_categories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1,
                create_subcontext BOOLEAN DEFAULT 0,
                subcontext_settings TEXT,  -- JSON stored as text
                order_index INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create knowledgebase entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS kb_entries (
                id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                text_content TEXT NOT NULL,
                keys TEXT,  -- JSON array stored as text
                category_id TEXT,
                enabled BOOLEAN DEFAULT 1,
                force_activation BOOLEAN DEFAULT 0,
                key_relative BOOLEAN DEFAULT 0,
                non_story_activatable BOOLEAN DEFAULT 0,
                search_range INTEGER DEFAULT 1000,
                token_budget INTEGER DEFAULT 250,
                budget_priority INTEGER DEFAULT 400,
                context_config TEXT,  -- JSON stored as text
                lore_bias_groups TEXT,  -- JSON stored as text
                last_updated_at INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES kb_categories(id)
            )
        ''')
        
        # Create indexes for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kb_entries_name 
            ON kb_entries(display_name)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kb_entries_category 
            ON kb_entries(category_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kb_entries_enabled 
            ON kb_entries(enabled)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_kb_entries_force 
            ON kb_entries(force_activation)
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at {DB_PATH}")

def store_user(username):
    """Store a username with access timestamp in the database"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        current_time = datetime.now()
        
        # Check if user already exists
        cursor.execute('''
            SELECT id, session_count FROM users 
            WHERE username = ?
        ''', (username,))
        
        existing_user = cursor.fetchone()
        
        if existing_user:
            # Update existing user
            user_id, session_count = existing_user
            cursor.execute('''
                UPDATE users 
                SET last_active = ?, session_count = ?
                WHERE id = ?
            ''', (current_time, session_count + 1, user_id))
            print(f"Updated existing user: {username} (session #{session_count + 1})")
        else:
            # Insert new user
            cursor.execute('''
                INSERT INTO users (username, access_date, last_active)
                VALUES (?, ?, ?)
            ''', (username, current_time, current_time))
            print(f"Created new user: {username}")
        
        conn.commit()
        conn.close()
        
        return True

def get_user(username):
    """Retrieve user information from database"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, access_date, last_active, session_count
            FROM users
            WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {
                'id': user[0],
                'username': user[1],
                'access_date': user[2],
                'last_active': user[3],
                'session_count': user[4]
            }
        return None

def get_all_users():
    """Get all users from the database"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT username, access_date, last_active, session_count
            FROM users
            ORDER BY last_active DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        return [
            {
                'username': user[0],
                'access_date': user[1],
                'last_active': user[2],
                'session_count': user[3]
            }
            for user in users
        ]

def update_user_activity(username):
    """Update the last active timestamp for a user"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users
            SET last_active = ?
            WHERE username = ?
        ''', (datetime.now(), username))
        
        conn.commit()
        conn.close()

def get_user_stats():
    """Get statistics about users in the database"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        # Users active today
        cursor.execute('''
            SELECT COUNT(*) FROM users
            WHERE DATE(last_active) = DATE('now')
        ''')
        active_today = cursor.fetchone()[0]
        
        # Total sessions
        cursor.execute('SELECT SUM(session_count) FROM users')
        total_sessions = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_users': total_users,
            'active_today': active_today,
            'total_sessions': total_sessions
        }

# Universal SQL functions with injection protection
def sql_insert(table, data, username=None):
    """Universal SQL insert function with validation"""
    if username:
        # Apply SQL injection validation
        if not validate_sql_input(username):
            raise ValueError(f"Invalid username contains potential SQL injection: {username}")
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Build parameterized query
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?' for _ in data.keys()])
            query = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

def sql_select(table, where_clause=None, params=None, username=None):
    """Universal SQL select function with validation"""
    if username:
        # Apply SQL injection validation
        if not validate_sql_input(username):
            raise ValueError(f"Invalid username contains potential SQL injection: {username}")
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            query = f'SELECT * FROM {table}'
            if where_clause:
                query += f' WHERE {where_clause}'
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            return cursor.fetchall()
        finally:
            conn.close()

def sql_update(table, data, where_clause, where_params, username=None):
    """Universal SQL update function with validation"""
    if username:
        # Apply SQL injection validation
        if not validate_sql_input(username):
            raise ValueError(f"Invalid username contains potential SQL injection: {username}")
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Build parameterized query
            set_clause = ', '.join([f'{key} = ?' for key in data.keys()])
            query = f'UPDATE {table} SET {set_clause} WHERE {where_clause}'
            
            params = list(data.values()) + where_params
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

def validate_sql_input(input_string):
    """Validate input to prevent SQL injection"""
    if not input_string:
        return False
    
    # Check for common SQL injection patterns
    dangerous_patterns = [
        "';", "'--", "' OR", "' AND", "' UNION", 
        "DROP", "DELETE", "INSERT", "UPDATE", "CREATE", "ALTER",
        "EXEC", "EXECUTE", "SCRIPT", "UNION", "SELECT"
    ]
    
    input_upper = input_string.upper()
    for pattern in dangerous_patterns:
        if pattern in input_upper:
            return False
    
    return True

def get_user_notes(username):
    """Get Rhoda's notes about a specific user"""
    if not validate_sql_input(username):
        return None
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT user_notes FROM users
                WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

def set_user_notes(username, notes):
    """Set Rhoda's notes about a specific user"""
    if not validate_sql_input(username):
        return False
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET user_notes = ?
                WHERE username = ?
            ''', (notes, username))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def set_user_timeout(username, timeout_until, admin_username=None):
    """Set timeout for a user (admin protection for Maggie)"""
    if not validate_sql_input(username):
        return False
    
    # Maggie cannot be timed out (admin protection)
    if username.lower() == "maggie":
        print("Cannot timeout admin user: Maggie")
        return False
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users 
                SET timeout_until = ?
                WHERE username = ?
            ''', (timeout_until, username))
            
            conn.commit()
            print(f"User {username} timed out until {timeout_until}")
            return cursor.rowcount > 0
        finally:
            conn.close()

def is_user_timed_out(username):
    """Check if a user is currently timed out"""
    if not validate_sql_input(username):
        return False
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT timeout_until FROM users
                WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            if result and result[0]:
                timeout_time = datetime.fromisoformat(result[0])
                return datetime.now() < timeout_time
            
            return False
        finally:
            conn.close()

def update_user_message_time(username):
    """Update the last message time for a user"""
    if not validate_sql_input(username):
        return False
    
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users
                SET last_message_time = ?
                WHERE username = ?
            ''', (datetime.now(), username))
            
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

# Schedule-related SQL functions

def get_planner_events(start_date=None, end_date=None):
    """Get planner events with optional date filtering"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if start_date and end_date:
                cursor.execute('''
                    SELECT * FROM planner_events
                    WHERE date >= ? AND date <= ?
                    ORDER BY date, time
                ''', (start_date, end_date))
            else:
                cursor.execute('''
                    SELECT * FROM planner_events
                    ORDER BY date, time
                ''')
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                event = dict(zip(columns, row))
                # Parse people_involved JSON if present
                if event.get('people_involved'):
                    import json
                    try:
                        event['people_involved'] = json.loads(event['people_involved'])
                    except:
                        event['people_involved'] = []
                events.append(event)
            return events
        finally:
            conn.close()

def add_planner_event(event_data):
    """Add a new event to the planner"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Convert people_involved list to JSON string if present
            if 'people_involved' in event_data and isinstance(event_data['people_involved'], list):
                import json
                event_data['people_involved'] = json.dumps(event_data['people_involved'])
            
            columns = ', '.join(event_data.keys())
            placeholders = ', '.join(['?' for _ in event_data.keys()])
            query = f'INSERT INTO planner_events ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(event_data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

def update_planner_event(event_id, event_data):
    """Update an existing planner event"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Convert people_involved list to JSON string if present
            if 'people_involved' in event_data and isinstance(event_data['people_involved'], list):
                import json
                event_data['people_involved'] = json.dumps(event_data['people_involved'])
            
            # Add updated_at timestamp
            event_data['updated_at'] = datetime.now()
            
            set_clause = ', '.join([f'{key} = ?' for key in event_data.keys()])
            query = f'UPDATE planner_events SET {set_clause} WHERE id = ?'
            
            params = list(event_data.values()) + [event_id]
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def delete_planner_event(event_id):
    """Delete a planner event"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM planner_events WHERE id = ?', (event_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def get_daily_schedule(day_of_week=None):
    """Get daily schedule events"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if day_of_week:
                cursor.execute('''
                    SELECT * FROM daily_schedule
                    WHERE day_of_week = ?
                    ORDER BY start_time
                ''', (day_of_week,))
            else:
                cursor.execute('''
                    SELECT * FROM daily_schedule
                    ORDER BY day_of_week, start_time
                ''')
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                event = dict(zip(columns, row))
                events.append(event)
            return events
        finally:
            conn.close()

def add_daily_event(event_data):
    """Add a new daily schedule event"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            columns = ', '.join(event_data.keys())
            placeholders = ', '.join(['?' for _ in event_data.keys()])
            query = f'INSERT INTO daily_schedule ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(event_data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

def get_reminders(start_date=None, end_date=None):
    """Get reminders with optional date filtering"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if start_date and end_date:
                cursor.execute('''
                    SELECT * FROM reminders
                    WHERE reminder_date >= ? AND reminder_date <= ?
                    ORDER BY reminder_date, reminder_time
                ''', (start_date, end_date))
            else:
                cursor.execute('''
                    SELECT * FROM reminders
                    ORDER BY reminder_date, reminder_time
                ''')
            
            columns = [desc[0] for desc in cursor.description]
            reminders = []
            for row in cursor.fetchall():
                reminder = dict(zip(columns, row))
                reminders.append(reminder)
            return reminders
        finally:
            conn.close()

def add_reminder(reminder_data):
    """Add a new reminder"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            columns = ', '.join(reminder_data.keys())
            placeholders = ', '.join(['?' for _ in reminder_data.keys()])
            query = f'INSERT INTO reminders ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(reminder_data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

def search_planner_events(search_text, limit=10):
    """Search planner events by text in event_name or event_notes"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            search_pattern = f'%{search_text}%'
            cursor.execute('''
                SELECT * FROM planner_events
                WHERE event_name LIKE ? OR event_notes LIKE ?
                ORDER BY date DESC, time DESC
                LIMIT ?
            ''', (search_pattern, search_pattern, limit))
            
            columns = [desc[0] for desc in cursor.description]
            events = []
            for row in cursor.fetchall():
                event = dict(zip(columns, row))
                # Parse people_involved JSON if present
                if event.get('people_involved'):
                    import json
                    try:
                        event['people_involved'] = json.loads(event['people_involved'])
                    except:
                        event['people_involved'] = []
                events.append(event)
            return events
        finally:
            conn.close()

# Knowledgebase SQL functions

def get_kb_categories(enabled_only=True):
    """Get knowledgebase categories"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            if enabled_only:
                cursor.execute('''
                    SELECT * FROM kb_categories
                    WHERE enabled = 1
                    ORDER BY order_index, name
                ''')
            else:
                cursor.execute('''
                    SELECT * FROM kb_categories
                    ORDER BY order_index, name
                ''')
            
            columns = [desc[0] for desc in cursor.description]
            categories = []
            for row in cursor.fetchall():
                category = dict(zip(columns, row))
                # Parse JSON fields if present
                if category.get('subcontext_settings'):
                    import json
                    try:
                        category['subcontext_settings'] = json.loads(category['subcontext_settings'])
                    except:
                        pass
                categories.append(category)
            return categories
        finally:
            conn.close()

def add_kb_category(category_data):
    """Add a new knowledgebase category"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Convert subcontext_settings to JSON string if present
            if 'subcontext_settings' in category_data and isinstance(category_data['subcontext_settings'], dict):
                import json
                category_data['subcontext_settings'] = json.dumps(category_data['subcontext_settings'])
            
            columns = ', '.join(category_data.keys())
            placeholders = ', '.join(['?' for _ in category_data.keys()])
            query = f'INSERT INTO kb_categories ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(category_data.values()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

def get_kb_entries(category_id=None, enabled_only=True, force_activation=None):
    """Get knowledgebase entries with optional filtering"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            conditions = []
            params = []
            
            if category_id:
                conditions.append('category_id = ?')
                params.append(category_id)
            
            if enabled_only:
                conditions.append('enabled = 1')
            
            if force_activation is not None:
                conditions.append('force_activation = ?')
                params.append(1 if force_activation else 0)
            
            where_clause = ' AND '.join(conditions) if conditions else '1=1'
            
            cursor.execute(f'''
                SELECT * FROM kb_entries
                WHERE {where_clause}
                ORDER BY display_name
            ''', params)
            
            columns = [desc[0] for desc in cursor.description]
            entries = []
            for row in cursor.fetchall():
                entry = dict(zip(columns, row))
                # Parse JSON fields
                import json
                if entry.get('keys'):
                    try:
                        entry['keys'] = json.loads(entry['keys'])
                    except:
                        entry['keys'] = []
                if entry.get('context_config'):
                    try:
                        entry['context_config'] = json.loads(entry['context_config'])
                    except:
                        pass
                if entry.get('lore_bias_groups'):
                    try:
                        entry['lore_bias_groups'] = json.loads(entry['lore_bias_groups'])
                    except:
                        pass
                entries.append(entry)
            return entries
        finally:
            conn.close()

def add_kb_entry(entry_data):
    """Add a new knowledgebase entry"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Convert JSON fields to strings
            import json
            if 'keys' in entry_data and isinstance(entry_data['keys'], list):
                entry_data['keys'] = json.dumps(entry_data['keys'])
            if 'context_config' in entry_data and isinstance(entry_data['context_config'], dict):
                entry_data['context_config'] = json.dumps(entry_data['context_config'])
            if 'lore_bias_groups' in entry_data and isinstance(entry_data['lore_bias_groups'], list):
                entry_data['lore_bias_groups'] = json.dumps(entry_data['lore_bias_groups'])
            
            columns = ', '.join(entry_data.keys())
            placeholders = ', '.join(['?' for _ in entry_data.keys()])
            query = f'INSERT INTO kb_entries ({columns}) VALUES ({placeholders})'
            
            cursor.execute(query, list(entry_data.values()))
            conn.commit()
            return entry_data.get('id', cursor.lastrowid)
        finally:
            conn.close()

def update_kb_entry(entry_id, entry_data):
    """Update an existing knowledgebase entry"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            # Convert JSON fields to strings
            import json
            if 'keys' in entry_data and isinstance(entry_data['keys'], list):
                entry_data['keys'] = json.dumps(entry_data['keys'])
            if 'context_config' in entry_data and isinstance(entry_data['context_config'], dict):
                entry_data['context_config'] = json.dumps(entry_data['context_config'])
            if 'lore_bias_groups' in entry_data and isinstance(entry_data['lore_bias_groups'], list):
                entry_data['lore_bias_groups'] = json.dumps(entry_data['lore_bias_groups'])
            
            # Update timestamp
            from datetime import datetime
            entry_data['last_updated_at'] = int(datetime.now().timestamp() * 1000)
            
            set_clause = ', '.join([f'{key} = ?' for key in entry_data.keys()])
            query = f'UPDATE kb_entries SET {set_clause} WHERE id = ?'
            
            params = list(entry_data.values()) + [entry_id]
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def delete_kb_entry(entry_id):
    """Delete a knowledgebase entry"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM kb_entries WHERE id = ?', (entry_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

def search_kb_entries(search_text, limit=10):
    """Search knowledgebase entries by text in display_name, text_content, or keys"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            search_pattern = f'%{search_text}%'
            cursor.execute('''
                SELECT * FROM kb_entries
                WHERE display_name LIKE ? 
                   OR text_content LIKE ?
                   OR keys LIKE ?
                ORDER BY 
                    CASE WHEN display_name LIKE ? THEN 1 ELSE 2 END,
                    display_name
                LIMIT ?
            ''', (search_pattern, search_pattern, search_pattern, search_pattern, limit))
            
            columns = [desc[0] for desc in cursor.description]
            entries = []
            for row in cursor.fetchall():
                entry = dict(zip(columns, row))
                # Parse JSON fields
                import json
                if entry.get('keys'):
                    try:
                        entry['keys'] = json.loads(entry['keys'])
                    except:
                        entry['keys'] = []
                if entry.get('context_config'):
                    try:
                        entry['context_config'] = json.loads(entry['context_config'])
                    except:
                        pass
                if entry.get('lore_bias_groups'):
                    try:
                        entry['lore_bias_groups'] = json.loads(entry['lore_bias_groups'])
                    except:
                        pass
                entries.append(entry)
            return entries
        finally:
            conn.close()

def check_kb_entry_exists(display_name):
    """Check if a knowledgebase entry with the given display_name exists"""
    with db_lock:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT COUNT(*) FROM kb_entries
                WHERE LOWER(display_name) = LOWER(?)
            ''', (display_name,))
            
            count = cursor.fetchone()[0]
            return count > 0
        finally:
            conn.close()

# Initialize database when module is imported
if not os.path.exists(DB_PATH):
    init_db()