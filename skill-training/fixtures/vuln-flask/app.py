"""Intentionally vulnerable Flask app — a TEST FIXTURE for skill-training.

Not a real service. Each function below carries a planted, well-known
vulnerability so the `codebase` skill's review can be scored on whether it
finds them. See fixtures/vuln-flask/README.md.
"""
import hashlib
import os
import sqlite3

from flask import Flask, request

app = Flask(__name__)

# VULN: hardcoded secret (ASVS V13 / config & secrets)
SECRET_KEY = "hardcoded-super-secret-123"


@app.route("/user")
def user():
    uid = request.args.get("id")
    conn = sqlite3.connect("app.db")
    # VULN: SQL injection — user input concatenated into the query (ASVS V2)
    row = conn.execute("SELECT name FROM users WHERE id = '%s'" % uid).fetchone()
    return str(row)


@app.route("/ping")
def ping():
    host = request.args.get("host")
    # VULN: OS command injection — unsanitized input to a shell (ASVS V2)
    return os.popen("ping -c 1 " + host).read()


@app.route("/download")
def download():
    fn = request.args.get("file")
    # VULN: path traversal — unsanitized filename joined to a base dir (ASVS V2)
    with open("/var/data/" + fn) as f:
        return f.read()


def hash_password(pw):
    # VULN: weak/unsalted password hashing with MD5 (ASVS V11 crypto)
    return hashlib.md5(pw.encode()).hexdigest()


if __name__ == "__main__":
    # VULN: debug mode enabled (Werkzeug console RCE) in production (ASVS V16)
    app.run(host="0.0.0.0", debug=True)
