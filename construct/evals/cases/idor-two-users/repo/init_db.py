"""Create shop.db with two customers and one order each (local development and tests)."""
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

DB_PATH = "shop.db"
USERS = [(1, "alice", "alice-dev-pw"), (2, "bob", "bob-dev-pw")]
ORDERS = [(1, 1, "alice: blue bicycle", 25000), (2, 2, "bob: winter tyres", 18000)]


def main():
    Path(DB_PATH).unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(Path("schema.sql").read_text())
    con.executemany(
        "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        [(uid, name, generate_password_hash(pw)) for uid, name, pw in USERS],
    )
    con.executemany("INSERT INTO orders (id, user_id, note, total) VALUES (?, ?, ?, ?)", ORDERS)
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
