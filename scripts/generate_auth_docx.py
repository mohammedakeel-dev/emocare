from docx import Document
from pathlib import Path

DOC_PATH = Path(__file__).resolve().parent.parent / "reports" / "login_signup_explanation.docx"
DOC_PATH.parent.mkdir(parents=True, exist_ok=True)

doc = Document()

doc.add_heading('Line-by-line explanation: login & signup (app.py)', level=1)

content = '''
@a pp.before_request
def before_request() -> None:
    g.db = sqlite3.connect(DB_PATH)
    g.db.row_factory = sqlite3.Row
- Explanation: Runs before each request. Opens a SQLite connection at DB_PATH and stores it on Flask's `g` (request-scoped) object; setting `row_factory` allows rows to be accessed like dicts (column names).

@app.teardown_appcontext
def close_connection(_: Any) -> None:
    db = getattr(g, "db", None)
    if db is not None:
        db.close()
- Explanation: Runs when the app context tears down (after request). Retrieves the connection from `g` and closes it if present to avoid resource leaks.

with app.app_context():
    init_db()
- Explanation: Ensures `init_db()` (which creates tables and runs migrations) runs during app startup within an application context.

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dominant_emotion TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            emotion TEXT,
            intensity INTEGER,
            image_path TEXT,
            detection_source TEXT DEFAULT 'text',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        );
        """)
        conn.commit()
        migrate_db(conn)
- Explanation: Creates `users`, `conversations`, and `messages` tables if missing. `users` stores accounts; `messages`/`conversations` store chat data. Commits changes and calls `migrate_db` to add missing columns for compatibility.

def migrate_db(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT image_path FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN image_path TEXT")
        except sqlite3.OperationalError:
            pass
    try:
        cursor.execute("SELECT detection_source FROM messages LIMIT 1")
    except sqlite3.OperationalError:
        try:
            cursor.execute("ALTER TABLE messages ADD COLUMN detection_source TEXT DEFAULT 'text'")
        except sqlite3.OperationalError:
            pass
    conn.commit()
- Explanation: Safely attempts to add `image_path` and `detection_source` columns to `messages` if they don't exist. Uses try/except to avoid failing if columns already exist.

def query_user(email: str) -> sqlite3.Row | None:
    cursor = g.db.execute("SELECT * FROM users WHERE email = ?", (email,))
    return cursor.fetchone()
- Explanation: Query helper that uses the per-request DB connection `g.db` to find a user by email. Uses parameterized query (`?`) to prevent SQL injection. Returns the first matching row or `None`.

def login_required(view: F) -> F:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
- Explanation: Decorator to protect routes. If `session` lacks `user_id`, flashes an error and redirects to login; otherwise proceeds to the wrapped view.

@app.route("/", methods=["GET", "POST"])
def login() -> str:
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
        else:
            user = query_user(email)
            if user and check_password_hash(user["password"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["full_name"]
                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("dashboard"))
            flash("Invalid credentials. Try again or sign up.", "error")

    return render_template("login.html")
- Explanation (line-by-line):
  - `if request.method == "POST":` — branch to process submitted form data.
  - `email = request.form.get("email", "").strip().lower()` — read email, remove spaces, normalize to lowercase to match stored emails.
  - `password = request.form.get("password", "")` — read password from form.
  - `if not email or not password:` — ensure both fields present; otherwise flash error.
  - `user = query_user(email)` — fetch user row from DB.
  - `if user and check_password_hash(user["password"], password):` — verify password against stored hashed password.
    - `session.clear()` — clear existing session data.
    - `session["user_id"] = user["id"]` — mark user as logged in.
    - `session["user_name"] = user["full_name"]` — store display name for templates.
    - `flash(...)` — show success message.
    - `return redirect(url_for("dashboard"))` — go to protected dashboard.
  - `flash("Invalid credentials...", "error")` — invalid login.
  - `return render_template("login.html")` — render the login page on GET or after failure.

@app.route("/signup", methods=["GET", "POST"])
def signup() -> str:
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not full_name or not email or not password:
            flash("Every field is required.", "error")
        elif password != confirm_password:
            flash("Passwords do not match.", "error")
        elif query_user(email):
            flash("An account with that email already exists.", "error")
        else:
            hashed_password = generate_password_hash(password)
            g.db.execute(
                "INSERT INTO users (full_name, email, password) VALUES (?, ?, ?)",
                (full_name, email, hashed_password),
            )
            g.db.commit()
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))

    return render_template("signup.html")
- Explanation (line-by-line):
  - Read `full_name`, `email`, `password`, `confirm_password` from `request.form` and normalize/strip where appropriate.
  - `if not full_name or not email or not password:` — require these fields.
  - `elif password != confirm_password:` — ensure confirmation matches.
  - `elif query_user(email):` — check whether the email is already registered; if so, error.
  - Else:
    - `hashed_password = generate_password_hash(password)` — securely hash password before storing.
    - `g.db.execute("INSERT INTO users ...", (full_name, email, hashed_password))` — parameterized insert into `users`.
    - `g.db.commit()` — persist the new user.
    - `flash("Account created! Please log in.", "success")` — notify user.
    - `return redirect(url_for("login"))` — send them to login page.
  - `return render_template("signup.html")` — on GET or after validation fail, render signup template.

Templates mapping:
- `templates/login.html` contains a `<form method="post">` with `name="email"` and `name="password"` inputs — these map directly to `request.form.get("email")` and `request.form.get("password")`.
- `templates/signup.html` contains `full_name`, `email`, `password`, `confirm_password` fields that map to the variables read in `signup()`.

Security notes:
- Passwords are hashed with `generate_password_hash` and verified with `check_password_hash` — passwords are not stored plaintext.
- Queries use `?` parameter placeholders to avoid SQL injection.
- `session["user_id"]` is the authentication marker; `login_required` checks it.
- DB connections are per-request (`g.db`) and closed after request to avoid leaks.

''' 

# Fix small accidental token at top of content ("@a pp.before_request")
content = content.replace("@a pp.before_request", "@app.before_request")

for para in content.split('\n\n'):
    doc.add_paragraph(para)

# Save document

doc.save(DOC_PATH)
print(f"Wrote: {DOC_PATH}")
''