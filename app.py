
from flask import Flask, render_template, request
import sqlite3

from datetime import datetime

import qrcode

import secrets

app = Flask(__name__)


# Connect to the database
def get_db_connection():
    connection = sqlite3.connect("attendance.db")
    connection.row_factory = sqlite3.Row
    return connection



# Create the students and courses tables
def create_table():
    connection = get_db_connection()

    # Students table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            matric_number TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL,
            level TEXT NOT NULL
        )
    """)

    # Courses table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_code TEXT NOT NULL UNIQUE,
            course_title TEXT NOT NULL,
            lecturer TEXT NOT NULL,
            schedule TEXT NOT NULL
        )
    """)
    
    # Attendance records table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            attendance_time TEXT NOT NULL,

            FOREIGN KEY (student_id) REFERENCES students(id),
            FOREIGN KEY (course_id) REFERENCES courses(id),

            UNIQUE (student_id, course_id, attendance_date)
        )
    """)

 
    # QR attendance sessions table
    connection.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        )
    """)
   


    connection.commit()
    connection.close()




# Homepage and dashboard
@app.route("/")
def home():
    connection = get_db_connection()

    total_students = connection.execute(
        "SELECT COUNT(*) FROM students"
    ).fetchone()[0]

    total_courses = connection.execute(
        "SELECT COUNT(*) FROM courses"
    ).fetchone()[0]

    total_attendance = connection.execute(
        "SELECT COUNT(*) FROM attendance"
    ).fetchone()[0]

    connection.close()

    return render_template(
        "index.html",
        total_students=total_students,
        total_courses=total_courses,
        total_attendance=total_attendance
    )


# Register a student
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        full_name = request.form["full_name"].strip()
        matric_number = request.form["matric_number"].strip()
        department = request.form["department"].strip()
        level = request.form["level"]

        if not all([
            full_name,
            matric_number,
            department,
            level
        ]):
            return "Please fill in every field.", 400

        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO students (
                    full_name,
                    matric_number,
                    department,
                    level
                )
                VALUES (?, ?, ?, ?)
            """, (
                full_name,
                matric_number,
                department,
                level
            ))

            connection.commit()

            return """
                <h2>Student registered successfully!</h2>
                <p><a href="/register">Register another student</a></p>
                <p><a href="/students">View registered students</a></p>
                <p><a href="/">Back to dashboard</a></p>
            """

        except sqlite3.IntegrityError:
            return """
                <h2>Registration unsuccessful</h2>
                <p>This matriculation number may already be registered.</p>
                <p><a href="/register">Try again</a></p>
            """, 409

        finally:
            connection.close()

    return render_template("register.html")


# View all registered students
@app.route("/students")
def students():
    connection = get_db_connection()

    all_students = connection.execute("""
        SELECT * FROM students
        ORDER BY full_name
    """).fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=all_students
    )

# Course management
@app.route("/courses", methods=["GET", "POST"])
def courses():

    if request.method == "POST":
        course_code = request.form["course_code"].strip().upper()
        course_title = request.form["course_title"].strip()
        lecturer = request.form["lecturer"].strip()
        schedule = request.form["schedule"].strip()

        if not all([
            course_code,
            course_title,
            lecturer,
            schedule
        ]):
            return "Please fill in every course field.", 400

        connection = get_db_connection()

        try:
            connection.execute("""
                INSERT INTO courses (
                    course_code,
                    course_title,
                    lecturer,
                    schedule
                )
                VALUES (?, ?, ?, ?)
            """, (
                course_code,
                course_title,
                lecturer,
                schedule
            ))

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()
            return """
                <h2>Course already exists</h2>
                <p>That course code is already registered.</p>
                <p><a href="/courses">Return to courses</a></p>
            """, 409

        finally:
            if connection:
                connection.close()

    connection = get_db_connection()

    all_courses = connection.execute("""
        SELECT * FROM courses
        ORDER BY course_code
    """).fetchall()

    connection.close()

    return render_template(
        "courses.html",
        courses=all_courses
    )


# Record and view attendance
@app.route("/attendance", methods=["GET", "POST"])
def attendance():

    connection = get_db_connection()
    message = ""

    if request.method == "POST":
        student_id = request.form["student_id"]
        course_id = request.form["course_id"]

        student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        course = connection.execute(
            "SELECT id FROM courses WHERE id = ?",
            (course_id,)
        ).fetchone()

        if student is None or course is None:
            message = "Please select a valid student and course."

        else:
            now = datetime.now()
            attendance_date = now.strftime("%Y-%m-%d")
            attendance_time = now.strftime("%H:%M:%S")

            try:
                connection.execute("""
                    INSERT INTO attendance (
                        student_id,
                        course_id,
                        attendance_date,
                        attendance_time
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    student_id,
                    course_id,
                    attendance_date,
                    attendance_time
                ))

                connection.commit()
                message = "Attendance recorded successfully!"

            except sqlite3.IntegrityError:
                message = (
                    "Attendance has already been recorded "
                    "for this student and course today."
                )

    all_students = connection.execute("""
        SELECT id, full_name, matric_number
        FROM students
        ORDER BY full_name
    """).fetchall()

    all_courses = connection.execute("""
        SELECT id, course_code, course_title
        FROM courses
        ORDER BY course_code
    """).fetchall()

    records = connection.execute("""
        SELECT
            students.full_name,
            students.matric_number,
            courses.course_code,
            attendance.attendance_date,
            attendance.attendance_time
        FROM attendance
        JOIN students
            ON attendance.student_id = students.id
        JOIN courses
            ON attendance.course_id = courses.id
        ORDER BY attendance.id DESC
    """).fetchall()

    connection.close()

    return render_template(
        "attendance.html",
        students=all_students,
        courses=all_courses,
        records=records,
        message=message
    )



# QR code page
@app.route("/generate_qr", methods=["GET", "POST"])
def generate_qr():
    import os
    from datetime import timedelta

    connection = get_db_connection()
    message = ""
    qr_image = None
    qr_link = None

    if request.method == "POST":
        course_id = request.form.get("course_id")

        course = connection.execute(
            "SELECT id, course_code, course_title FROM courses WHERE id = ?",
            (course_id,)
        ).fetchone()

        if course is None:
            message = "Please select a valid course."
        else:
            now = datetime.now()
            token = secrets.token_urlsafe(24)
            expires_at = now + timedelta(minutes=15)

            connection.execute("""
                UPDATE attendance_sessions
                SET active = 0
                WHERE course_id = ?
            """, (course_id,))

            cursor = connection.execute("""
                INSERT INTO attendance_sessions
                (course_id, token, created_at, expires_at, active)
                VALUES (?, ?, ?, ?, 1)
            """, (
                course_id,
                token,
                now.isoformat(timespec="seconds"),
                expires_at.isoformat(timespec="seconds")
            ))

            connection.commit()
            session_id = cursor.lastrowid

            os.makedirs("static/qrcodes", exist_ok=True)
            image_name = f"session_{session_id}.png"
            image_path = os.path.join("static", "qrcodes", image_name)

            qr_link = "https://attendease-9fi6.onrender.com/checkin/" + token

            qr = qrcode.make(qr_link)
            qr.save(image_path)

            qr_image = image_name
            message = (
                f"QR code created for {course['course_code']} - "
                f"{course['course_title']}. It expires in 15 minutes."
            )

    all_courses = connection.execute("""
        SELECT id, course_code, course_title
        FROM courses
        ORDER BY course_code
    """).fetchall()

    connection.close()

    return render_template(
        "generate_qr.html",
        courses=all_courses,
        message=message,
        qr_image=qr_image,
        qr_link=qr_link
    )


@app.route("/checkin/<token>", methods=["GET", "POST"])
def checkin(token):
    connection = get_db_connection()
    message = ""
    valid_session = False

    try:
        session = connection.execute("""
            SELECT id, course_id, expires_at, active
            FROM attendance_sessions
            WHERE token = ?
        """, (token,)).fetchone()

        if session is None or session["active"] != 1:
            message = "This QR code is invalid or no longer active."
        elif datetime.fromisoformat(session["expires_at"]) < datetime.now():
            connection.execute("""
                UPDATE attendance_sessions
                SET active = 0
                WHERE id = ?
            """, (session["id"],))
            connection.commit()
            message = "This QR code has expired. Please ask the lecturer for a new one."
        else:
            valid_session = True

            course = connection.execute("""
                SELECT course_code, course_title
                FROM courses
                WHERE id = ?
            """, (session["course_id"],)).fetchone()

            if request.method == "POST":
                matric_number = request.form.get(
                    "matric_number", ""
                ).strip()

                student = connection.execute("""
                    SELECT id, full_name
                    FROM students
                    WHERE matric_number = ?
                """, (matric_number,)).fetchone()

                if student is None:
                    message = "Student not found. Check your matric number."
                else:
                    now = datetime.now()

                    try:
                        connection.execute("""
                            INSERT INTO attendance
                            (student_id, course_id, attendance_date, attendance_time)
                            VALUES (?, ?, ?, ?)
                        """, (
                            student["id"],
                            session["course_id"],
                            now.strftime("%Y-%m-%d"),
                            now.strftime("%H:%M:%S")
                        ))
                        connection.commit()
                        message = (
                            "Attendance recorded successfully for "
                            + student["full_name"] + "!"
                        )
                    except sqlite3.IntegrityError:
                        message = "Attendance has already been recorded for this course today."

    finally:
        connection.close()

    return render_template(
        "checkin.html",
        message=message,
        valid_session=valid_session
    )


create_table()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)