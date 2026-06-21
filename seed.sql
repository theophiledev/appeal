-- Seed data for ULK Marks Appeal System
-- Run AFTER schema.sql

USE appeal_db;

-- ── HOD account (password: hod123) ─────────────────────────────────────────
INSERT IGNORE INTO admins (username, password, role) VALUES
    ('hod1', '5c8473579466adb756fa9e042efc8d7756217c5f4c950731fcf96bd65ba184e9', 'hod');

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
    ('2205000458', 'Database Management',    '85'),
    ('2205000458', 'Software Engineering',   '74'),
    ('2205000458', 'Networking',             '65'),
    ('2205000458', 'Web Development',        '82'),
    ('2205000459', 'Database Management',    '65'),
    ('2205000459', 'Software Engineering',   '80'),
    ('2205000459', 'Networking',             '57'),
    ('2205000459', 'Web Development',        '75'),
    ('2205000460', 'Database Management',    '52'),
    ('2205000460', 'Software Engineering',   '62'),
    ('2205000460', 'Networking',             '82'),
    ('2205000460', 'Web Development',        '45'),
    ('2205000461', 'Database Management',    '88'),
    ('2205000461', 'Software Engineering',   '92'),
    ('2205000461', 'Networking',             '78'),
    ('2205000461', 'Web Development',        '90'),
    ('2205000462', 'Database Management',    '57'),
    ('2205000462', 'Software Engineering',   '45'),
    ('2205000462', 'Networking',             '65'),
    ('2205000462', 'Web Development',        '30');

-- ── Sample appeals (for demo) ──────────────────────────────────────────────
INSERT IGNORE INTO appeals (student_id, module_name, reason, status_id, review_comment) VALUES
    ('2205000462', 'Web Development', 'I believe my final project was graded incorrectly. I submitted on time and met all requirements.', 1, NULL),
    ('2205000462', 'Software Engineering', 'My group contribution was rated unfairly by peers.', 1, NULL),
    ('2205000460', 'Web Development', 'I missed the exam due to sickness. I have a medical certificate.', 3, 'Medical certificate not submitted within the required 48-hour window.');
