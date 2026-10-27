import sqlite3

from flask import Flask, g, jsonify, request, session
from werkzeug.security import check_password_hash

from auth import login_required

app = Flask(__name__)
app.secret_key = "dev-only"
DB_PATH = "shop.db"


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    row = db().execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (body.get("username", ""),)
    ).fetchone()
    if row is None or not check_password_hash(row["password_hash"], body.get("password", "")):
        return jsonify(error="invalid credentials"), 401
    session["user_id"] = row["id"]
    return jsonify(id=row["id"])


@app.get("/api/orders")
@login_required
def list_orders():
    rows = db().execute(
        "SELECT id, note, total FROM orders WHERE user_id = ?", (g.user_id,)
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/orders/<int:order_id>")
@login_required
def get_order(order_id):
    row = db().execute(
        "SELECT id, user_id, note, total FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(dict(row))
