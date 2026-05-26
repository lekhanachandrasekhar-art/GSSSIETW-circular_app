from flask import Flask, render_template, redirect, request, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
import pandas as pd
from datetime import date
from werkzeug.utils import secure_filename

# -------------------------------
# LOAD EXCEL DATASETS
# -------------------------------

students_df = pd.read_excel('students.xlsx')
faculty_df = pd.read_excel('faculty.xlsx')

# -------------------------------
# CREATE FLASK APP
# -------------------------------

app = Flask(__name__)

app.secret_key = 'CIRCULARXAI'

# -------------------------------
# MYSQL CONFIG
# -------------------------------

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Jayanagar@14'
app.config['MYSQL_DB'] = 'CIRCULARXAI'

# -------------------------------
# UPLOAD FOLDER
# -------------------------------

UPLOAD_FOLDER = os.path.join('static', 'uploads')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# MYSQL CONNECTION
# -------------------------------

mysql = MySQL(app)

# -------------------------------
# HOME PAGE
# -------------------------------

@app.route('/')
def home():

    return render_template('index.html')

# -------------------------------
# LOGIN
# -------------------------------


@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        # GET LOGIN ID
        user_id = request.form.get('id')

        # CHECK EMPTY

        user_id = user_id.strip()

        # -------------------------------
        # STUDENT LOGIN
        # -------------------------------

        student = students_df[
            students_df['usn'].astype(str).str.strip() == user_id
        ]

        if not student.empty:

            session['user_id'] = student.iloc[0]['usn']
            session['name'] = student.iloc[0]['name']
            session['branch'] = student.iloc[0]['branch']
            session['post'] = "Student"
            session['role'] = 'Student'

            return redirect('/student')

        # -------------------------------
        # FACULTY LOGIN
        # -------------------------------

        faculty = faculty_df[
            faculty_df['faculty_code'].astype(str).str.strip() == user_id
        ]

        if not faculty.empty:

            session['user_id'] = faculty.iloc[0]['faculty_code']
            session['name'] = faculty.iloc[0]['name']
            session['branch'] = faculty.iloc[0]['branch']
            session['post'] = faculty.iloc[0]['post']
            session['role'] = 'Faculty'

            return redirect('/faculty')

        return "Invalid Login ID"

    return render_template('login.html')

# -------------------------------
# FACULTY DASHBOARD
# -------------------------------

@app.route('/faculty')
def faculty_dashboard():
    if session.get('role') != 'Faculty':
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # GET HIDDEN PINS OF CURRENT USER
    cursor.execute("""
        SELECT circular_id
        FROM hidden_pins
        WHERE user_id = %s
    """, (
        session.get('user_id'),
    ))

    hidden_data = cursor.fetchall()

    # STORE ONLY IDS
    hidden_pins = []

    for row in hidden_data:

        hidden_pins.append(row['circular_id'])

    # MAIN QUERY
    cursor.execute("""
SELECT circulars.*,

CASE
    WHEN read_status.circular_id IS NULL THEN 0
    ELSE 1
END AS is_read,

CASE
    WHEN hidden_pins.circular_id IS NULL THEN 0
    ELSE 1
END AS is_hidden

FROM circulars

LEFT JOIN read_status
ON circulars.id = read_status.circular_id
AND read_status.user_id = %s

LEFT JOIN hidden_pins
ON circulars.id = hidden_pins.circular_id
AND hidden_pins.user_id = %s

WHERE circulars.status='active'

ORDER BY
is_read ASC,
circulars.upload_date DESC
""",
(
    session['user_id'],
    session['user_id']
))
    

    circulars = cursor.fetchall()

    # REMOVE ONLY PIN DISPLAY FOR THIS USER
    filtered_circulars = []

    for circular in circulars:

        # HIDE ONLY IF:
        # 1. circular is pinned
        # 2. user removed it

       if circular['id'] in hidden_pins:
            circular['is_pinned'] = 0
            continue
    filtered_circulars = []

    for circular in circulars:

    # IF USER REMOVED PIN
    # SHOW AS NORMAL CIRCULAR

        if circular['id'] in hidden_pins:

            circular['is_pinned'] = 0


        filtered_circulars.append(circular)

    return render_template(
        'faculty_dashboard.html',
        circulars=filtered_circulars
    )
# -------------------------------
# STUDENT DASHBOARD
# -------------------------------

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'Student':
        return redirect('/login')
    

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    # GET HIDDEN PINS OF CURRENT USER
    cursor.execute("""
        SELECT circular_id
        FROM hidden_pins
        WHERE user_id = %s
    """, (
        session.get('user_id'),
    ))

    hidden_data = cursor.fetchall()

    # STORE ONLY IDS
    hidden_pins = []

    for row in hidden_data:

        hidden_pins.append(row['circular_id'])


    cursor.execute("""
SELECT circulars.*,

CASE
    WHEN read_status.circular_id IS NULL THEN 0
    ELSE 1
END AS is_read,

CASE
    WHEN hidden_pins.circular_id IS NULL THEN 0
    ELSE 1
END AS is_hidden

FROM circulars

LEFT JOIN read_status
ON circulars.id = read_status.circular_id
AND read_status.user_id = %s

LEFT JOIN hidden_pins
ON circulars.id = hidden_pins.circular_id
AND hidden_pins.user_id = %s

WHERE circulars.status='active'

ORDER BY
is_read ASC,
circulars.upload_date DESC
""",
(
    session['user_id'],
    session['user_id']
))
    circulars = cursor.fetchall()

    return render_template(
        'student.html',
        circulars=circulars
    )

# -------------------------------
# UPLOAD PAGE
# -------------------------------

@app.route('/upload', methods=['GET', 'POST'])
def upload():

    if request.method == 'POST':

        title = request.form['title']
        description = request.form['description']
        department = request.form['department']
        access_type = request.form['access_type']

        file = request.files.get('attachment')

        filename = ""

        # ONLY SAVE FILE IF USER SELECTED ONE
        if file and file.filename != "":

            # CREATE FOLDER IF NOT EXISTS
            os.makedirs('static/uploads', exist_ok=True)

            filename = file.filename

            save_path = os.path.join('static/uploads', filename)

            file.save(save_path)

        cursor = mysql.connection.cursor()

        cursor.execute("""
            INSERT INTO circulars
            (
                title,
                description,
                department,
                access_type,
                attachment_path,
                uploader_name,
                uploader_department
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            title,
            description,
            department,
            access_type,
            filename,
            session['name'],
            session['branch']
        ))

        mysql.connection.commit()

        return redirect('/faculty')

    return render_template('upload.html')

# -------------------------------
# SEARCH
# -------------------------------

@app.route('/search')
def search():

    keyword = request.args.get('search')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
    SELECT *
    FROM circulars
    WHERE
    title LIKE %s
    OR description LIKE %s
    OR department LIKE %s
    """

    value = "%" + keyword + "%"

    cursor.execute(
        query,
        (value, value, value)
    )
    mysql.connection.commit()

    results = cursor.fetchall()

    return render_template(
        'faculty_dashboard.html',
        circulars=results
    )

# -------------------------------
# FILTER BY DEPARTMENT
# -------------------------------

@app.route('/filter/<department>')
def filter_department(department):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT circulars.*,

    CASE
        WHEN read_status.circular_id IS NULL THEN 0
        ELSE 1
    END AS is_read

    FROM circulars

    LEFT JOIN read_status
    ON circulars.id = read_status.circular_id
    AND read_status.user_id = %s

    WHERE circulars.department=%s
    """,
    (
        session['user_id'],
        department
    ))

    circulars = cursor.fetchall()

    if session['role'] == 'Student':

        return render_template(
        'student.html',
        circulars=circulars
    )

    return render_template(
    'faculty_dashboard.html',
    circulars=circulars
)

# -------------------------------
# FILTER BY MONTH
# -------------------------------

@app.route('/month/<month>')
def month_filter(month):

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
    SELECT *
    FROM circulars
    WHERE MONTHNAME(upload_date)=%s
    """

    cursor.execute(query,(month,))

    results = cursor.fetchall()

    if session['role'] == 'Student':

        return render_template(
        'student.html',
        circulars=results
    )

    return render_template(
    'faculty_dashboard.html',
    circulars=results
)

# -------------------------------
# MARK AS READ
# -------------------------------

@app.route('/mark_read/<int:id>')
def mark_read(id):

    if not session.get('user_id'):
        return redirect('/login')

    cursor = mysql.connection.cursor()

    # CHECK already exists
    cursor.execute("""
    SELECT *
    FROM read_status
    WHERE user_id=%s
    AND circular_id=%s
    """,
    (
        session['user_id'],
        id
    ))

    existing = cursor.fetchone()

    # INSERT ONLY IF NOT EXISTS
    if not existing:

        cursor.execute("""
        INSERT INTO read_status(user_id, circular_id)
        VALUES(%s,%s)
        """,
        (
            session['user_id'],
            id
        ))

        mysql.connection.commit()

    if session.get('role') == 'Student':
        return redirect('/student')

    return redirect('/faculty')

# -------------------------------
# SAVE CIRCULAR
# -------------------------------

@app.route('/save/<int:id>')
def save(id):

    if not session.get('user_id'):
        return redirect('/login')

    cursor = mysql.connection.cursor()

    # CHECK already exists
    cursor.execute("""
    SELECT *
    FROM bookmarks
    WHERE user_id=%s
    AND circular_id=%s
    """,
    (
        session['user_id'],
        id
    ))

    existing = cursor.fetchone()

    # INSERT ONLY IF NOT EXISTS
    if not existing:

        cursor.execute("""
        INSERT INTO bookmarks(user_id, circular_id)
        VALUES(%s,%s)
        """,
        (
            session['user_id'],
            id
        ))

        mysql.connection.commit()

    if session.get('role') == 'Student':
        return redirect('/student')

    return redirect('/faculty')
# -------------------------------
# READ PAGE
# -------------------------------

@app.route('/read')
def read():

    if not session.get('user_id'):
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT circulars.*,

    1 AS is_read,

    CASE
        WHEN hidden_pins.circular_id IS NULL THEN 0
        ELSE 1
    END AS is_hidden

    FROM circulars

    JOIN read_status
    ON circulars.id = read_status.circular_id

    LEFT JOIN hidden_pins
    ON circulars.id = hidden_pins.circular_id
    AND hidden_pins.user_id = %s

    WHERE read_status.user_id=%s

    ORDER BY circulars.upload_date DESC
    """,
    (
        session['user_id'],
        session['user_id']
    ))

    circulars = cursor.fetchall()

    if session['role'] == 'Student':

        return render_template(
            'student.html',
            circulars=circulars
        )

    return render_template(
        'faculty_dashboard.html',
        circulars=circulars
    )
# -------------------------------
# SAVED PAGE
# -------------------------------

@app.route('/saved')
def saved():

    if not session.get('user_id'):
        return redirect('/login')

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT circulars.*,

    CASE
        WHEN read_status.circular_id IS NULL THEN 0
        ELSE 1
    END AS is_read,

    CASE
        WHEN hidden_pins.circular_id IS NULL THEN 0
        ELSE 1
    END AS is_hidden

    FROM circulars

    JOIN bookmarks
    ON circulars.id = bookmarks.circular_id

    LEFT JOIN read_status
    ON circulars.id = read_status.circular_id
    AND read_status.user_id = %s

    LEFT JOIN hidden_pins
    ON circulars.id = hidden_pins.circular_id
    AND hidden_pins.user_id = %s

    WHERE bookmarks.user_id=%s

    ORDER BY is_read ASC,
    circulars.upload_date DESC
    """,
    (
        session['user_id'],
        session['user_id'],
        session['user_id']
    ))

    circulars = cursor.fetchall()

    if session['role'] == 'Student':

        return render_template(
            'student.html',
            circulars=circulars
        )

    return render_template(
        'faculty_dashboard.html',
        circulars=circulars
    )
# -------------------------------
# HISTORY PAGE
# -------------------------------

@app.route('/history')
def history():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    SELECT *
    FROM circulars
    WHERE status='archived'
    ORDER BY upload_date DESC
    """)

    circulars = cursor.fetchall()

    return render_template(
        'faculty_dashboard.html',
        circulars=circulars
    )

# -------------------------------
# CHECK EXPIRY
# -------------------------------

@app.route('/check_expiry')
def check_expiry():

    today = date.today()

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute("""
    UPDATE circulars
    SET status='archived'
    WHERE expiry_date < %s
    """,
    (
        today,
    ))

    mysql.connection.commit()

    return "Expired Circulars Archived"

# -------------------------------
# ANALYTICS
# -------------------------------

@app.route('/analytics')
def analytics():

    cursor = mysql.connection.cursor()

    cursor.execute("""
    SELECT department, COUNT(*)
    FROM circulars
    GROUP BY department
    """)

    data = cursor.fetchall()

    return render_template(
        'analytics.html',
        data=data
    )

# -------------------------------
# NOTIFICATIONS
# -------------------------------

@app.route('/notifications')
def notifications():

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # TOTAL NEW CIRCULARS

    cursor.execute("""
    SELECT COUNT(*) AS total
    FROM circulars
    WHERE status='active'
    """)

    total_result = cursor.fetchone()

    total = total_result['total']

    # IMPORTANT CIRCULARS

    cursor.execute("""
    SELECT COUNT(*) AS important_count
    FROM circulars
    WHERE is_pinned=1
    """)

    important_result = cursor.fetchone()

    important = important_result['important_count']

    return render_template(
        'notifications.html',
        total=total,
        important=important
    )
# -----hide pin------
@app.route('/hide_pin/<int:circular_id>')
def hide_pin(circular_id):

    if 'user_id' not in session:
        return redirect('/login')

    cursor = mysql.connection.cursor()

    # CHECK already hidden or not
    cursor.execute("""
    SELECT *
    FROM hidden_pins
    WHERE user_id=%s
    AND circular_id=%s
    """,
    (
        session['user_id'],
        circular_id
    ))

    existing = cursor.fetchone()

    # INSERT ONLY IF NOT EXISTS
    if not existing:

        cursor.execute("""
        INSERT INTO hidden_pins(user_id, circular_id)
        VALUES(%s,%s)
        """,
        (
            session['user_id'],
            circular_id
        ))

        mysql.connection.commit()

    # REDIRECT BASED ON ROLE
    if session['role'] == 'Student':
        return redirect('/student')

    return redirect('/faculty')

# -------------------------------
# RUN APP
# -------------------------------

if __name__ == '__main__':

    app.run(debug=True)