import sqlite3

from flask import Flask, g, jsonify, request

from auth import login_required

app = Flask(__name__)
app.secret_key = "dev-only"
DB_PATH = "shop.db"


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.get("/api/orders/<int:order_id>")
@login_required
def get_order(order_id):
    row = db().execute(
        "SELECT id, note, total FROM orders WHERE id = ? AND user_id = ?",
        (order_id, g.user_id),
    ).fetchone()
    if row is None:
        return jsonify(error="not found"), 404
    return jsonify(dict(row))


@app.get("/api/orders/search")
@login_required
def search_orders():
    q = request.args.get("q", "")
    rows = db().execute(
        "SELECT id, note, total FROM orders WHERE user_id = ? AND note LIKE ?",
        (g.user_id, f"%{q}%"),
    ).fetchall()
    return jsonify([dict(r) for r in rows])
