-- Create an admin user (SQLite)
-- Prefer: run `python init_db.py` which creates admin/admin123.

-- Example: username=admin2, password=MyPass123
-- SHA256("MyPass123") = 7b81987a9f4c3c4b1d971b4b6c38c0b41c6bdcbe0bff0d2c5c3f49eb5c1b6e42

INSERT INTO admins (username, password_hash)
VALUES ('admin2', '7b81987a9f4c3c4b1d971b4b6c38c0b41c6bdcbe0bff0d2c5c3f49eb5c1b6e42');
