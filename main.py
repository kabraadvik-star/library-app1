from flask import Flask,request,redirect,url_for,session,flash,render_template_string
from werkzeug.security import generate_password_hash,check_password_hash
from datetime import date,timedelta
from functools import wraps
import sqlite3
import secrets
from pathlib import Path

app=Flask(__name__)
app.secret_key="library_app_secret_key_change_this"

BASE_DIR=Path(__file__).resolve().parent
DB_FILE=BASE_DIR/"library.db"

LIBRARIAN_USERNAME="librarian_avalon"
LIBRARIAN_PASSWORD="12345"

BORROW_DAYS=14
FINE_PER_DAY=5
MAX_BOOKS=3


# =========================================================
# DATABASE
# =========================================================

def get_db():
    con=sqlite3.connect(DB_FILE)
    con.row_factory=sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    con=get_db()

    con.execute("""
    CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        gr_number TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        grade TEXT NOT NULL,
        section TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        must_change_password INTEGER DEFAULT 1,
        created_at TEXT NOT NULL
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS books(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        category TEXT,
        isbn TEXT,
        status TEXT DEFAULT 'Available',
        created_at TEXT NOT NULL
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        return_date TEXT,
        fine INTEGER DEFAULT 0,
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(book_id) REFERENCES books(id)
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS reservations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        book_id INTEGER NOT NULL,
        reservation_date TEXT NOT NULL,
        collection_date TEXT NOT NULL,
        status TEXT DEFAULT 'Reserved',
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(book_id) REFERENCES books(id)
    )
    """)

    con.commit()
    con.close()


# =========================================================
# HELPERS
# =========================================================

def today():
    return date.today()


def calculate_fine(due_date):
    due=date.fromisoformat(due_date)
    days_late=max(0,(today()-due).days)
    return days_late*FINE_PER_DAY


def librarian_required(function):
    @wraps(function)
    def wrapper(*args,**kwargs):
        if session.get("role")!="librarian":
            return redirect(url_for("login"))
        return function(*args,**kwargs)
    return wrapper


def student_required(function):
    @wraps(function)
    def wrapper(*args,**kwargs):
        if session.get("role")!="student":
            return redirect(url_for("login"))
        return function(*args,**kwargs)
    return wrapper


# =========================================================
# CSS
# =========================================================

CSS="""
*{
    box-sizing:border-box;
}

body{
    margin:0;
    font-family:Arial,Helvetica,sans-serif;
    background:#f4f6f9;
    color:#172033;
}

a{
    text-decoration:none;
}

button{
    font-family:inherit;
}

.layout{
    min-height:100vh;
    display:flex;
}

.sidebar{
    width:245px;
    background:#111827;
    color:white;
    padding:24px 15px;
    position:fixed;
    left:0;
    top:0;
    bottom:0;
    display:flex;
    flex-direction:column;
}

.logo{
    display:flex;
    align-items:center;
    gap:12px;
    padding:5px 10px 30px;
}

.logo-icon{
    width:44px;
    height:44px;
    border-radius:12px;
    background:white;
    color:#111827;
    display:flex;
    justify-content:center;
    align-items:center;
    font-size:21px;
    font-weight:bold;
}

.logo-title{
    font-weight:bold;
    font-size:17px;
}

.logo-subtitle{
    color:#9ca3af;
    font-size:12px;
    margin-top:3px;
}

.nav{
    display:flex;
    flex-direction:column;
    gap:5px;
}

.nav a{
    color:#cbd5e1;
    padding:12px 13px;
    border-radius:9px;
    font-size:14px;
}

.nav a:hover{
    background:#1f2937;
    color:white;
}

.sidebar-bottom{
    margin-top:auto;
    border-top:1px solid #293344;
    padding-top:15px;
}

.sidebar-user{
    color:#9ca3af;
    font-size:12px;
    padding:0 12px 10px;
}

.logout{
    display:block;
    color:#cbd5e1;
    padding:10px 12px;
}

.logout:hover{
    color:white;
}

.main{
    margin-left:245px;
    width:calc(100% - 245px);
    padding:35px 42px;
}

.header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:25px;
}

.header h1{
    margin:5px 0;
    font-size:32px;
}

.header p{
    margin:0;
    color:#667085;
}

.eyebrow{
    color:#667085;
    font-size:11px;
    font-weight:bold;
    letter-spacing:1.5px;
}

.primary{
    background:#111827;
    color:white;
    border:0;
    border-radius:9px;
    padding:12px 17px;
    cursor:pointer;
    font-weight:bold;
    display:inline-block;
}

.primary:hover{
    background:#263142;
}

.secondary{
    background:white;
    border:1px solid #d7dce5;
    color:#344054;
    border-radius:9px;
    padding:11px 16px;
    display:inline-block;
}

.full{
    width:100%;
}

.stats{
    display:grid;
    grid-template-columns:repeat(6,1fr);
    gap:14px;
    margin-bottom:25px;
}

.stat{
    background:white;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:19px;
}

.stat small{
    display:block;
    color:#667085;
    margin-bottom:10px;
}

.stat strong{
    font-size:27px;
}

.card{
    background:white;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:22px;
    margin-bottom:20px;
}

.card-header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:15px;
}

.card-header h2{
    margin:0;
    font-size:19px;
}

.table-container{
    overflow-x:auto;
}

table{
    width:100%;
    border-collapse:collapse;
    min-width:700px;
}

th{
    text-align:left;
    padding:13px 10px;
    color:#667085;
    font-size:11px;
    text-transform:uppercase;
    border-bottom:1px solid #e5e7eb;
}

td{
    padding:14px 10px;
    border-bottom:1px solid #edf0f3;
    font-size:14px;
}

td small{
    display:block;
    color:#98a2b3;
    margin-top:3px;
}

.badge{
    display:inline-block;
    border-radius:30px;
    padding:5px 9px;
    font-size:11px;
    font-weight:bold;
}

.green{
    background:#e8f7ee;
    color:#147a4c;
}

.blue{
    background:#e9f1ff;
    color:#2457a6;
}

.orange{
    background:#fff2dd;
    color:#9a5c00;
}

.gray{
    background:#eef0f3;
    color:#667085;
}

.form-card{
    max-width:650px;
    background:white;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:28px;
}

.form-card label{
    display:block;
    font-weight:bold;
    font-size:14px;
    margin:14px 0 7px;
}

.form-card input,
.form-card select{
    width:100%;
    padding:12px;
    border:1px solid #d5dae3;
    border-radius:9px;
    font-size:15px;
    outline:none;
    background:white;
}

.form-card input:focus,
.form-card select:focus{
    border-color:#667085;
}

.form-buttons{
    display:flex;
    gap:10px;
    margin-top:20px;
}

.two{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:15px;
}

.search{
    display:flex;
    gap:10px;
    margin-bottom:20px;
}

.search input{
    flex:1;
    padding:12px;
    border:1px solid #d5dae3;
    border-radius:9px;
    font-size:15px;
}

.search button{
    border:0;
    background:#e9edf3;
    border-radius:9px;
    padding:0 18px;
    cursor:pointer;
}

.actions{
    display:flex;
    gap:10px;
    align-items:center;
}

.actions a{
    color:#344054;
}

.danger{
    background:none;
    border:0;
    color:#b42318;
    cursor:pointer;
}

.small-button{
    background:#111827;
    color:white;
    border:0;
    border-radius:7px;
    padding:7px 11px;
    cursor:pointer;
}

.empty{
    text-align:center;
    color:#98a2b3;
    padding:30px!important;
}

.flash-area{
    margin-bottom:20px;
}

.flash{
    padding:12px 15px;
    border-radius:9px;
    margin-bottom:8px;
    font-size:14px;
    font-weight:bold;
}

.flash.success{
    background:#e8f7ee;
    color:#147a4c;
}

.flash.error{
    background:#feeceb;
    color:#b42318;
}

.flash.info{
    background:#e9f1ff;
    color:#2457a6;
}

/* LOGIN */

.login-page{
    min-height:100vh;
    display:flex;
    justify-content:center;
    align-items:center;
    padding:25px;
    background:linear-gradient(135deg,#eef2f7,#ffffff);
}

.login-card{
    width:430px;
    max-width:100%;
    background:white;
    border:1px solid #e1e5eb;
    border-radius:20px;
    padding:40px;
    box-shadow:0 20px 50px rgba(0,0,0,.08);
}

.login-icon{
    width:60px;
    height:60px;
    background:#111827;
    color:white;
    border-radius:15px;
    display:flex;
    justify-content:center;
    align-items:center;
    font-size:27px;
    font-weight:bold;
    margin:0 auto 18px;
}

.login-school{
    text-align:center;
    color:#667085;
    font-size:11px;
    letter-spacing:2px;
    font-weight:bold;
}

.login-card h1{
    text-align:center;
    margin:8px 0;
    font-size:30px;
}

.login-card .description{
    text-align:center;
    color:#667085;
    margin-bottom:27px;
}

.login-card label{
    display:block;
    font-size:14px;
    font-weight:bold;
    margin:13px 0 7px;
}

.login-card input{
    width:100%;
    padding:13px;
    border:1px solid #d5dae3;
    border-radius:9px;
    font-size:15px;
}

.password-box{
    display:flex;
    border:1px solid #d5dae3;
    border-radius:9px;
    overflow:hidden;
}

.password-box input{
    border:0;
    border-radius:0;
    outline:none;
}

.password-box button{
    border:0;
    background:#f2f4f7;
    padding:0 13px;
    cursor:pointer;
}

.login-button{
    margin-top:20px;
    width:100%;
    padding:13px;
    background:#111827;
    color:white;
    border:0;
    border-radius:9px;
    font-weight:bold;
    font-size:15px;
    cursor:pointer;
}

.login-help{
    margin-top:20px;
    background:#f7f8fa;
    border-radius:9px;
    padding:13px;
    color:#667085;
    font-size:12px;
    line-height:1.6;
}

.success-card{
    max-width:650px;
    background:white;
    border:1px solid #e5e7eb;
    border-radius:16px;
    padding:40px;
    text-align:center;
}

.success-icon{
    width:55px;
    height:55px;
    border-radius:50%;
    background:#e8f7ee;
    color:#147a4c;
    display:flex;
    justify-content:center;
    align-items:center;
    font-size:25px;
    font-weight:bold;
    margin:0 auto 18px;
}

.credentials{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
    margin:25px 0;
}

.credential{
    background:#f5f7fa;
    padding:18px;
    border-radius:10px;
}

.credential small{
    display:block;
    color:#667085;
    margin-bottom:5px;
}

.credential strong{
    font-size:18px;
}

.book-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(230px,1fr));
    gap:18px;
}

.book-card{
    background:white;
    border:1px solid #e5e7eb;
    border-radius:15px;
    padding:22px;
}

.book-card h2{
    font-size:18px;
    margin:15px 0 5px;
}

.book-card p{
    color:#667085;
    margin:0 0 10px;
}

.book-card small{
    display:block;
    color:#98a2b3;
    margin-bottom:20px;
}

.book-icon{
    font-size:28px;
}

@media(max-width:1000px){
    .stats{
        grid-template-columns:repeat(3,1fr);
    }
}

@media(max-width:700px){
    .sidebar{
        position:static;
        width:100%;
    }

    .layout{
        display:block;
    }

    .main{
        margin-left:0;
        width:100%;
        padding:22px;
    }

    .stats{
        grid-template-columns:1fr 1fr;
    }

    .header{
        flex-direction:column;
        align-items:flex-start;
    }

    .two,
    .credentials{
        grid-template-columns:1fr;
    }

    .login-card{
        padding:28px;
    }
}
"""


# =========================================================
# TEMPLATE BASE
# =========================================================

BASE="""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{{ title|default("Library App") }}</title>
<style>
{{ css|safe }}
</style>
</head>

<body>

{% if session.get("role") %}

<div class="layout">

<aside class="sidebar">

<div class="logo">
<div class="logo-icon">L</div>
<div>
<div class="logo-title">Library App</div>
<div class="logo-subtitle">
{{ "Librarian" if session["role"]=="librarian" else "Student" }}
</div>
</div>
</div>

<div class="nav">

{% if session["role"]=="librarian" %}

<a href="{{ url_for('dashboard') }}">Dashboard</a>
<a href="{{ url_for('books') }}">Books</a>
<a href="{{ url_for('students') }}">Students</a>
<a href="{{ url_for('register_student') }}">Register Student</a>
<a href="{{ url_for('issue') }}">Issue Book</a>
<a href="{{ url_for('reservations') }}">Reservations</a>
<a href="{{ url_for('transactions') }}">Transactions</a>

{% else %}

<a href="{{ url_for('student_dashboard') }}">My Dashboard</a>
<a href="{{ url_for('student_books') }}">Browse Books</a>
<a href="{{ url_for('student_reservations') }}">My Reservations</a>
<a href="{{ url_for('student_history') }}">My History</a>
<a href="{{ url_for('change_password') }}">Change Password</a>

{% endif %}

</div>

<div class="sidebar-bottom">
<div class="sidebar-user">
{{ session.get("username",session.get("gr_number","")) }}
</div>
<a class="logout" href="{{ url_for('logout') }}">Log out</a>
</div>

</aside>

<main class="main">

<div class="flash-area">
{% with messages=get_flashed_messages(with_categories=true) %}
{% for category,message in messages %}
<div class="flash {{ category }}">{{ message }}</div>
{% endfor %}
{% endwith %}
</div>

{{ content|safe }}

</main>
</div>

{% else %}

<div class="flash-area">
{% with messages=get_flashed_messages(with_categories=true) %}
{% for category,message in messages %}
<div class="flash {{ category }}">{{ message }}</div>
{% endfor %}
{% endwith %}
</div>

{{ content|safe }}

{% endif %}

</body>
</html>
"""


def page(content,title="Library App"):
    return render_template_string(
        BASE,
        content=content,
        title=title,
        css=CSS
    )


# =========================================================
# LOGIN
# =========================================================

LOGIN="""
<div class="login-page">

<div class="login-card">

<div class="login-icon">L</div>

<div class="login-school">AVALON HEIGHTS</div>

<h1>Library App</h1>

<div class="description">
Sign in to access the school library.
</div>

<form method="POST">

<label>Username / GR Number</label>

<input
type="text"
name="username"
placeholder="Enter username or GR number"
required
autofocus
>

<label>Password</label>

<div class="password-box">

<input
id="password"
type="password"
name="password"
placeholder="Enter password"
required
>

<button type="button" onclick="showPassword()">
Show
</button>

</div>

<button class="login-button">
Sign in
</button>

</form>

<div class="login-help">
<b>Librarian:</b> use the librarian username and password.<br>
<b>Students:</b> use your GR number and student password.
</div>

</div>

</div>

<script>
function showPassword(){
    const input=document.getElementById("password");
    const button=document.querySelector(".password-box button");

    if(input.type==="password"){
        input.type="text";
        button.innerText="Hide";
    }else{
        input.type="password";
        button.innerText="Show";
    }
}
</script>
"""


@app.route("/login",methods=["GET","POST"])
def login():

    if session.get("role")=="librarian":
        return redirect(url_for("dashboard"))

    if session.get("role")=="student":
        return redirect(url_for("student_dashboard"))

    if request.method=="POST":

        username=request.form.get("username","").strip()
        password=request.form.get("password","")

        # LIBRARIAN
        if username==LIBRARIAN_USERNAME and password==LIBRARIAN_PASSWORD:

            session.clear()
            session["role"]="librarian"
            session["username"]=username

            return redirect(url_for("dashboard"))

        # STUDENT
        con=get_db()

        student=con.execute(
            "SELECT * FROM students WHERE gr_number=?",
            (username,)
        ).fetchone()

        con.close()

        if student and check_password_hash(
            student["password_hash"],
            password
        ):

            session.clear()
            session["role"]="student"
            session["student_id"]=student["id"]
            session["gr_number"]=student["gr_number"]

            if student["must_change_password"]:
                flash(
                    "Please change your temporary password.",
                    "info"
                )

                return redirect(
                    url_for("change_password")
                )

            return redirect(
                url_for("student_dashboard")
            )

        flash(
            "Invalid username/GR number or password.",
            "error"
        )

    return page(LOGIN,"Login")


@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


# =========================================================
# LIBRARIAN DASHBOARD
# =========================================================

@app.route("/")
@librarian_required
def dashboard():

    con=get_db()

    total_books=con.execute(
        "SELECT COUNT(*) c FROM books"
    ).fetchone()["c"]

    available=con.execute(
        "SELECT COUNT(*) c FROM books WHERE status='Available'"
    ).fetchone()["c"]

    borrowed=con.execute(
        "SELECT COUNT(*) c FROM books WHERE status='Borrowed'"
    ).fetchone()["c"]

    reserved=con.execute(
        "SELECT COUNT(*) c FROM books WHERE status='Reserved'"
    ).fetchone()["c"]

    students=con.execute(
        "SELECT COUNT(*) c FROM students"
    ).fetchone()["c"]

    loans=con.execute(
        "SELECT COUNT(*) c FROM transactions WHERE return_date IS NULL"
    ).fetchone()["c"]

    recent=con.execute("""
        SELECT
        t.*,
        s.name student_name,
        s.gr_number,
        b.title
        FROM transactions t
        JOIN students s ON s.id=t.student_id
        JOIN books b ON b.id=t.book_id
        ORDER BY t.id DESC
        LIMIT 8
    """).fetchall()

    con.close()

    content="""
    <div class="header">
    <div>
    <div class="eyebrow">LIBRARIAN</div>
    <h1>Dashboard</h1>
    <p>Overview of your school library.</p>
    </div>

    <a class="primary" href="{{ url_for('issue') }}">
    + Issue Book
    </a>
    </div>

    <div class="stats">

    <div class="stat">
    <small>Total Books</small>
    <strong>{{ total_books }}</strong>
    </div>

    <div class="stat">
    <small>Available</small>
    <strong>{{ available }}</strong>
    </div>

    <div class="stat">
    <small>Borrowed</small>
    <strong>{{ borrowed }}</strong>
    </div>

    <div class="stat">
    <small>Reserved</small>
    <strong>{{ reserved }}</strong>
    </div>

    <div class="stat">
    <small>Students</small>
    <strong>{{ students }}</strong>
    </div>

    <div class="stat">
    <small>Active Loans</small>
    <strong>{{ loans }}</strong>
    </div>

    </div>

    <div class="card">

    <div class="card-header">
    <h2>Recent Activity</h2>
    <a href="{{ url_for('transactions') }}">View all</a>
    </div>

    <div class="table-container">

    <table>

    <tr>
    <th>Student</th>
    <th>Book</th>
    <th>Issued</th>
    <th>Status</th>
    </tr>

    {% for row in recent %}

    <tr>

    <td>
    <b>{{ row.student_name }}</b>
    <small>{{ row.gr_number }}</small>
    </td>

    <td>{{ row.title }}</td>

    <td>{{ row.issue_date }}</td>

    <td>

    {% if row.return_date %}
    <span class="badge green">Returned</span>
    {% else %}
    <span class="badge blue">Borrowed</span>
    {% endif %}

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="4" class="empty">
    No transactions yet.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            total_books=total_books,
            available=available,
            borrowed=borrowed,
            reserved=reserved,
            students=students,
            loans=loans,
            recent=recent
        ),
        "Dashboard"
    )


# =========================================================
# BOOKS
# =========================================================

@app.route("/books")
@librarian_required
def books():

    q=request.args.get("q","").strip()

    con=get_db()

    if q:

        like="%"+q+"%"

        books=con.execute("""
            SELECT *
            FROM books
            WHERE title LIKE ?
            OR author LIKE ?
            OR category LIKE ?
            OR isbn LIKE ?
            ORDER BY title
        """,(like,like,like,like)).fetchall()

    else:

        books=con.execute(
            "SELECT * FROM books ORDER BY title"
        ).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">LIBRARY</div>
    <h1>Books</h1>
    <p>Manage the library collection.</p>
    </div>

    <a class="primary" href="{{ url_for('add_book') }}">
    + Add Book
    </a>

    </div>

    <form class="search" method="GET">

    <input
    name="q"
    value="{{ q }}"
    placeholder="Search title, author, category or ISBN"
    >

    <button>Search</button>

    </form>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>Book</th>
    <th>Author</th>
    <th>Category</th>
    <th>ISBN</th>
    <th>Status</th>
    <th>Actions</th>
    </tr>

    {% for book in books %}

    <tr>

    <td><b>{{ book.title }}</b></td>

    <td>{{ book.author }}</td>

    <td>{{ book.category or "—" }}</td>

    <td>{{ book.isbn or "—" }}</td>

    <td>

    {% if book.status=="Available" %}
    <span class="badge green">Available</span>

    {% elif book.status=="Reserved" %}
    <span class="badge orange">Reserved</span>

    {% else %}
    <span class="badge blue">Borrowed</span>
    {% endif %}

    </td>

    <td>

    <div class="actions">

    <a href="{{ url_for('edit_book',book_id=book.id) }}">
    Edit
    </a>

    {% if book.status=="Available" %}

    <form
    method="POST"
    action="{{ url_for('delete_book',book_id=book.id) }}"
    onsubmit="return confirm('Delete this book?')"
    >

    <button class="danger">
    Delete
    </button>

    </form>

    {% endif %}

    </div>

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="6" class="empty">
    No books found.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            books=books,
            q=q
        ),
        "Books"
    )


@app.route("/books/add",methods=["GET","POST"])
@librarian_required
def add_book():

    if request.method=="POST":

        title=request.form.get("title","").strip()
        author=request.form.get("author","").strip()
        category=request.form.get("category","").strip()
        isbn=request.form.get("isbn","").strip()

        if not title or not author:

            flash(
                "Book title and author are required.",
                "error"
            )

            return redirect(url_for("add_book"))

        con=get_db()

        con.execute("""
            INSERT INTO books
            (title,author,category,isbn,status,created_at)
            VALUES(?,?,?,?,?,?)
        """,(
            title,
            author,
            category,
            isbn,
            "Available",
            today().isoformat()
        ))

        con.commit()
        con.close()

        flash(
            "Book added successfully.",
            "success"
        )

        return redirect(url_for("books"))

    content="""
    <div class="header">
    <div>
    <div class="eyebrow">LIBRARY</div>
    <h1>Add Book</h1>
    </div>
    </div>

    <div class="form-card">

    <form method="POST">

    <label>Book Title</label>
    <input name="title" required>

    <label>Author</label>
    <input name="author" required>

    <label>Category</label>
    <input name="category">

    <label>ISBN</label>
    <input name="isbn">

    <div class="form-buttons">
    <a class="secondary" href="{{ url_for('books') }}">
    Cancel
    </a>

    <button class="primary">
    Add Book
    </button>
    </div>

    </form>

    </div>
    """

    return page(
        render_template_string(content),
        "Add Book"
    )


@app.route("/books/edit/<int:book_id>",methods=["GET","POST"])
@librarian_required
def edit_book(book_id):

    con=get_db()

    book=con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    if not book:

        con.close()
        return "Book not found",404

    if request.method=="POST":

        title=request.form.get("title","").strip()
        author=request.form.get("author","").strip()
        category=request.form.get("category","").strip()
        isbn=request.form.get("isbn","").strip()

        if not title or not author:

            con.close()

            flash(
                "Title and author are required.",
                "error"
            )

            return redirect(
                url_for("edit_book",book_id=book_id)
            )

        con.execute("""
            UPDATE books
            SET title=?,author=?,category=?,isbn=?
            WHERE id=?
        """,(
            title,
            author,
            category,
            isbn,
            book_id
        ))

        con.commit()
        con.close()

        flash(
            "Book updated.",
            "success"
        )

        return redirect(url_for("books"))

    con.close()

    content="""
    <div class="header">
    <div>
    <div class="eyebrow">LIBRARY</div>
    <h1>Edit Book</h1>
    </div>
    </div>

    <div class="form-card">

    <form method="POST">

    <label>Book Title</label>
    <input name="title" value="{{ book.title }}" required>

    <label>Author</label>
    <input name="author" value="{{ book.author }}" required>

    <label>Category</label>
    <input name="category" value="{{ book.category or '' }}">

    <label>ISBN</label>
    <input name="isbn" value="{{ book.isbn or '' }}">

    <div class="form-buttons">
    <a class="secondary" href="{{ url_for('books') }}">
    Cancel
    </a>

    <button class="primary">
    Save Changes
    </button>
    </div>

    </form>

    </div>
    """

    return page(
        render_template_string(
            content,
            book=book
        ),
        "Edit Book"
    )


@app.post("/books/delete/<int:book_id>")
@librarian_required
def delete_book(book_id):

    con=get_db()

    book=con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    if not book:

        con.close()
        return "Book not found",404

    history=con.execute(
        "SELECT COUNT(*) c FROM transactions WHERE book_id=?",
        (book_id,)
    ).fetchone()["c"]

    if book["status"]!="Available" or history>0:

        con.close()

        flash(
            "This book cannot be deleted.",
            "error"
        )

        return redirect(url_for("books"))

    con.execute(
        "DELETE FROM books WHERE id=?",
        (book_id,)
    )

    con.commit()
    con.close()

    flash(
        "Book deleted.",
        "success"
    )

    return redirect(url_for("books"))


# =========================================================
# STUDENTS
# =========================================================

@app.route("/students")
@librarian_required
def students():

    q=request.args.get("q","").strip()

    con=get_db()

    if q:

        like="%"+q+"%"

        students=con.execute("""
            SELECT
            s.*,
            (
                SELECT COUNT(*)
                FROM transactions t
                WHERE t.student_id=s.id
                AND t.return_date IS NULL
            ) active_books

            FROM students s

            WHERE s.gr_number LIKE ?
            OR s.name LIKE ?
            OR s.grade LIKE ?
            OR s.section LIKE ?

            ORDER BY s.gr_number
        """,(like,like,like,like)).fetchall()

    else:

        students=con.execute("""
            SELECT
            s.*,
            (
                SELECT COUNT(*)
                FROM transactions t
                WHERE t.student_id=s.id
                AND t.return_date IS NULL
            ) active_books

            FROM students s
            ORDER BY s.gr_number
        """).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENTS</div>
    <h1>Students</h1>
    <p>Manage GR-number based student accounts.</p>
    </div>

    <a class="primary" href="{{ url_for('register_student') }}">
    + Register Student
    </a>

    </div>

    <form class="search" method="GET">

    <input
    name="q"
    value="{{ q }}"
    placeholder="Search GR number, name, grade or section"
    >

    <button>Search</button>

    </form>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>GR Number</th>
    <th>Name</th>
    <th>Grade</th>
    <th>Section</th>
    <th>Books</th>
    <th>Account</th>
    </tr>

    {% for s in students %}

    <tr>

    <td><b>{{ s.gr_number }}</b></td>

    <td>{{ s.name }}</td>

    <td>{{ s.grade }}</td>

    <td>{{ s.section }}</td>

    <td>{{ s.active_books }}/{{ max_books }}</td>

    <td>

    {% if s.must_change_password %}

    <span class="badge orange">
    Password change required
    </span>

    {% else %}

    <span class="badge green">
    Active
    </span>

    {% endif %}

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="6" class="empty">
    No students found.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            students=students,
            q=q,
            max_books=MAX_BOOKS
        ),
        "Students"
    )


@app.route("/students/register",methods=["GET","POST"])
@librarian_required
def register_student():

    if request.method=="POST":

        gr=request.form.get("gr_number","").strip()
        name=request.form.get("name","").strip()
        grade=request.form.get("grade","").strip()
        section=request.form.get("section","").strip()

        if not all([gr,name,grade,section]):

            flash(
                "All fields are required.",
                "error"
            )

            return redirect(
                url_for("register_student")
            )

        con=get_db()

        existing=con.execute(
            "SELECT id FROM students WHERE gr_number=?",
            (gr,)
        ).fetchone()

        if existing:

            con.close()

            flash(
                "That GR number is already registered.",
                "error"
            )

            return redirect(
                url_for("register_student")
            )

        temporary_password=secrets.token_urlsafe(6)

        con.execute("""
            INSERT INTO students
            (
                gr_number,
                name,
                grade,
                section,
                password_hash,
                must_change_password,
                created_at
            )
            VALUES(?,?,?,?,?,?,?)
        """,(
            gr,
            name,
            grade,
            section,
            generate_password_hash(
                temporary_password
            ),
            1,
            today().isoformat()
        ))

        con.commit()
        con.close()

        content="""
        <div class="success-card">

        <div class="success-icon">
        ✓
        </div>

        <div class="eyebrow">
        ACCOUNT CREATED
        </div>

        <h1>{{ name }}</h1>

        <p>
        Give the student these login details.
        They must change the temporary password
        after their first login.
        </p>

        <div class="credentials">

        <div class="credential">
        <small>GR Number</small>
        <strong>{{ gr }}</strong>
        </div>

        <div class="credential">
        <small>Temporary Password</small>
        <strong>{{ temporary_password }}</strong>
        </div>

        </div>

        <a class="primary"
        href="{{ url_for('students') }}">
        Back to Students
        </a>

        </div>
        """

        return page(
            render_template_string(
                content,
                name=name,
                gr=gr,
                temporary_password=temporary_password
            ),
            "Student Created"
        )

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENT ACCOUNTS</div>
    <h1>Register Student</h1>
    <p>Create a student account using their GR number.</p>
    </div>

    </div>

    <div class="form-card">

    <form method="POST">

    <label>GR Number</label>
    <input name="gr_number" required>

    <label>Student Name</label>
    <input name="name" required>

    <div class="two">

    <div>
    <label>Grade</label>
    <input name="grade" required>
    </div>

    <div>
    <label>Section</label>
    <input name="section" required>
    </div>

    </div>

    <button class="primary">
    Create Student Account
    </button>

    </form>

    </div>
    """

    return page(
        render_template_string(content),
        "Register Student"
    )


# =========================================================
# ISSUE BOOK
# =========================================================

def issue_book_to_student(
    con,
    student_id,
    book_id
):

    book=con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    if not book:
        return False,"Book not found."

    if book["status"]!="Available":
        return False,"That book is not available."

    count=con.execute("""
        SELECT COUNT(*) c
        FROM transactions
        WHERE student_id=?
        AND return_date IS NULL
    """,(student_id,)).fetchone()["c"]

    if count>=MAX_BOOKS:
        return False,f"This student already has {MAX_BOOKS} books."

    duplicate=con.execute("""
        SELECT id
        FROM transactions
        WHERE student_id=?
        AND book_id=?
        AND return_date IS NULL
    """,(student_id,book_id)).fetchone()

    if duplicate:
        return False,"This student already has this book."

    issue_date=today()
    due_date=issue_date+timedelta(
        days=BORROW_DAYS
    )

    con.execute("""
        INSERT INTO transactions
        (
            student_id,
            book_id,
            issue_date,
            due_date,
            fine
        )
        VALUES(?,?,?,?,0)
    """,(
        student_id,
        book_id,
        issue_date.isoformat(),
        due_date.isoformat()
    ))

    con.execute("""
        UPDATE books
        SET status='Borrowed'
        WHERE id=?
    """,(book_id,))

    con.execute("""
        UPDATE reservations
        SET status='Collected'
        WHERE student_id=?
        AND book_id=?
        AND status='Reserved'
    """,(student_id,book_id))

    con.commit()

    return True,(
        "Book issued successfully. "
        f"Due date: {due_date.strftime('%d %b %Y')}."
    )


@app.route("/issue",methods=["GET","POST"])
@librarian_required
def issue():

    con=get_db()

    available=con.execute("""
        SELECT *
        FROM books
        WHERE status='Available'
        ORDER BY title
    """).fetchall()

    if request.method=="POST":

        gr=request.form.get("gr_number","").strip()
        book_id=request.form.get("book_id","")

        if not gr or not book_id:

            con.close()

            flash(
                "Enter a GR number and select a book.",
                "error"
            )

            return redirect(url_for("issue"))

        student=con.execute(
            "SELECT * FROM students WHERE gr_number=?",
            (gr,)
        ).fetchone()

        if not student:

            con.close()

            content="""
            <div class="header">

            <div>
            <div class="eyebrow">FIRST ISSUE</div>

            <h1>New Student</h1>

            <p>
            GR number <b>{{ gr }}</b>
            is not registered.
            Enter the student's details once.
            </p>

            </div>

            </div>

            <div class="form-card">

            <form method="POST"
            action="{{ url_for('first_issue') }}">

            <input
            type="hidden"
            name="gr_number"
            value="{{ gr }}"
            >

            <input
            type="hidden"
            name="book_id"
            value="{{ book_id }}"
            >

            <label>Student Name</label>
            <input name="name" required>

            <div class="two">

            <div>
            <label>Grade</label>
            <input name="grade" required>
            </div>

            <div>
            <label>Section</label>
            <input name="section" required>
            </div>

            </div>

            <button class="primary">
            Create Account & Issue Book
            </button>

            </form>

            </div>
            """

            return page(
                render_template_string(
                    content,
                    gr=gr,
                    book_id=book_id
                ),
                "First Issue"
            )

        ok,message=issue_book_to_student(
            con,
            student["id"],
            int(book_id)
        )

        con.close()

        flash(
            message,
            "success" if ok else "error"
        )

        return redirect(url_for("issue"))

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">BORROWING</div>
    <h1>Issue Book</h1>
    <p>
    Enter only the student's GR number.
    </p>
    </div>

    </div>

    <div class="form-card">

    <form method="POST">

    <label>Student GR Number</label>

    <input
    name="gr_number"
    placeholder="Enter GR number"
    required
    autofocus
    >

    <label>Book</label>

    <select name="book_id" required>

    <option value="">
    Select a book
    </option>

    {% for book in books %}

    <option value="{{ book.id }}">
    {{ book.title }} — {{ book.author }}
    </option>

    {% endfor %}

    </select>

    <button class="primary">
    Issue Book
    </button>

    </form>

    </div>
    """

    return page(
        render_template_string(
            content,
            books=available
        ),
        "Issue Book"
    )


@app.post("/issue/first")
@librarian_required
def first_issue():

    gr=request.form.get("gr_number","").strip()
    name=request.form.get("name","").strip()
    grade=request.form.get("grade","").strip()
    section=request.form.get("section","").strip()
    book_id=request.form.get("book_id","")

    if not all([gr,name,grade,section,book_id]):

        flash(
            "Fill in all student details.",
            "error"
        )

        return redirect(url_for("issue"))

    con=get_db()

    existing=con.execute(
        "SELECT id FROM students WHERE gr_number=?",
        (gr,)
    ).fetchone()

    if existing:

        con.close()

        flash(
            "That GR number already exists.",
            "error"
        )

        return redirect(url_for("issue"))

    temporary_password=secrets.token_urlsafe(6)

    cur=con.execute("""
        INSERT INTO students
        (
            gr_number,
            name,
            grade,
            section,
            password_hash,
            must_change_password,
            created_at
        )
        VALUES(?,?,?,?,?,?,?)
    """,(
        gr,
        name,
        grade,
        section,
        generate_password_hash(
            temporary_password
        ),
        1,
        today().isoformat()
    ))

    student_id=cur.lastrowid

    ok,message=issue_book_to_student(
        con,
        student_id,
        int(book_id)
    )

    if not ok:

        con.rollback()
        con.close()

        flash(
            message,
            "error"
        )

        return redirect(url_for("issue"))

    con.close()

    content="""
    <div class="success-card">

    <div class="success-icon">
    ✓
    </div>

    <div class="eyebrow">
    FIRST ISSUE COMPLETE
    </div>

    <h1>{{ name }}</h1>

    <p>{{ message }}</p>

    <div class="credentials">

    <div class="credential">
    <small>GR Number</small>
    <strong>{{ gr }}</strong>
    </div>

    <div class="credential">
    <small>Temporary Password</small>
    <strong>{{ temporary_password }}</strong>
    </div>

    </div>

    <p>
    Give this temporary password to the student.
    They must change it after their first login.
    </p>

    <a class="primary"
    href="{{ url_for('issue') }}">
    Issue Another Book
    </a>

    </div>
    """

    return page(
        render_template_string(
            content,
            name=name,
            gr=gr,
            temporary_password=temporary_password,
            message=message
        ),
        "First Issue Complete"
    )


# =========================================================
# RETURN / TRANSACTIONS
# =========================================================

@app.route("/transactions")
@librarian_required
def transactions():

    con=get_db()

    transactions=con.execute("""
        SELECT
        t.*,
        s.name student_name,
        s.gr_number,
        b.title
        FROM transactions t
        JOIN students s ON s.id=t.student_id
        JOIN books b ON b.id=t.book_id
        ORDER BY t.id DESC
    """).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">BORROWING</div>
    <h1>Transactions</h1>
    <p>All book issues and returns.</p>
    </div>

    </div>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>Student</th>
    <th>Book</th>
    <th>Issued</th>
    <th>Due</th>
    <th>Returned</th>
    <th>Fine</th>
    <th>Action</th>
    </tr>

    {% for t in transactions %}

    <tr>

    <td>
    <b>{{ t.student_name }}</b>
    <small>{{ t.gr_number }}</small>
    </td>

    <td>{{ t.title }}</td>

    <td>{{ t.issue_date }}</td>

    <td>{{ t.due_date }}</td>

    <td>
    {{ t.return_date or "Not returned" }}
    </td>

    <td>
    ₹{{ t.fine }}
    </td>

    <td>

    {% if not t.return_date %}

    <form
    method="POST"
    action="{{ url_for('return_book',transaction_id=t.id) }}"
    >

    <button class="small-button">
    Return
    </button>

    </form>

    {% else %}

    <span class="badge green">
    Completed
    </span>

    {% endif %}

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="7" class="empty">
    No transactions yet.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            transactions=transactions
        ),
        "Transactions"
    )


@app.post("/return/<int:transaction_id>")
@librarian_required
def return_book(transaction_id):

    con=get_db()

    transaction=con.execute(
        "SELECT * FROM transactions WHERE id=?",
        (transaction_id,)
    ).fetchone()

    if not transaction:

        con.close()
        return "Transaction not found",404

    if transaction["return_date"]:

        con.close()

        flash(
            "This book has already been returned.",
            "error"
        )

        return redirect(url_for("transactions"))

    fine=calculate_fine(
        transaction["due_date"]
    )

    con.execute("""
        UPDATE transactions
        SET return_date=?,fine=?
        WHERE id=?
    """,(
        today().isoformat(),
        fine,
        transaction_id
    ))

    con.execute("""
        UPDATE books
        SET status='Available'
        WHERE id=?
    """,(transaction["book_id"],))

    con.commit()
    con.close()

    flash(
        f"Book returned. Fine: ₹{fine}",
        "success"
    )

    return redirect(url_for("transactions"))


# =========================================================
# RESERVATIONS
# =========================================================

@app.route("/reservations")
@librarian_required
def reservations():

    con=get_db()

    reservations=con.execute("""
        SELECT
        r.*,
        s.name student_name,
        s.gr_number,
        b.title
        FROM reservations r
        JOIN students s ON s.id=r.student_id
        JOIN books b ON b.id=r.book_id
        ORDER BY r.id DESC
    """).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">RESERVATIONS</div>
    <h1>Reservations</h1>
    <p>Books reserved by students from home.</p>
    </div>

    </div>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>Student</th>
    <th>Book</th>
    <th>Reserved</th>
    <th>Collection</th>
    <th>Status</th>
    <th>Action</th>
    </tr>

    {% for r in reservations %}

    <tr>

    <td>
    <b>{{ r.student_name }}</b>
    <small>{{ r.gr_number }}</small>
    </td>

    <td>{{ r.title }}</td>

    <td>{{ r.reservation_date }}</td>

    <td>{{ r.collection_date }}</td>

    <td>
    <span class="badge
    {% if r.status=="Collected" %}
    green
    {% elif r.status=="Reserved" %}
    orange
    {% else %}
    gray
    {% endif %}
    ">
    {{ r.status }}
    </span>
    </td>

    <td>

    {% if r.status=="Reserved" %}

    <div class="actions">

    <form
    method="POST"
    action="{{ url_for('issue_reservation',reservation_id=r.id) }}"
    >

    <button class="small-button">
    Issue
    </button>

    </form>

    <form
    method="POST"
    action="{{ url_for('cancel_reservation',reservation_id=r.id) }}"
    >

    <button class="danger">
    Cancel
    </button>

    </form>

    </div>

    {% endif %}

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="6" class="empty">
    No reservations yet.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            reservations=reservations
        ),
        "Reservations"
    )


@app.post("/reservations/<int:reservation_id>/issue")
@librarian_required
def issue_reservation(reservation_id):

    con=get_db()

    reservation=con.execute(
        "SELECT * FROM reservations WHERE id=?",
        (reservation_id,)
    ).fetchone()

    if not reservation:

        con.close()

        flash(
            "Reservation not found.",
            "error"
        )

        return redirect(url_for("reservations"))

    if reservation["status"]!="Reserved":

        con.close()

        flash(
            "This reservation is no longer active.",
            "error"
        )

        return redirect(url_for("reservations"))

    ok,message=issue_book_to_student(
        con,
        reservation["student_id"],
        reservation["book_id"]
    )

    con.close()

    flash(
        message,
        "success" if ok else "error"
    )

    return redirect(url_for("reservations"))


@app.post("/reservations/<int:reservation_id>/cancel")
@librarian_required
def cancel_reservation(reservation_id):

    con=get_db()

    reservation=con.execute(
        "SELECT * FROM reservations WHERE id=?",
        (reservation_id,)
    ).fetchone()

    if reservation and reservation["status"]=="Reserved":

        con.execute("""
            UPDATE reservations
            SET status='Cancelled'
            WHERE id=?
        """,(reservation_id,))

        con.execute("""
            UPDATE books
            SET status='Available'
            WHERE id=?
            AND status='Reserved'
        """,(reservation["book_id"],))

        con.commit()

    con.close()

    flash(
        "Reservation cancelled.",
        "success"
    )

    return redirect(url_for("reservations"))


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student")
@student_required
def student_dashboard():

    con=get_db()

    student=con.execute(
        "SELECT * FROM students WHERE id=?",
        (session["student_id"],)
    ).fetchone()

    loans=con.execute("""
        SELECT
        t.*,
        b.title,
        b.author
        FROM transactions t
        JOIN books b ON b.id=t.book_id
        WHERE t.student_id=?
        AND t.return_date IS NULL
        ORDER BY t.due_date
    """,(student["id"],)).fetchall()

    reservations=con.execute("""
        SELECT
        r.*,
        b.title,
        b.author
        FROM reservations r
        JOIN books b ON b.id=r.book_id
        WHERE r.student_id=?
        ORDER BY r.id DESC
    """,(student["id"],)).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENT</div>

    <h1>
    Welcome, {{ student.name }}
    </h1>

    <p>
    GR {{ student.gr_number }}
    · Grade {{ student.grade }}
    · Section {{ student.section }}
    </p>

    </div>

    <a class="primary"
    href="{{ url_for('student_books') }}">
    Browse Books
    </a>

    </div>

    <div class="stats">

    <div class="stat">
    <small>Current Books</small>
    <strong>{{ loans|length }}/{{ max_books }}</strong>
    </div>

    <div class="stat">
    <small>Reservations</small>
    <strong>
    {{ reservations|selectattr("status","equalto","Reserved")|list|length }}
    </strong>
    </div>

    </div>

    <div class="card">

    <div class="card-header">
    <h2>My Current Books</h2>
    </div>

    <div class="table-container">

    <table>

    <tr>
    <th>Book</th>
    <th>Issued</th>
    <th>Due</th>
    <th>Current Fine</th>
    </tr>

    {% for book in loans %}

    <tr>

    <td>
    <b>{{ book.title }}</b>
    <small>{{ book.author }}</small>
    </td>

    <td>{{ book.issue_date }}</td>

    <td>{{ book.due_date }}</td>

    <td>
    ₹{{ calculate_fine(book.due_date) }}
    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="4" class="empty">
    You currently have no books.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            student=student,
            loans=loans,
            reservations=reservations,
            max_books=MAX_BOOKS,
            calculate_fine=calculate_fine
        ),
        "Student Dashboard"
    )


# =========================================================
# STUDENT BROWSE BOOKS
# =========================================================

@app.route("/student/books")
@student_required
def student_books():

    q=request.args.get("q","").strip()

    con=get_db()

    if q:

        like="%"+q+"%"

        books=con.execute("""
            SELECT *
            FROM books
            WHERE status='Available'
            AND
            (
                title LIKE ?
                OR author LIKE ?
                OR category LIKE ?
                OR isbn LIKE ?
            )
            ORDER BY title
        """,(like,like,like,like)).fetchall()

    else:

        books=con.execute("""
            SELECT *
            FROM books
            WHERE status='Available'
            ORDER BY title
        """).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENT</div>

    <h1>Browse Books</h1>

    <p>
    Reserve an available book for collection tomorrow.
    </p>

    </div>

    </div>

    <form class="search" method="GET">

    <input
    name="q"
    value="{{ q }}"
    placeholder="Search books"
    >

    <button>Search</button>

    </form>

    <div class="book-grid">

    {% for book in books %}

    <div class="book-card">

    <div class="book-icon">
    📚
    </div>

    <h2>{{ book.title }}</h2>

    <p>{{ book.author }}</p>

    <small>
    {{ book.category or "General" }}
    </small>

    <form
    method="POST"
    action="{{ url_for('reserve_book',book_id=book.id) }}"
    >

    <button class="primary full">
    Reserve for Tomorrow
    </button>

    </form>

    </div>

    {% else %}

    <div class="empty">
    No available books found.
    </div>

    {% endfor %}

    </div>
    """

    return page(
        render_template_string(
            content,
            books=books,
            q=q
        ),
        "Browse Books"
    )


# =========================================================
# STUDENT RESERVE
# =========================================================

@app.post("/student/reserve/<int:book_id>")
@student_required
def reserve_book(book_id):

    con=get_db()

    book=con.execute(
        "SELECT * FROM books WHERE id=?",
        (book_id,)
    ).fetchone()

    if not book or book["status"]!="Available":

        con.close()

        flash(
            "That book is no longer available.",
            "error"
        )

        return redirect(url_for("student_books"))

    student_id=session["student_id"]

    existing=con.execute("""
        SELECT id
        FROM reservations
        WHERE student_id=?
        AND book_id=?
        AND status='Reserved'
    """,(student_id,book_id)).fetchone()

    if existing:

        con.close()

        flash(
            "You already reserved this book.",
            "error"
        )

        return redirect(url_for("student_books"))

    tomorrow=today()+timedelta(days=1)

    con.execute("""
        INSERT INTO reservations
        (
            student_id,
            book_id,
            reservation_date,
            collection_date,
            status
        )
        VALUES(?,?,?,?,?)
    """,(
        student_id,
        book_id,
        today().isoformat(),
        tomorrow.isoformat(),
        "Reserved"
    ))

    con.execute("""
        UPDATE books
        SET status='Reserved'
        WHERE id=?
    """,(book_id,))

    con.commit()
    con.close()

    flash(
        "Book reserved successfully. "
        f"Collect it on {tomorrow.strftime('%d %b %Y')}.",
        "success"
    )

    return redirect(
        url_for("student_reservations")
    )


# =========================================================
# STUDENT RESERVATIONS
# =========================================================

@app.route("/student/reservations")
@student_required
def student_reservations():

    con=get_db()

    reservations=con.execute("""
        SELECT
        r.*,
        b.title,
        b.author
        FROM reservations r
        JOIN books b ON b.id=r.book_id
        WHERE r.student_id=?
        ORDER BY r.id DESC
    """,(session["student_id"],)).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENT</div>
    <h1>My Reservations</h1>
    </div>

    </div>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>Book</th>
    <th>Reserved</th>
    <th>Collection</th>
    <th>Status</th>
    </tr>

    {% for r in reservations %}

    <tr>

    <td>
    <b>{{ r.title }}</b>
    <small>{{ r.author }}</small>
    </td>

    <td>{{ r.reservation_date }}</td>

    <td>{{ r.collection_date }}</td>

    <td>

    {% if r.status=="Reserved" %}
    <span class="badge orange">Reserved</span>

    {% elif r.status=="Collected" %}
    <span class="badge green">Collected</span>

    {% else %}
    <span class="badge gray">{{ r.status }}</span>
    {% endif %}

    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="4" class="empty">
    No reservations.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            reservations=reservations
        ),
        "My Reservations"
    )


# =========================================================
# STUDENT HISTORY
# =========================================================

@app.route("/student/history")
@student_required
def student_history():

    con=get_db()

    transactions=con.execute("""
        SELECT
        t.*,
        b.title,
        b.author
        FROM transactions t
        JOIN books b ON b.id=t.book_id
        WHERE t.student_id=?
        ORDER BY t.id DESC
    """,(session["student_id"],)).fetchall()

    con.close()

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">STUDENT</div>
    <h1>Borrowing History</h1>
    </div>

    </div>

    <div class="card">

    <div class="table-container">

    <table>

    <tr>
    <th>Book</th>
    <th>Issued</th>
    <th>Due</th>
    <th>Returned</th>
    <th>Fine</th>
    </tr>

    {% for t in transactions %}

    <tr>

    <td>
    <b>{{ t.title }}</b>
    <small>{{ t.author }}</small>
    </td>

    <td>{{ t.issue_date }}</td>

    <td>{{ t.due_date }}</td>

    <td>
    {{ t.return_date or "Not returned" }}
    </td>

    <td>
    ₹{{ t.fine if t.return_date else calculate_fine(t.due_date) }}
    </td>

    </tr>

    {% else %}

    <tr>
    <td colspan="5" class="empty">
    No borrowing history.
    </td>
    </tr>

    {% endfor %}

    </table>

    </div>

    </div>
    """

    return page(
        render_template_string(
            content,
            transactions=transactions,
            calculate_fine=calculate_fine
        ),
        "Borrowing History"
    )


# =========================================================
# CHANGE PASSWORD
# =========================================================

@app.route("/student/change-password",methods=["GET","POST"])
@student_required
def change_password():

    if request.method=="POST":

        current=request.form.get(
            "current_password",
            ""
        )

        new=request.form.get(
            "new_password",
            ""
        )

        confirm=request.form.get(
            "confirm_password",
            ""
        )

        con=get_db()

        student=con.execute(
            "SELECT * FROM students WHERE id=?",
            (session["student_id"],)
        ).fetchone()

        if not check_password_hash(
            student["password_hash"],
            current
        ):

            con.close()

            flash(
                "Current password is incorrect.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        if len(new)<6:

            con.close()

            flash(
                "New password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        if new!=confirm:

            con.close()

            flash(
                "The passwords do not match.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )

        con.execute("""
            UPDATE students
            SET password_hash=?,
                must_change_password=0
            WHERE id=?
        """,(
            generate_password_hash(new),
            student["id"]
        ))

        con.commit()
        con.close()

        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(
            url_for("student_dashboard")
        )

    content="""
    <div class="header">

    <div>
    <div class="eyebrow">ACCOUNT</div>
    <h1>Change Password</h1>
    <p>Choose a password you will remember.</p>
    </div>

    </div>

    <div class="form-card">

    <form method="POST">

    <label>Current Password</label>
    <input
    type="password"
    name="current_password"
    required
    >

    <label>New Password</label>
    <input
    type="password"
    name="new_password"
    minlength="6"
    required
    >

    <label>Confirm New Password</label>
    <input
    type="password"
    name="confirm_password"
    minlength="6"
    required
    >

    <button class="primary">
    Change Password
    </button>

    </form>

    </div>
    """

    return page(
        render_template_string(content),
        "Change Password"
    )


# =========================================================
# START
# =========================================================

if __name__=="__main__":

    init_db()

    print()
    print("======================================")
    print("        LIBRARY APP")
    print("======================================")
    print("Librarian username: librarian_avalon")
    print("Librarian password: 12345")
    print("Website: http://127.0.0.1:5000")
    print("======================================")
    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )