import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'trainer'))
)
''')

# Admin kullanıcıyı güvenli şekilde ekle
hashed_password = generate_password_hash('1234')

cursor.execute('''
INSERT OR IGNORE INTO users (username, password, role)
VALUES (?, ?, ?)
''', ('admin1', hashed_password, 'admin'))

conn.commit()
conn.close()
print("✅ users tablosu başarıyla oluşturuldu.")