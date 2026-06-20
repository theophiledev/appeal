"""
USSD helpers and simulator for the ULK Marks Appeal System.
"""
import hashlib
import random
import string
from datetime import datetime, timedelta

import MySQLdb.cursors

# ── In-memory OTP store (use Redis in production) ───────────────────────────
_otp_store: dict = {}

MAX_PIN_ATTEMPTS = 3


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _ussd(text):
    return text, 200, {'Content-Type': 'text/plain'}


def _main_menu() -> str:
    return (
        "CON Dear Student, welcome to ULK Marks Appeal System.\n"
        "Please select an option:\n"
        "1. View my marks\n"
        "2. Submit an appeal\n"
        "3. Check appeal status\n"
        "4. Reset my PIN\n"
        "5. My profile\n"
        "0. Exit"
    )


def send_otp(phone: str) -> str:
    otp = ''.join(random.choices(string.digits, k=6))
    _otp_store[phone] = {
        'otp': otp,
        'expires': datetime.now() + timedelta(minutes=10)
    }
    return otp


def verify_otp(phone: str, provided: str) -> bool:
    rec = _otp_store.get(phone)
    if not rec:
        return False
    if datetime.now() > rec['expires']:
        _otp_store.pop(phone, None)
        return False
    if rec['otp'] == provided:
        _otp_store.pop(phone, None)
        return True
    return False


def authenticate_student(mysql, student_id: str, pin: str, phone: str) -> str:
    c = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    c.execute(
        "SELECT pin_hash, failed_attempts, locked FROM pin_credentials WHERE student_id=%s",
        (student_id,)
    )
    row = c.fetchone()

    if not row:
        return "No PIN registered. Please use option 4 to set your PIN."

    if row['locked']:
        _log_access(mysql, student_id, phone, 'LOGIN_LOCKED', False)
        return "Account is locked. Please use option 4 to reset your PIN via OTP."

    if sha256(pin) == row['pin_hash']:
        c2 = mysql.connection.cursor()
        c2.execute(
            "UPDATE pin_credentials SET failed_attempts=0 WHERE student_id=%s",
            (student_id,)
        )
        _log_access(mysql, student_id, phone, 'LOGIN_SUCCESS', True)
        mysql.connection.commit()
        return 'OK'

    new_fails = row['failed_attempts'] + 1
    locked = 1 if new_fails >= MAX_PIN_ATTEMPTS else 0
    c2 = mysql.connection.cursor()
    c2.execute(
        "UPDATE pin_credentials SET failed_attempts=%s, locked=%s WHERE student_id=%s",
        (new_fails, locked, student_id)
    )
    _log_access(mysql, student_id, phone, 'LOGIN_FAILED', False)
    mysql.connection.commit()

    if locked:
        return "Account locked after 3 failed attempts. Use option 4 to reset your PIN."
    remaining = MAX_PIN_ATTEMPTS - new_fails
    return f"Incorrect PIN. You have {remaining} attempt(s) remaining."


def _log_access(mysql, student_id: str, phone: str, action: str, success: bool):
    c = mysql.connection.cursor()
    c.execute(
        "INSERT INTO access_audit (student_id, phone, action, success, timestamp) "
        "VALUES (%s, %s, %s, %s, NOW())",
        (student_id, phone, action, int(success))
    )
    mysql.connection.commit()
