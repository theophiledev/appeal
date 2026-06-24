-- Migration: Persistent OTP store (survives server restarts & multi-worker)
CREATE TABLE IF NOT EXISTS otp_store (
    phone    VARCHAR(20)   PRIMARY KEY,
    otp      VARCHAR(6)    NOT NULL,
    expires  DATETIME      NOT NULL,
    INDEX idx_expires (expires)
) ENGINE=InnoDB;
