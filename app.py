import os
import re
import secrets
import sqlite3
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, abort
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Production mein SECRET_KEY environment variable se set karein.
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "0") == "1"
)
app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024

csrf = CSRFProtect(app)

PRIVATE_DIR = Path(app.root_path) / "instance"
PRIVATE_DIR.mkdir(exist_ok=True)
DB_PATH = PRIVATE_DIR / "students.sqlite3"


def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                course TEXT NOT NULL,
                branch TEXT NOT NULL,
                semester TEXT NOT NULL,
                enrollment TEXT,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Cache-Control"] = "no-store"
    return response


def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)
    return wrapper


@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("index.html")

    first = request.form.get("first_name", "").strip()
    last = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    course = request.form.get("course", "").strip()
    branch = request.form.get("branch", "").strip()
    semester = request.form.get("semester", "").strip()
    enrollment = request.form.get("enrollment", "").strip()
    password = request.form.get("password", "")
    confirm = request.form.get("confirm_password", "")

    if not all([first, last, email, phone, course, branch,
                semester, password, confirm]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("register"))

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        flash("Please enter a valid email address.", "error")
        return redirect(url_for("register"))

    if not re.fullmatch(r"[6-9]\d{9}", phone):
        flash("Enter a valid 10-digit Indian mobile number.", "error")
        return redirect(url_for("register"))

    if len(password) < 8:
        flash("Password must contain at least 8 characters.", "error")
        return redirect(url_for("register"))

    if password != confirm:
        flash("Passwords do not match.", "error")
        return redirect(url_for("register"))

    try:
        with connect_db() as db:
            db.execute("""
                INSERT INTO students
                (first_name, last_name, email, phone, course,
                 branch, semester, enrollment, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first, last, email, phone, course,
                branch, semester, enrollment,
                generate_password_hash(password)
            ))
    except sqlite3.IntegrityError:
        flash("This email is already registered.", "error")
        return redirect(url_for("register"))

    flash("Student registered successfully!", "success")
    return redirect(url_for("register"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = os.environ.get("ADMIN_USERNAME", "")
        password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")

        entered_user = request.form.get("username", "")
        entered_password = request.form.get("password", "")

        if (
            username
            and password_hash
            and secrets.compare_digest(entered_user, username)
            and check_password_hash(password_hash, entered_password)
        ):
            session.clear()
            session["is_admin"] = True
            session.permanent = True
            app.permanent_session_lifetime = 1800
            return redirect(url_for("dashboard"))

        flash("Invalid credentials or admin not configured.", "error")

    return render_template("admin_login.html")


@app.route("/admin")
@admin_required
def dashboard():
    q = request.args.get("q", "").strip()

    with connect_db() as db:
        if q:
            term = f"%{q}%"
            students = db.execute("""
                SELECT id, first_name, last_name, email, phone,
                       course, branch, semester, enrollment, created_at
                FROM students
                WHERE first_name LIKE ? OR last_name LIKE ?
                   OR email LIKE ? OR enrollment LIKE ?
                ORDER BY id DESC LIMIT 200
            """, (term, term, term, term)).fetchall()
        else:
            students = db.execute("""
                SELECT id, first_name, last_name, email, phone,
                       course, branch, semester, enrollment, created_at
                FROM students ORDER BY id DESC LIMIT 200
            """).fetchall()

        total = db.execute(
            "SELECT COUNT(*) FROM students"
        ).fetchone()[0]

    return render_template(
        "admin_dashboard.html", students=students,
        total=total, q=q
    )


@app.route("/admin/student/<int:student_id>")
@admin_required
def student_detail(student_id):
    with connect_db() as db:
        student = db.execute("""
            SELECT id, first_name, last_name, email, phone,
                   course, branch, semester, enrollment, created_at
            FROM students WHERE id = ?
        """, (student_id,)).fetchone()

    if student is None:
        abort(404)

    return render_template("student_detail.html", student=student)


@app.route("/admin/student/<int:student_id>/delete", methods=["POST"])
@admin_required
def delete_student(student_id):
    with connect_db() as db:
        db.execute("DELETE FROM students WHERE id = ?", (student_id,))

    flash("Student record deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    return redirect(url_for("admin_login"))


@app.errorhandler(413)
def too_large(_error):
    return "Request is too large.", 413


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)