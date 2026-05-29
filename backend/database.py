import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any

DB_PATH = 'aeroexpress.db'

def get_connection():
    """Возвращает соединение с БД"""
    return sqlite3.connect(DB_PATH)

def init_db():
    """Инициализация всех таблиц (сессии, сообщения, письма, билеты)"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Таблица сессий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Таблица сообщений
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

        # Таблица для писем (email_queue)
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

        # Таблица билетов (новая)
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

    print("✅ База данных инициализирована (таблицы sessions, messages, email_queue, tickets)")

# ==================== Функции для сессий и сообщений ====================

def get_or_create_session(session_key: str) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
        row = cursor.fetchone()
        if row:
            return row[0]
        cursor.execute('INSERT INTO sessions (session_key) VALUES (?)', (session_key,))
        return cursor.lastrowid

def save_message(session_key: str, role: str, text: str, intent: str = None, confidence: float = None):
    session_id = get_or_create_session(session_key)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO messages (session_id, role, text, intent, confidence)
            VALUES (?, ?, ?, ?, ?)
        ''', (session_id, role, text, intent, confidence))

def get_all_messages(limit=1000):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.session_key, m.role, m.text, m.intent, m.timestamp
            FROM messages m
            JOIN sessions s ON m.session_id = s.id
            ORDER BY m.timestamp DESC
            LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

def get_dialog_history(session_key: str, limit: int = 50) -> List[Dict]:
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

# ==================== Функции для билетов ====================

def add_ticket(ticket_number: str, passenger_name: str, email: str, phone: str,
              route: str, date: str, departure_time: str, status: str = 'active'):
    """Добавляет или обновляет билет в базе"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO tickets
            (ticket_number, passenger_name, email, phone, route, date, departure_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (ticket_number, passenger_name, email, phone, route, date, departure_time, status))

def find_tickets_by_email(email: str):
    """Ищет билеты по email (точное совпадение)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE email = ?', (email,))
        return cursor.fetchall()

def find_tickets_by_phone(phone: str):
    """Ищет билеты по номеру телефона (точное совпадение)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE phone = ?', (phone,))
        return cursor.fetchall()

def find_ticket_by_number(ticket_number: str):
    """Ищет билет по номеру билета"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets WHERE ticket_number = ?', (ticket_number,))
        return cursor.fetchone()

def get_all_tickets():
    """Возвращает все билеты (для отладки)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tickets')
        return cursor.fetchall()

def update_ticket_status(ticket_number: str, status: str):
    """Обновляет статус билета (active, refunded, used)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE tickets SET status = ? WHERE ticket_number = ?', (status, ticket_number))

# ==================== Функции для писем (email_queue) ====================

def save_email(sender: str, subject: str, body: str, predicted_intent: str = None,
               confidence: float = None, target_department: str = None) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO email_queue (sender, subject, body_text, predicted_intent, confidence, target_department)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (sender, subject, body, predicted_intent, confidence, target_department))
        return cursor.lastrowid

def get_unprocessed_emails(limit=10):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM email_queue WHERE status = 'new' ORDER BY created_at LIMIT ?
        ''', (limit,))
        return cursor.fetchall()

def update_email_status(email_id: int, status: str, auto_reply: str = None):
    with get_connection() as conn:
        cursor = conn.cursor()
        if auto_reply:
            cursor.execute('''
                UPDATE email_queue
                SET status = ?, auto_reply = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, auto_reply, email_id))
        else:
            cursor.execute('''
                UPDATE email_queue
                SET status = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, email_id))

# ==================== Вспомогательная функция для метрик ====================

def get_metrics():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM email_queue WHERE status = "new"')
        unprocessed_emails = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM tickets')
        total_tickets = cursor.fetchone()[0]
        return {
            'total_sessions': total_sessions,
            'total_messages': total_messages,
            'unprocessed_emails': unprocessed_emails,
            'total_tickets': total_tickets,
            'active_sessions': 0,
            'escalated_sessions': 0,
            'escalation_rate': 0.0
        }