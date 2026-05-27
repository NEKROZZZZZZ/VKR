import sqlite3
from datetime import datetime

DB_PATH = 'aeroexpress.db'

def add_test_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Создаём тестовую сессию
    session_key = 'test_user_001'
    cursor.execute('''
        INSERT OR IGNORE INTO sessions (session_key, channel, status, created_at)
        VALUES (?, 'webchat', 'active', ?)
    ''', (session_key, datetime.now()))
    
    # Получаем ID сессии
    cursor.execute('SELECT id FROM sessions WHERE session_key = ?', (session_key,))
    session_id = cursor.fetchone()[0]
    
    # 2. Добавляем тестовые сообщения
    test_messages = [
        (session_id, 'user', 'Привет!', 'greeting', 0.95),
        (session_id, 'bot', 'Здравствуйте! Чем могу помочь?', 'greeting', 0.95),
        (session_id, 'user', 'Как вернуть билет?', 'refund', 0.88),
        (session_id, 'bot', 'Укажите номер билета (10 цифр)', 'refund', 0.88),
    ]
    
    cursor.executemany('''
        INSERT INTO messages (session_id, role, text, intent, confidence, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [(m[0], m[1], m[2], m[3], m[4], datetime.now()) for m in test_messages])
    
    # 3. Добавляем тестовое письмо в email_queue
    cursor.execute('''
        INSERT INTO email_queue (sender, subject, body_text, predicted_intent, confidence, target_department, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ('test@example.com', 'Возврат билета', 'Хочу вернуть билет 1234567890', 'refund', 0.92, 'Финансовый отдел', 'new'))
    
    conn.commit()
    conn.close()
    
    print("✅ Тестовые данные добавлены!")
    print(f"Сессия: {session_key}")
    print("Сообщения: 4 записи")
    print("Письма: 1 запись")

if __name__ == "__main__":
    add_test_data()