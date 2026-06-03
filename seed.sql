-- Seed data for ULK Marks Appeal System
-- Run AFTER schema.sql

USE appeal_db;

-- ── HOD account (password: hod123) ─────────────────────────────────────────
INSERT IGNORE INTO admins (username, password, role) VALUES
    ('hod1', '9d0c0e42ceb28abd8f9acc6d094f4f7f4a886b5a6f5e0a4b8c7d6e5f4a3b2c1d', 'hod');

-- ── Sample students ────────────────────────────────────────────────────────
INSERT IGNORE INTO students (student_id, name, phone) VALUES
    ('2205000458', 'BIKORIMANA Jean Baptiste', '+250780000001'),
    ('2205000459', 'KAMANA Alice',            '+250780000002'),
    ('2205000460', 'HABIMANA Eric',           '+250780000003'),
    ('2205000461', 'UWERA Diane',             '+250780000004'),
    ('2205000462', 'NTIBIRINGWA Peter',       '+250780000005');

-- ── PIN credentials (PIN: 1234 for all students) ───────────────────────────
-- SHA-256 of "1234" = 03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4
INSERT IGNORE INTO pin_credentials (student_id, pin_hash, failed_attempts, locked) VALUES
    ('2205000458', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 0, 0),
    ('2205000459', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 0, 0),
    ('2205000460', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 0, 0),
    ('2205000461', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 0, 0),
    ('2205000462', '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4', 0, 0);

-- ── Marks / Results ────────────────────────────────────────────────────────
INSERT IGNORE INTO marks (student_id, module_name, mark) VALUES
    ('2205000458', 'Database Management',    'A'),
    ('2205000458', 'Software Engineering',   'B+'),
    ('2205000458', 'Networking',             'B'),
    ('2205000458', 'Web Development',        'A-'),
    ('2205000459', 'Database Management',    'B'),
    ('2205000459', 'Software Engineering',   'A-'),
    ('2205000459', 'Networking',             'C+'),
    ('2205000459', 'Web Development',        'B+'),
    ('2205000460', 'Database Management',    'C'),
    ('2205000460', 'Software Engineering',   'B'),
    ('2205000460', 'Networking',             'A-'),
    ('2205000460', 'Web Development',        'D'),
    ('2205000461', 'Database Management',    'A'),
    ('2205000461', 'Software Engineering',   'A'),
    ('2205000461', 'Networking',             'B+'),
    ('2205000461', 'Web Development',        'A'),
    ('2205000462', 'Database Management',    'C+'),
    ('2205000462', 'Software Engineering',   'D'),
    ('2205000462', 'Networking',             'B'),
    ('2205000462', 'Web Development',        'F');

-- ── Sample appeals (for demo) ──────────────────────────────────────────────
INSERT IGNORE INTO appeals (student_id, module_name, reason, status_id) VALUES
    ('2205000462', 'Web Development', 'I believe my final project was graded incorrectly. I submitted on time and met all requirements.', 1),
    ('2205000462', 'Software Engineering', 'My group contribution was rated unfairly by peers.', 1),
    ('2205000460', 'Web Development', 'I missed the exam due to sickness. I have a medical certificate.', 1);
