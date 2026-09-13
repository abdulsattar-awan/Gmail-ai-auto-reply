import sqlite3
conn = sqlite3.connect("emails.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS emails (
    id TEXT PRIMARY KEY,
    sender TEXT,
    subject TEXT,
    category TEXT,
    reply TEXT
)
""")
conn.commit()

cursor.execute("SELECT * FROM emails")
rows = cursor.fetchall()

for row in rows:
    print(row)