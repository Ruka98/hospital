PRAGMA foreign_keys = ON;

-- Patients can login and view their own history
CREATE TABLE IF NOT EXISTS patients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  phone TEXT,
  dob TEXT,
  gender TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- All hospital staff (admins, doctors, nurses, radiologists, etc.)
CREATE TABLE IF NOT EXISTS staff (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  role TEXT NOT NULL,                -- admin | doctor | nurse | radiologist
  category TEXT,                     -- specialty / department (e.g., Cardiologist, ICU Nurse, CT Radiology)
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  phone TEXT,
  is_available INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Doctor-created clinical orders (kept for backward compatibility / patient view)
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  doctor_id INTEGER NOT NULL,         -- staff.id where role='doctor'
  order_type TEXT NOT NULL,           -- ECG / Cardio / Physio / etc.
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'Pending',
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  FOREIGN KEY(doctor_id) REFERENCES staff(id) ON DELETE CASCADE
);

-- Doctor assignments to other staff (nurses / radiologists, etc.)
CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  doctor_id INTEGER NOT NULL,
  assignee_staff_id INTEGER NOT NULL, -- staff.id (nurse / radiologist)
  task_type TEXT NOT NULL,            -- CT Scan / X-Ray / Nursing Care / ECG / etc.
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'Assigned', -- Assigned | In Progress | Completed
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  FOREIGN KEY(doctor_id) REFERENCES staff(id) ON DELETE CASCADE,
  FOREIGN KEY(assignee_staff_id) REFERENCES staff(id) ON DELETE CASCADE
);

-- Notifications for staff (e.g., when assigned)
CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  staff_id INTEGER NOT NULL,
  message TEXT NOT NULL,
  is_read INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(staff_id) REFERENCES staff(id) ON DELETE CASCADE
);

-- Reports added by nurses / radiologists (and doctors, if needed)
CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL,
  created_by_staff_id INTEGER NOT NULL,
  report_type TEXT NOT NULL,          -- Report / Scan Result / Note / etc.
  report_text TEXT,
  image_filename TEXT,               -- optional uploaded scan/image
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY(patient_id) REFERENCES patients(id) ON DELETE CASCADE,
  FOREIGN KEY(created_by_staff_id) REFERENCES staff(id) ON DELETE CASCADE
);
