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


def cart_view(user_id):
    rows = db().execute(
        "SELECT p.id, p.name, p.price, c.quantity FROM cart_items c "
        "JOIN products p ON p.id = c.product_id WHERE c.user_id = ?",
        (user_id,),
    ).fetchall()
    items = [dict(r) for r in rows]
    return {"items": items, "total": sum(i["price"] * i["quantity"] for i in items)}


@app.get("/api/cart")
@login_required
def get_cart():
    return jsonify(cart_view(g.user_id))


@app.post("/api/cart/items")
@login_required
def add_item():
    body = request.get_json(silent=True) or {}
    product = db().execute(
        "SELECT id FROM products WHERE id = ?", (body.get("product_id"),)
    ).fetchone()
    if product is None:
        return jsonify(error="unknown product"), 404
    quantity = int(body.get("quantity", 1))
    db().execute(
        "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (?, ?, ?)",
        (g.user_id, product["id"], quantity),
    )
    db().commit()
    return jsonify(cart_view(g.user_id)), 201
