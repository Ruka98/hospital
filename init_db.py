import sqlite3
from pathlib import Path
import hashlib
import os

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "hospital.db"
SCHEMA_PATH = APP_DIR / "schema.sql"

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def main():
    if DB_PATH.exists():
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    # Insert default admin into staff table
    conn.execute(
        "INSERT INTO staff (name, role, category, username, password_hash, is_available) VALUES (?, ?, ?, ?, ?, ?)",
        ("Administrator", "admin", "Management", "admin", hash_pw("admin123"), 1),
    )

    conn.commit()
    conn.close()
    print("✅ Database ready: hospital.db")
    print("✅ Default admin: admin / admin123")

if __name__ == "__main__":
    main()
