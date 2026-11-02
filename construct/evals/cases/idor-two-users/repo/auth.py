from functools import wraps

from flask import g, jsonify, session


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user_id = session.get("user_id")
        if user_id is None:
            return jsonify(error="unauthorized"), 401
        g.user_id = int(user_id)
        return view(*args, **kwargs)

    return wrapper
