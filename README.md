# Hospital Management (Admin + Staff + Patient Logins) - SQLite + Flask

## Roles
- **Admin**: creates staff (Doctor/Nurse/Radiologist) + patients, toggles staff availability
- **Doctor**: creates orders, assigns patients to **available** nurses/radiologists, views patient history
- **Nurse / Radiologist**: receives notifications when assigned, updates assignment status, adds reports and uploads scans/images/PDFs to patient record
- **Patient**: logs in and views their own orders, assignments, reports, and uploaded scans

## Run
```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

Open: http://127.0.0.1:5000

Default admin: `admin / admin123`

## Notes
- Uploaded files are saved to `./uploads/` and served at `/uploads/<filename>`
- This is a demo app (passwords use SHA256). For production, use bcrypt/argon2, HTTPS, and proper access controls.
