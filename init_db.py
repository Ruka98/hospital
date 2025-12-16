import sqlite3
from pathlib import Path
import hashlib

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "hospital.db"
SCHEMA_PATH = APP_DIR / "schema.sql"

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def main():
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())

    conn.execute(
        "INSERT OR IGNORE INTO admins (username, password_hash) VALUES (?, ?)",
        ("admin", hash_pw("admin123")),
    )
    conn.commit()
    conn.close()
    print("✅ Database ready: hospital.db")
    print("✅ Default admin: admin / admin123")

if __name__ == "__main__":
    main()
