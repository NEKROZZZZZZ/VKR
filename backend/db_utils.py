import sqlite3
from datetime import datetime

DB_PATH = 'aeroexpress.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Создаёт таблицы, если их нет"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT UNIQUE NOT NULL,
                channel TEXT DEFAULT 'webchat',
                status TEXT DEFAULT 'active',
                state TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                intent TEXT,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute(''')
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body_text TEXT NOT NULL,
                predicted_intent TEXT,
                confidence REAL,
                target_department TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    print("База данных инициализирована (таблицы созданы)")

def create_session(session_key, channel='webchat'):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO sessions (session_key, channel, created_at)
            VALUES (?, ?, ?)
        ''', (session_key, channel, datetime.now()))
        cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
        return cursor.fetchone()[0]

def save_message(session_key, role, text, intent=None, confidence=None):
    with get_connection() as conn:
        cursor = conn.cursor()
        # убедимся, что сессия существует
        cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
        row = cursor.fetchone()
        if not row:
            session_id = create_session(session_key)
        else:
            session_id = row[0]
        cursor.execute('''
            INSERT INTO messages (session_id, role, text, intent, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_id, role, text, intent, confidence, datetime.now()))

def get_history(session_key, limit=50):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, text, intent, timestamp
            FROM messages
            WHERE session_id = (SELECT id FROM sessions WHERE session_key = ?)
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (session_key, limit))
        rows = cursor.fetchall()
        return [{'role': r[0], 'text': r[1], 'intent': r[2], 'timestamp': r[3]} for r in rows]

def get_metrics():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM email_queue WHERE status="new"')
        unprocessed_emails = cursor.fetchone()[0]
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'unprocessed_emails': unprocessed_emails,
            'active_sessions': 0,
            'escalated_sessions': 0,
            'escalation_rate': 0.0
        }