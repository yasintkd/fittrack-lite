import sqlite3


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanı bağlantısı
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Kullanıcı tablosu (giriş sistemi için)
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'trainer'))
)
''')

# Üye tablosu
cursor.execute('''
CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT
)
''')

# Eğitmen tablosu
cursor.execute('''
CREATE TABLE IF NOT EXISTS trainers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    phone TEXT
)
''')

# Sınıf tablosu
cursor.execute('''
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    trainer_id INTEGER,
    FOREIGN KEY (trainer_id) REFERENCES trainers(id)
)
''')

# Katılım tablosu
cursor.execute('''
CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    class_id INTEGER,
    FOREIGN KEY (member_id) REFERENCES members(id),
    FOREIGN KEY (class_id) REFERENCES classes(id)
)
''')

# Ödeme tablosu
cursor.execute('''
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER,
    amount REAL,
    date TEXT,
    note TEXT,
    FOREIGN KEY (member_id) REFERENCES members(id)
)
''')

# Güvenli sütun ekleme fonksiyonu
def add_column_if_not_exists(table, column, column_type):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

# Öğrenciye özel ek alanlar
add_column_if_not_exists('members', 'birth_date', 'TEXT')
add_column_if_not_exists('members', 'height', 'REAL')
add_column_if_not_exists('members', 'weight', 'REAL')
add_column_if_not_exists('members', 'belt_level', 'TEXT')
add_column_if_not_exists('members', 'weight_category', 'TEXT')
add_column_if_not_exists('members', 'parent_name', 'TEXT')
add_column_if_not_exists('members', 'parent_phone', 'TEXT')
add_column_if_not_exists('members', 'parent_email', 'TEXT')
add_column_if_not_exists('members', 'registration_date', 'TEXT')
add_column_if_not_exists('trainers', 'share_percent', 'REAL')
add_column_if_not_exists('payments', 'note', 'TEXT')
add_column_if_not_exists('payments', 'payment_date', 'TEXT')
add_column_if_not_exists('payments', 'start_date', 'TEXT')
add_column_if_not_exists('payments', 'end_date', 'TEXT')

# Değişiklikleri kaydet
conn.commit()
conn.close()