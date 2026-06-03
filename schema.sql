-- ULK Marks Appeal System - Database Schema
-- Run this script to create the required MySQL database and tables.

CREATE DATABASE IF NOT EXISTS appeal_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE appeal_db;

-- ── Admins / HOD accounts ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admins (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    username   VARCHAR(100) NOT NULL UNIQUE,
    password   VARCHAR(64)  NOT NULL,   -- SHA-256 hex hash
    role       ENUM('admin','hod') NOT NULL DEFAULT 'admin',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Students ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
    student_id VARCHAR(50)  PRIMARY KEY,
    name       VARCHAR(150) NOT NULL,
    phone      VARCHAR(20)  NOT NULL
) ENGINE=InnoDB;

-- ── Marks / Results ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS marks (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  VARCHAR(50)  NOT NULL,
    module_name VARCHAR(150) NOT NULL,
    mark        VARCHAR(10)  NOT NULL,
    updated_by  VARCHAR(100) DEFAULT NULL,
    updated_at  DATETIME     DEFAULT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Appeal status lookup ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appeal_status (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    status_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
INSERT IGNORE INTO appeal_status (id, status_name) VALUES
    (1, 'Pending'),
    (2, 'Approved'),
    (3, 'Rejected');

-- ── Appeals ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS appeals (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    student_id     VARCHAR(50)  NOT NULL,
    module_name    VARCHAR(150) NOT NULL,
    reason         TEXT         NOT NULL,
    status_id      INT          NOT NULL DEFAULT 1,
    reviewed_by    VARCHAR(100) DEFAULT NULL,
    review_comment TEXT         DEFAULT NULL,
    created_at     DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (status_id)  REFERENCES appeal_status(id)
) ENGINE=InnoDB;

-- ── Student PIN credentials ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pin_credentials (
    student_id      VARCHAR(50) PRIMARY KEY,
    pin_hash        VARCHAR(64) NOT NULL,
    failed_attempts INT         NOT NULL DEFAULT 0,
    locked          TINYINT(1)  NOT NULL DEFAULT 0,
    created_at      DATETIME    DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ── Access audit log ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS access_audit (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_id  VARCHAR(50)  DEFAULT NULL,
    phone       VARCHAR(20)  DEFAULT NULL,
    action      VARCHAR(50)  NOT NULL,
    success     TINYINT(1)   NOT NULL DEFAULT 0,
    timestamp   DATETIME     DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ── Default admin account (password: admin123) ─────────────────────────────
INSERT IGNORE INTO admins (username, password, role) VALUES
    ('admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin');
