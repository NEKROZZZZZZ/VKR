import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

DB_PATH = 'aeroexpress.db'

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
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
        cursor.execute('''
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
    print("База данных SQLite готова")

def get_session_by_key(session_key: str) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM sessions WHERE session_key = ?', (session_key,))
        row = cursor.fetchone()
        return dict(row) if row else None

def create_session(session_key: str, channel: str = 'webchat') -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT OR IGNORE INTO sessions (session_key, channel) VALUES (?, ?)', (session_key, channel))
        cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
        return cursor.fetchone()[0]

def get_or_create_session(session_key: str, channel: str = 'webchat') -> Dict:
    sess = get_session_by_key(session_key)
    if not sess:
        create_session(session_key, channel)
        sess = get_session_by_key(session_key)
    return sess

def save_message(session_key: str, role: str, text: str, intent: str = None, confidence: float = None) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
        row = cursor.fetchone()
        if not row:
            create_session(session_key)
            cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
            session_id = cursor.fetchone()[0]
        else:
            session_id = row[0]
        cursor.execute(
            'INSERT INTO messages (session_id, role, text, intent, confidence) VALUES (?, ?, ?, ?, ?)',
            (session_id, role, text, intent, confidence)
        )
        return cursor.lastrowid

def get_dialog_history(session_key: str, limit: int = 50) -> List[Dict]:
    with get_db() as conn:
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

def get_metrics() -> Dict[str, Any]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE status = "active"')
        active_sessions = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM email_queue WHERE status = "new"')
        unprocessed_emails = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM sessions WHERE status = "escalated"')
        escalated_sessions = cursor.fetchone()[0]
        escalation_rate = round(escalated_sessions / total_sessions if total_sessions else 0, 3)
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_messages': total_messages,
            'unprocessed_emails': unprocessed_emails,
            'escalated_sessions': escalated_sessions,
            'escalation_rate': escalation_rate
        }