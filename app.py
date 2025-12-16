from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import sqlite3
from pathlib import Path
import hashlib
from werkzeug.utils import secure_filename
import os

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "hospital.db"
UPLOAD_DIR = APP_DIR / "uploads"
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_pw(pw: str) -> str:
    # Demo only. For real systems use bcrypt/argon2 + HTTPS + strong secrets.
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def require_role(role: str):
    if session.get("role") != role:
        # If user is staff but logged in, they might have access if admin
        if session.get("role") == "admin":
             return None
        return redirect(url_for("home"))
    return None

def require_staff_role(role: str):
    if session.get("role") != role:
        if session.get("role") == "admin":
            return None # Admins can access staff routes
        return redirect(url_for("home"))
    return None

def require_any_staff():
    if not session.get("role") or session.get("role") == "patient":
        return redirect(url_for("staff_login"))
    return None

app = Flask(__name__)
app.secret_key = "CHANGE_ME_TO_A_RANDOM_SECRET_KEY"
UPLOAD_DIR.mkdir(exist_ok=True)

@app.route("/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)

# ---------------- Home / Auth ----------------
@app.route("/")
def home():
    role = session.get("role")
    if role == "admin":
        return redirect(url_for("admin_dashboard"))
    if role == "doctor":
        return redirect(url_for("doctor_dashboard"))
    if role == "nurse":
        return redirect(url_for("nurse_dashboard"))
    if role == "radiologist":
        return redirect(url_for("radiologist_dashboard"))
    if role == "patient":
        return redirect(url_for("patient_dashboard"))
    return render_template("choose_login.html", title="Choose Login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/login/staff", methods=["GET","POST"])
def staff_login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = db()
        # Query generic staff table
        row = conn.execute(
            "SELECT id, username, password_hash, role FROM staff WHERE username=?",
            (username,),
        ).fetchone()
        conn.close()

        if row and row["password_hash"] == hash_pw(password):
            session["role"] = row["role"]
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            return redirect(url_for(f"{row['role']}_dashboard"))

        flash("Invalid staff credentials")
    return render_template("login.html", title="Staff Login", role="staff")

@app.route("/login/patient", methods=["GET","POST"])
def patient_login():
    if request.method == "POST":
        username = request.form.get("username","").strip()
        password = request.form.get("password","")
        conn = db()
        row = conn.execute("SELECT id, username, password_hash FROM patients WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and row["password_hash"] == hash_pw(password):
            session["role"] = "patient"
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            return redirect(url_for("patient_dashboard"))
        flash("Invalid patient credentials")
    return render_template("login.html", title="Patient Login", role="patient")

# ---------------- Admin ----------------
@app.route("/admin")
def admin_dashboard():
    r = require_role("admin")
    if r: return r
    conn = db()
    staff = conn.execute("SELECT * FROM staff ORDER BY id DESC").fetchall()
    patients = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    recent_assignments = conn.execute("""
        SELECT a.*, p.name AS patient_name, d.name AS doctor_name, s.name AS assignee_name, s.role AS assignee_role
        FROM assignments a
        JOIN patients p ON p.id = a.patient_id
        JOIN staff d ON d.id = a.doctor_id
        JOIN staff s ON s.id = a.assignee_staff_id
        ORDER BY a.id DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return render_template(
        "admin_dashboard.html",
        title="Admin Dashboard",
        staff=staff,
        patients=patients,
        recent_assignments=recent_assignments,
    )

@app.post("/admin/staff/create")
def admin_create_staff():
    r = require_role("admin")
    if r: return r
    name = request.form.get("name","").strip()
    role = request.form.get("role","").strip()
    # Robust category handling: trust hidden input first (JS), fall back to manual reconstruction
    category = request.form.get("category","").strip()
    if not category or category == "Other":
        cat_select = request.form.get("category_select","").strip()
        cat_other = request.form.get("category_other","").strip()
        if cat_select == "Other" and cat_other:
            category = cat_other
        elif cat_select and cat_select != "Other":
            category = cat_select

    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    phone = request.form.get("phone","").strip()
    is_available = 1 if request.form.get("is_available") == "on" else 0

    # Updated to allow admin creation
    if role not in ("admin", "doctor","nurse","radiologist"):
        flash("Role must be admin, doctor, nurse, or radiologist")
        return redirect(url_for("admin_dashboard"))
    if not (name and username and password):
        flash("Name, username, password are required")
        return redirect(url_for("admin_dashboard"))
    conn = db()
    try:
        conn.execute(
            "INSERT INTO staff (name, role, category, username, password_hash, phone, is_available) VALUES (?,?,?,?,?,?,?)",
            (name, role, category, username, hash_pw(password), phone, is_available),
        )
        conn.commit()
        flash("Staff account created")
    except sqlite3.IntegrityError:
        flash("Username already exists")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/patient/create")
def admin_create_patient():
    r = require_role("admin")
    if r: return r
    name = request.form.get("name","").strip()
    username = request.form.get("username","").strip()
    password = request.form.get("password","")
    phone = request.form.get("phone","").strip()
    dob = request.form.get("dob","").strip()
    gender = request.form.get("gender","").strip()
    if not (name and username and password):
        flash("Name, username, password are required")
        return redirect(url_for("admin_dashboard"))
    conn = db()
    try:
        conn.execute(
            "INSERT INTO patients (name, username, password_hash, phone, dob, gender) VALUES (?,?,?,?,?,?)",
            (name, username, hash_pw(password), phone, dob, gender),
        )
        conn.commit()
        flash("Patient account created")
    except sqlite3.IntegrityError:
        flash("Username already exists")
    finally:
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/staff/toggle-availability/<int:staff_id>")
def admin_toggle_availability(staff_id):
    r = require_role("admin")
    if r: return r
    conn = db()
    row = conn.execute("SELECT is_available FROM staff WHERE id=?", (staff_id,)).fetchone()
    if row:
        new_val = 0 if row["is_available"] else 1
        conn.execute("UPDATE staff SET is_available=? WHERE id=?", (new_val, staff_id))
        conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/staff/delete/<int:staff_id>")
def admin_delete_staff(staff_id):
    r = require_role("admin")
    if r: return r
    conn = db()
    conn.execute("DELETE FROM staff WHERE id=?", (staff_id,))
    conn.commit()
    conn.close()
    flash("Staff deleted")
    return redirect(url_for("admin_dashboard"))

@app.post("/admin/patient/delete/<int:patient_id>")
def admin_delete_patient(patient_id):
    r = require_role("admin")
    if r: return r
    conn = db()
    conn.execute("DELETE FROM patients WHERE id=?", (patient_id,))
    conn.commit()
    conn.close()
    flash("Patient deleted")
    return redirect(url_for("admin_dashboard"))

# ---------------- Doctor ----------------
@app.route("/doctor")
def doctor_dashboard():
    r = require_staff_role("doctor")
    if r: return r
    doctor_id = session["user_id"]
    conn = db()
    doctor = conn.execute("SELECT * FROM staff WHERE id=? AND role='doctor'", (doctor_id,)).fetchone()
    patients = conn.execute("SELECT * FROM patients ORDER BY id DESC").fetchall()
    nurses = conn.execute("SELECT * FROM staff WHERE role='nurse' AND is_available=1 ORDER BY name").fetchall()
    radiologists = conn.execute("SELECT * FROM staff WHERE role='radiologist' AND is_available=1 ORDER BY name").fetchall()

    recent_orders = conn.execute("""
        SELECT o.*, p.name AS patient_name
        FROM orders o
        JOIN patients p ON p.id=o.patient_id
        WHERE o.doctor_id=?
        ORDER BY o.id DESC
        LIMIT 200
    """, (doctor_id,)).fetchall()

    recent_assignments = conn.execute("""
        SELECT a.*, p.name AS patient_name, s.name AS assignee_name, s.role AS assignee_role
        FROM assignments a
        JOIN patients p ON p.id=a.patient_id
        JOIN staff s ON s.id=a.assignee_staff_id
        WHERE a.doctor_id=?
        ORDER BY a.id DESC
        LIMIT 200
    """, (doctor_id,)).fetchall()

    notifications = conn.execute("""
        SELECT * FROM notifications
        WHERE staff_id=?
        ORDER BY id DESC
        LIMIT 50
    """, (doctor_id,)).fetchall()

    conn.close()
    return render_template(
        "doctor_dashboard.html",
        title="Doctor Dashboard",
        doctor=doctor,
        patients=patients,
        nurses=nurses,
        radiologists=radiologists,
        recent_orders=recent_orders,
        recent_assignments=recent_assignments,
        notifications=notifications,
    )

@app.post("/doctor/orders/create")
def doctor_create_order():
    r = require_staff_role("doctor")
    if r: return r
    doctor_id = session["user_id"]
    patient_id = int(request.form.get("patient_id","0") or 0)
    order_type = request.form.get("order_type","").strip()
    notes = request.form.get("notes","").strip()
    if not (patient_id and order_type):
        flash("Patient + order type are required")
        return redirect(url_for("doctor_dashboard"))
    conn = db()
    conn.execute(
        "INSERT INTO orders (patient_id, doctor_id, order_type, notes) VALUES (?,?,?,?)",
        (patient_id, doctor_id, order_type, notes),
    )
    conn.commit()
    conn.close()
    flash("Order created")
    return redirect(url_for("doctor_dashboard"))

@app.post("/doctor/assignments/create")
def doctor_create_assignment():
    r = require_staff_role("doctor")
    if r: return r
    doctor_id = session["user_id"]
    patient_id = int(request.form.get("patient_id","0") or 0)
    assignee_staff_id = int(request.form.get("assignee_staff_id","0") or 0)
    task_type = request.form.get("task_type","").strip()
    notes = request.form.get("notes","").strip()

    if not (patient_id and assignee_staff_id and task_type):
        flash("Patient + assignee + task type are required")
        return redirect(url_for("doctor_dashboard"))

    conn = db()
    assignee = conn.execute(
        "SELECT id, role, name FROM staff WHERE id=? AND is_available=1",
        (assignee_staff_id,),
    ).fetchone()
    if not assignee or assignee["role"] not in ("nurse","radiologist"):
        conn.close()
        flash("Assignee must be an available nurse or radiologist")
        return redirect(url_for("doctor_dashboard"))

    conn.execute(
        "INSERT INTO assignments (patient_id, doctor_id, assignee_staff_id, task_type, notes) VALUES (?,?,?,?,?)",
        (patient_id, doctor_id, assignee_staff_id, task_type, notes),
    )

    msg = f"New assignment: {task_type} (Patient ID {patient_id})"
    conn.execute("INSERT INTO notifications (staff_id, message) VALUES (?,?)", (assignee_staff_id, msg))

    conn.commit()
    conn.close()
    flash("Ticket created (assignee notified)")
    return redirect(url_for("doctor_dashboard"))

@app.get("/doctor/patient/<int:patient_id>")
def doctor_view_patient(patient_id):
    r = require_staff_role("doctor")
    if r: return r
    conn = db()
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()
    if not patient:
        conn.close()
        flash("Patient not found")
        return redirect(url_for("doctor_dashboard"))

    orders = conn.execute("""
        SELECT o.*, d.name AS doctor_name
        FROM orders o
        JOIN staff d ON d.id=o.doctor_id
        WHERE o.patient_id=?
        ORDER BY o.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    assignments = conn.execute("""
        SELECT a.*, d.name AS doctor_name, s.name AS assignee_name, s.role AS assignee_role
        FROM assignments a
        JOIN staff d ON d.id=a.doctor_id
        JOIN staff s ON s.id=a.assignee_staff_id
        WHERE a.patient_id=?
        ORDER BY a.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    reports = conn.execute("""
        SELECT r.*, s.name AS staff_name, s.role AS staff_role
        FROM reports r
        JOIN staff s ON s.id=r.created_by_staff_id
        WHERE r.patient_id=?
        ORDER BY r.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    conn.close()
    return render_template(
        "patient_history.html",
        title="Patient History",
        patient=patient,
        orders=orders,
        assignments=assignments,
        reports=reports,
    )

# ---------------- Nurse & Radiologist ----------------
def _staff_dashboard(role: str, title: str, template_name: str):
    r = require_staff_role(role)
    if r: return r
    staff_id = session["user_id"]
    conn = db()
    me = conn.execute("SELECT * FROM staff WHERE id=? AND role=?", (staff_id, role)).fetchone()

    notifications = conn.execute("""
        SELECT * FROM notifications
        WHERE staff_id=?
        ORDER BY id DESC
        LIMIT 200
    """, (staff_id,)).fetchall()

    assignments = conn.execute("""
        SELECT a.*, p.name AS patient_name, d.name AS doctor_name
        FROM assignments a
        JOIN patients p ON p.id=a.patient_id
        JOIN staff d ON d.id=a.doctor_id
        WHERE a.assignee_staff_id=?
        ORDER BY a.id DESC
        LIMIT 300
    """, (staff_id,)).fetchall()

    conn.close()
    return render_template(
        template_name,
        title=title,
        me=me,
        notifications=notifications,
        assignments=assignments,
    )

@app.route("/nurse")
def nurse_dashboard():
    return _staff_dashboard("nurse", "Nurse Dashboard", "nurse_dashboard.html")

@app.route("/radiologist")
def radiologist_dashboard():
    return _staff_dashboard("radiologist", "Radiologist Dashboard", "radiologist_dashboard.html")

@app.post("/staff/notifications/mark-read/<int:notif_id>")
def staff_mark_notification_read(notif_id):
    role = session.get("role")
    if role not in ("nurse","radiologist","doctor"):
        return redirect(url_for("home"))
    staff_id = session.get("user_id")
    conn = db()
    conn.execute("UPDATE notifications SET is_read=1 WHERE id=? AND staff_id=?", (notif_id, staff_id))
    conn.commit()
    conn.close()
    return redirect(url_for(f"{role}_dashboard"))

@app.post("/staff/assignments/update-status/<int:assignment_id>")
def staff_update_assignment_status(assignment_id):
    role = session.get("role")
    if role not in ("nurse","radiologist"):
        return redirect(url_for("home"))
    staff_id = session.get("user_id")
    status = request.form.get("status","Assigned").strip()
    if status not in ("Assigned","In Progress","Completed"):
        status = "Assigned"
    conn = db()
    # Fetch assignment details first if we need to notify
    assignment = conn.execute(
        "SELECT * FROM assignments WHERE id=? AND assignee_staff_id=?",
        (assignment_id, staff_id)
    ).fetchone()

    if assignment:
        conn.execute(
            "UPDATE assignments SET status=? WHERE id=? AND assignee_staff_id=?",
            (status, assignment_id, staff_id),
        )

        if status == "Completed":
            # Notify Doctor
            doc_msg = f"Task '{assignment['task_type']}' for patient #{assignment['patient_id']} was completed."
            conn.execute("INSERT INTO notifications (staff_id, message) VALUES (?,?)", (assignment['doctor_id'], doc_msg))

            # Notify Patient
            pat_msg = f"Your task '{assignment['task_type']}' has been completed."
            conn.execute("INSERT INTO patient_notifications (patient_id, message) VALUES (?,?)", (assignment['patient_id'], pat_msg))

        conn.commit()
        flash("Ticket status updated")
    else:
        flash("Assignment not found or access denied")

    conn.close()
    return redirect(url_for(f"{role}_dashboard"))

def _save_upload(file_storage):
    if not file_storage or not getattr(file_storage, "filename", ""):
        return None
    filename = secure_filename(file_storage.filename)
    if not filename:
        return None
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        return None
    base = os.path.splitext(filename)[0]
    i = 0
    out_name = filename
    while (UPLOAD_DIR / out_name).exists():
        i += 1
        out_name = f"{base}_{i}{ext}"
    file_storage.save(UPLOAD_DIR / out_name)
    return out_name

@app.post("/staff/reports/create")
def staff_create_report():
    role = session.get("role")
    if role not in ("nurse","radiologist"):
        return redirect(url_for("home"))
    staff_id = session.get("user_id")
    patient_id = int(request.form.get("patient_id","0") or 0)
    report_type = request.form.get("report_type","").strip() or ("Scan Result" if role=="radiologist" else "Report")
    report_text = request.form.get("report_text","").strip()
    image_filename = _save_upload(request.files.get("image_file"))

    if not patient_id:
        flash("Patient is required")
        return redirect(url_for(f"{role}_dashboard"))

    conn = db()
    conn.execute(
        "INSERT INTO reports (patient_id, created_by_staff_id, report_type, report_text, image_filename) VALUES (?,?,?,?,?)",
        (patient_id, staff_id, report_type, report_text, image_filename),
    )
    conn.commit()
    conn.close()
    flash("Report added to patient record")
    return redirect(url_for(f"{role}_dashboard"))

# ---------------- Patient ----------------
@app.route("/patient")
def patient_dashboard():
    r = require_role("patient")
    if r: return r
    patient_id = session["user_id"]
    conn = db()
    patient = conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()

    my_orders = conn.execute("""
        SELECT o.*, d.name AS doctor_name, d.category AS doctor_specialty
        FROM orders o
        JOIN staff d ON d.id = o.doctor_id
        WHERE o.patient_id = ?
        ORDER BY o.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    my_assignments = conn.execute("""
        SELECT a.*, d.name AS doctor_name, s.name AS assignee_name, s.role AS assignee_role
        FROM assignments a
        JOIN staff d ON d.id=a.doctor_id
        JOIN staff s ON s.id=a.assignee_staff_id
        WHERE a.patient_id=?
        ORDER BY a.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    my_reports = conn.execute("""
        SELECT r.*, s.name AS staff_name, s.role AS staff_role
        FROM reports r
        JOIN staff s ON s.id=r.created_by_staff_id
        WHERE r.patient_id=?
        ORDER BY r.id DESC
        LIMIT 300
    """, (patient_id,)).fetchall()

    notifications = conn.execute("""
        SELECT * FROM patient_notifications
        WHERE patient_id=?
        ORDER BY id DESC
        LIMIT 50
    """, (patient_id,)).fetchall()

    conn.close()
    return render_template(
        "patient_dashboard.html",
        title="Patient Dashboard",
        patient=patient,
        my_orders=my_orders,
        my_assignments=my_assignments,
        my_reports=my_reports,
        notifications=notifications,
    )

@app.post("/patient/notifications/mark-read/<int:notif_id>")
def patient_mark_notification_read(notif_id):
    r = require_role("patient")
    if r: return r
    patient_id = session["user_id"]
    conn = db()
    conn.execute("UPDATE patient_notifications SET is_read=1 WHERE id=? AND patient_id=?", (notif_id, patient_id))
    conn.commit()
    conn.close()
    return redirect(url_for("patient_dashboard"))

if __name__ == "__main__":
    app.run(debug=True)
