import sqlite3
import os

print("Создание базы данных...")

# Путь к файлу базы данных
db_path = 'aeroexpress.db'

# Удаляем старую базу данных, если она есть
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Старая база данных {db_path} удалена")

# Создаём подключение к базе данных
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Создаём таблицу сессий
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
print("✓ Таблица 'sessions' создана")

# Создаём таблицу сообщений
cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    intent TEXT,
    confidence REAL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions (id)
)
''')
print("✓ Таблица 'messages' создана")

# Создаём таблицу для писем
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
print("✓ Таблица 'email_queue' создана")

# Сохраняем изменения и закрываем соединение
conn.commit()
conn.close()

print(f"\n✅ База данных успешно создана: {db_path}")
print(f"📍 Полный путь: {os.path.abspath(db_path)}")

# Проверяем, что файл создался
if os.path.exists(db_path):
    size = os.path.getsize(db_path)
    print(f"📁 Размер файла: {size} байт")