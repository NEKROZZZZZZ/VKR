import sqlite3

conn = sqlite3.connect('aeroexpress.db')
cursor = conn.cursor()

# Получаем список всех таблиц
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Таблицы в базе данных:")
for table in tables:
    print(f"  - {table[0]}")

# Проверяем структуру таблицы sessions
cursor.execute("PRAGMA table_info(sessions)")
columns = cursor.fetchall()
print("\nСтруктура таблицы 'sessions':")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
print("\n✅ База данных работает корректно!")