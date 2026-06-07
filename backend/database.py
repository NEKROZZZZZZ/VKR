import sqlite3
from datetime import datetime
from typing import List, Dict

DB_PATH = 'aeroexpress.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                intent TEXT,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT UNIQUE NOT NULL,
                passenger_name TEXT,
                email TEXT,
                phone TEXT,
                route TEXT,
                date TEXT,
                departure_time TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT,
                subject TEXT,
                body_text TEXT,
                predicted_intent TEXT,
                confidence REAL,
                target_department TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    print("✅ База данных готова")

def save_message(session_key: str, role: str, text: str, intent: str = None, confidence: float = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (session_key, role, text, intent, confidence, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (session_key, role, text, intent, confidence, datetime.now()))

def get_dialog_history(session_key: str, limit: int = 200) -> List[Dict]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, text, intent, timestamp
            FROM messages
            WHERE session_key = ?
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (session_key, limit))
        rows = cursor.fetchall()
        return [{'role': r[0], 'text': r[1], 'intent': r[2], 'timestamp': r[3]} for r in rows]

def get_escalated_sessions(limit=50):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT session_key, MAX(timestamp) as last_activity
            FROM messages
            WHERE role = 'user' AND intent = 'operator'
            GROUP BY session_key
            ORDER BY last_activity DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        return [{'session_key': r[0], 'last_activity': r[1]} for r in rows if r[0] is not None]

def has_operator_replied(session_key: str) -> bool:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM messages WHERE session_key = ? AND role = "operator"', (session_key,))
        count = cursor.fetchone()[0]
        return count > 0

def get_all_messages(limit=1000):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT session_key, role, text, intent, timestamp
            FROM messages
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

def find_tickets_by_email(email):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE email = ?', (email,))
        return cursor.fetchall()

def find_tickets_by_phone(phone):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE phone = ?', (phone,))
        return cursor.fetchall()

def find_ticket_by_number(ticket_number):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE ticket_number = ?', (ticket_number,))
        return cursor.fetchone()

def update_ticket_status(ticket_number, status):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tickets SET status = ? WHERE ticket_number = ?', (status, ticket_number))