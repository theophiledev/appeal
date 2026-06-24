"""
================================================================
USSD-Based Marks Appeal System with PIN-Secured Student Authentication
Case Study: University Libre de Kigali (ULK)

Framework Actors:
  - Admin  : login/logout, manage accounts, system maintenance
  - HOD    : login/out, manage appeals, manage results
  - Student: login/logout (PIN via USSD), view marks,
             submit appeal, view results

Author    : BIKORIMANA Jean Baptiste  |  Reg: 2205000458
Supervisor: Mr. ISHIMWE Olivier Angel Kevin
================================================================
"""

import os
import hashlib
import random
import string
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, request, render_template, redirect,
                   session, url_for, flash, send_from_directory)
from flask_mysqldb import MySQL
import MySQLdb.cursors

from ussd import _ussd, _main_menu, authenticate_student

# ── optionally import Africa's Talking (graceful fallback for sandbox) ──────
try:
    import africastalking
    africastalking.initialize(
        username=os.environ.get('AT_USERNAME', 'sandbox'),
        api_key=os.environ.get('AT_API_KEY', 'your-api-key')
    )
    at_sms = africastalking.SMS
    AT_ENABLED = True
except Exception:
    AT_ENABLED = False

# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'ulk-appeal-secret-change-in-prod')

# ── MySQL ─────────────────────────────────────────────────────────────────────
app.config['MYSQL_HOST']     = os.environ.get('MYSQL_HOST',     'localhost')
app.config['MYSQL_USER']     = os.environ.get('MYSQL_USER',     'root')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
app.config['MYSQL_DB']       = os.environ.get('MYSQL_DB',       'appeal_db')
app.config['MYSQL_PORT']     = int(os.environ.get('MYSQL_PORT', 3306))

mysql = MySQL(app)

# ── Stores ───────────────────────────────────────────────────────────────────
_login_attempts: dict = {}     # ip -> { count, last_attempt }
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# =============================================================================
# UTILITY HELPERS
# =============================================================================

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def cur(dict_cursor=True):
    """Return a fresh cursor (DictCursor by default)."""
    if dict_cursor:
        return mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    return mysql.connection.cursor()


def mark_to_grade(mark: str) -> str:
    """Convert numeric mark to letter grade. Returns original if not numeric."""
    try:
        m = float(mark)
    except (ValueError, TypeError):
        return mark
    if m >= 80:
        return 'A'
    if m >= 70:
        return 'B+'
    if m >= 60:
        return 'B'
    if m >= 55:
        return 'C+'
    if m >= 50:
        return 'C'
    if m >= 40:
        return 'D'
    return 'F'


def _has_review_comment(c) -> str:
    """Check if review_comment column exists; return SQL fragment."""
    c.execute("""
        SELECT COUNT(*) AS cnt FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME='appeals' AND COLUMN_NAME='review_comment'
          AND TABLE_SCHEMA=(SELECT DATABASE())
    """)
    row = c.fetchone()
    return ', a.review_comment' if row and row['cnt'] > 0 else ', NULL AS review_comment'


def log_access(student_id: str, phone: str, action: str, success: bool):
    c = cur(False)
    c.execute(
        "INSERT INTO access_audit (student_id, phone, action, success, timestamp) "
        "VALUES (%s, %s, %s, %s, NOW())",
        (student_id, phone, action, int(success))
    )
    mysql.connection.commit()


def _clean_expired_otps():
    c = cur(False)
    c.execute("DELETE FROM otp_store WHERE expires < NOW()")
    mysql.connection.commit()


def send_otp(phone: str) -> str:
    otp = ''.join(random.choices(string.digits, k=6))
    expires = datetime.now() + timedelta(minutes=10)
    c = cur(False)
    c.execute(
        "INSERT INTO otp_store (phone, otp, expires) VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE otp=VALUES(otp), expires=VALUES(expires)",
        (phone, otp, expires)
    )
    mysql.connection.commit()
    _clean_expired_otps()
    if AT_ENABLED:
        try:
            at_sms.send(
                f"ULK Marks Appeal: Your PIN reset OTP is {otp}. "
                "Valid for 10 minutes. Do not share this code.",
                [phone]
            )
        except Exception as e:
            app.logger.error(f"[SMS] {e}")
    return otp


def verify_otp(phone: str, provided: str) -> bool:
    _clean_expired_otps()
    c = cur()
    c.execute("SELECT otp, expires FROM otp_store WHERE phone=%s", (phone,))
    rec = c.fetchone()
    if not rec:
        return False
    if datetime.now() > rec['expires']:
        c2 = cur(False)
        c2.execute("DELETE FROM otp_store WHERE phone=%s", (phone,))
        mysql.connection.commit()
        return False
    if rec['otp'] == provided:
        c2 = cur(False)
        c2.execute("DELETE FROM otp_store WHERE phone=%s", (phone,))
        mysql.connection.commit()
        return True
    return False





# =============================================================================
# AUTH DECORATORS
# =============================================================================

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('loggedin') or session.get('role') != 'admin':
            flash('Please log in as Admin.', 'warning')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def hod_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('loggedin') or session.get('role') != 'hod':
            flash('Please log in as HOD.', 'warning')
            return redirect(url_for('hod_login'))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# ── ADMIN PORTAL ─────────────────────────────────────────────────────────────
# Actor: Admin  |  login/logout · manage accounts · system maintenance
# =============================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('loggedin') and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            msg = 'Please enter both username and password.'
        else:
            ip = request.remote_addr or 'unknown'
            now = datetime.now()
            if ip in _login_attempts:
                rec = _login_attempts[ip]
                if rec['count'] >= MAX_LOGIN_ATTEMPTS:
                    if (now - rec['last_attempt']).total_seconds() < LOGIN_LOCKOUT_MINUTES * 60:
                        remaining = int(LOGIN_LOCKOUT_MINUTES * 60 - (now - rec['last_attempt']).total_seconds())
                        msg = f'Too many failed attempts. Try again in {remaining} seconds.'
                    else:
                        _login_attempts.pop(ip, None)
                else:
                    if (now - rec['last_attempt']).total_seconds() > LOGIN_LOCKOUT_MINUTES * 60:
                        _login_attempts.pop(ip, None)
            if not msg:
                c = cur()
                c.execute(
                    "SELECT * FROM admins WHERE username=%s AND role='admin'",
                    (username,)
                )
                admin = c.fetchone()
                if admin:
                    if sha256(password) == admin['password']:
                        _login_attempts.pop(ip, None)
                        session.update({'loggedin': True, 'username': admin['username'],
                                        'role': 'admin', 'admin_id': admin['id']})
                        return redirect(url_for('admin_dashboard'))
                    else:
                        msg = 'Incorrect password.'
                else:
                    msg = 'Account not found.'
                _login_attempts.setdefault(ip, {'count': 0, 'last_attempt': now})
                _login_attempts[ip]['count'] += 1
                _login_attempts[ip]['last_attempt'] = now
                remaining_attempts = MAX_LOGIN_ATTEMPTS - _login_attempts[ip]['count']
                if remaining_attempts > 0 and remaining_attempts <= 3:
                    msg += f' {remaining_attempts} attempt(s) remaining.'
                elif remaining_attempts <= 0:
                    msg = f'Account locked due to too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.'
    return render_template('admin_login.html', msg=msg)


@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    c = cur()
    page = int(request.args.get('page', 1))
    per_page = 10

    # System-wide stats
    c.execute("SELECT COUNT(*) AS cnt FROM students")
    total_students = c.fetchone()['cnt']

    c.execute("SELECT COUNT(*) AS cnt FROM appeals")
    total_appeals = c.fetchone()['cnt']

    c.execute("""
        SELECT s.status_name, COUNT(*) AS cnt
        FROM   appeals a JOIN appeal_status s ON a.status_id = s.id
        GROUP  BY s.status_name
    """)
    status_counts = {r['status_name']: r['cnt'] for r in c.fetchall()}

    # Admin accounts
    c.execute("SELECT id, username, role, created_at FROM admins ORDER BY id")
    accounts = c.fetchall()

    # Paginated audit log
    c.execute("SELECT COUNT(*) AS cnt FROM access_audit")
    audit_total = c.fetchone()['cnt']
    c.execute("""
        SELECT student_id, phone, action, success, timestamp
        FROM   access_audit
        ORDER  BY id DESC LIMIT %s OFFSET %s
    """, (per_page, (page - 1) * per_page))
    audit_log = c.fetchall()

    # Paginated students (exclude template)
    c.execute("SELECT COUNT(*) AS cnt FROM students WHERE student_id != '__TEMPLATE__'")
    student_total = c.fetchone()['cnt']
    c.execute("SELECT student_id, name, phone FROM students WHERE student_id != '__TEMPLATE__' ORDER BY name LIMIT %s OFFSET %s",
              (per_page, (page - 1) * per_page))
    all_students = c.fetchall()

    # All modules (distinct from marks, exclude template)
    c.execute("SELECT DISTINCT module_name FROM marks WHERE student_id != '__TEMPLATE__' ORDER BY module_name")
    all_modules = [r['module_name'] for r in c.fetchall()]

    # All marks for grade display (exclude template)
    c.execute("""
        SELECT m.id, m.student_id, s.name, m.module_name, m.mark,
               m.updated_by, m.updated_at
        FROM   marks m
        JOIN   students s ON m.student_id = s.student_id
        WHERE  m.student_id != '__TEMPLATE__'
        ORDER  BY m.student_id, m.module_name
    """)
    all_marks = c.fetchall()

    # Recent appeals
    rc_col = _has_review_comment(cur())
    c.execute(f"""
        SELECT a.id, a.student_id, s.name, a.module_name, a.reason,
               st.status_name, a.created_at{rc_col}
        FROM   appeals a
        JOIN   students s      ON a.student_id = s.student_id
        JOIN   appeal_status st ON a.status_id = st.id
        ORDER  BY a.id DESC LIMIT %s OFFSET %s
    """, (per_page, (page - 1) * per_page))
    recent_appeals = c.fetchall()

    c.execute("SELECT COUNT(*) AS cnt FROM appeals")
    appeal_total = c.fetchone()['cnt']

    tab = request.args.get('tab', 'overview')
    search = request.args.get('q', '').strip()
    pages = lambda total: max(1, (total + per_page - 1) // per_page)

    return render_template('admin_dashboard.html',
                           total_students=total_students,
                           total_appeals=total_appeals,
                           status_counts=status_counts,
                           accounts=accounts,
                           audit_log=audit_log,
                           recent_appeals=recent_appeals,
                           students=all_students,
                           modules=all_modules,
                           all_marks=all_marks,
                           search=search,
                           tab=tab, page=page, per_page=per_page,
                           student_total=student_total,
                           audit_total=audit_total,
                           appeal_total=appeal_total,
                           student_pages=pages(student_total),
                           appeal_pages=pages(appeal_total),
                           audit_pages=pages(audit_total))


@app.route('/admin/manage_accounts', methods=['GET', 'POST'])
@admin_required
def admin_manage_accounts():
    """Admin: create / deactivate Admin and HOD accounts."""
    msg = ''
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            username = request.form['username']
            password = sha256(request.form['password'])
            role     = request.form['role']          # 'admin' or 'hod'
            c = cur(False)
            c.execute(
                "INSERT INTO admins (username, password, role, created_at) "
                "VALUES (%s, %s, %s, NOW())",
                (username, password, role)
            )
            mysql.connection.commit()
            flash(f'✅ Account "{username}" ({role}) created.', 'success')

        elif action == 'delete':
            account_id = request.form['account_id']
            c = cur(False)
            c.execute("DELETE FROM admins WHERE id=%s AND id != %s",
                      (account_id, session['admin_id']))
            mysql.connection.commit()
            flash('🗑️ Account removed.', 'success')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/add_student', methods=['POST'])
@admin_required
def admin_add_student():
    student_id = request.form['student_id']
    name       = request.form['name']
    phone      = request.form['phone']
    c = cur(False)
    try:
        c.execute("INSERT INTO students (student_id, name, phone) VALUES (%s, %s, %s)",
                  (student_id, name, phone))
        mysql.connection.commit()
        flash(f'✅ Student {name} ({student_id}) added.', 'success')
    except Exception as e:
        flash(f'❌ Error: {e}', 'danger')
    return redirect(url_for('admin_dashboard', tab='students'))


@app.route('/admin/delete_student/<student_id>', methods=['POST'])
@admin_required
def admin_delete_student(student_id):
    c = cur(False)
    try:
        c.execute("DELETE FROM students WHERE student_id=%s", (student_id,))
        mysql.connection.commit()
        flash(f'🗑️ Student {student_id} deleted.', 'success')
    except Exception as e:
        flash(f'❌ Error: {e}', 'danger')
    return redirect(url_for('admin_dashboard', tab='students'))


@app.route('/admin/add_module', methods=['POST'])
@admin_required
def admin_add_module():
    module_name = request.form['module_name'].strip()
    c = cur(False)
    try:
        c.execute("INSERT IGNORE INTO students (student_id, name, phone) VALUES ('__TEMPLATE__', '__System__', '__template__')")
        c.execute("INSERT INTO marks (student_id, module_name, mark) VALUES (%s, %s, %s)",
                  ('__TEMPLATE__', module_name, '0'))
        mysql.connection.commit()
        flash(f'✅ Module "{module_name}" added.', 'success')
    except Exception as e:
        flash(f'❌ Error: {e}', 'danger')
    return redirect(url_for('admin_dashboard', tab='modules'))


@app.route('/admin/rename_module', methods=['POST'])
@admin_required
def admin_rename_module():
    old_name = request.form.get('old_name', '').strip()
    new_name = request.form.get('new_name', '').strip()
    if not old_name or not new_name:
        flash('Both old and new module names are required.', 'danger')
        return redirect(url_for('admin_dashboard', tab='modules'))
    c = cur(False)
    c.execute("UPDATE marks SET module_name=%s WHERE module_name=%s", (new_name, old_name))
    mysql.connection.commit()
    flash(f'✅ Module renamed from "{old_name}" to "{new_name}".', 'success')
    return redirect(url_for('admin_dashboard', tab='modules'))


@app.route('/admin/delete_module/<path:module_name>', methods=['POST'])
@admin_required
def admin_delete_module(module_name):
    c = cur(False)
    c.execute("DELETE FROM marks WHERE module_name=%s", (module_name,))
    mysql.connection.commit()
    flash(f'🗑️ Module "{module_name}" and all its marks deleted.', 'success')
    return redirect(url_for('admin_dashboard', tab='modules'))


@app.route('/admin/edit_student/<student_id>', methods=['POST'])
@admin_required
def admin_edit_student(student_id):
    name  = request.form['name']
    phone = request.form['phone']
    c = cur(False)
    c.execute("UPDATE students SET name=%s, phone=%s WHERE student_id=%s",
              (name, phone, student_id))
    mysql.connection.commit()
    flash(f'✅ Student {student_id} updated.', 'success')
    return redirect(url_for('admin_dashboard', tab='students'))


@app.route('/admin/system_maintenance')
@admin_required
def admin_system_maintenance():
    """Admin: system maintenance — view all locked students, unlock accounts."""
    c = cur()
    c.execute("""
        SELECT p.student_id, s.name, s.phone, p.failed_attempts, p.locked
        FROM   pin_credentials p
        JOIN   students s ON p.student_id = s.student_id
        ORDER  BY p.locked DESC, p.failed_attempts DESC
    """)
    pin_status = c.fetchall()
    return render_template('admin_maintenance.html', pin_status=pin_status)


@app.route('/admin/unlock/<student_id>', methods=['POST'])
@admin_required
def admin_unlock(student_id):
    c = cur(False)
    c.execute(
        "UPDATE pin_credentials SET locked=0, failed_attempts=0 WHERE student_id=%s",
        (student_id,)
    )
    mysql.connection.commit()
    flash(f'✅ Account for {student_id} has been unlocked.', 'success')
    return redirect(url_for('admin_system_maintenance'))


# =============================================================================
# ── HOD PORTAL ───────────────────────────────────────────────────────────────
# Actor: HOD  |  login/out · manage appeals · manage results
# =============================================================================

@app.route('/hod/login', methods=['GET', 'POST'])
def hod_login():
    if session.get('loggedin') and session.get('role') == 'hod':
        return redirect(url_for('hod_dashboard'))
    msg = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            msg = 'Please enter both username and password.'
        else:
            ip = request.remote_addr or 'unknown'
            now = datetime.now()
            if ip in _login_attempts:
                rec = _login_attempts[ip]
                if rec['count'] >= MAX_LOGIN_ATTEMPTS:
                    if (now - rec['last_attempt']).total_seconds() < LOGIN_LOCKOUT_MINUTES * 60:
                        remaining = int(LOGIN_LOCKOUT_MINUTES * 60 - (now - rec['last_attempt']).total_seconds())
                        msg = f'Too many failed attempts. Try again in {remaining} seconds.'
                    else:
                        _login_attempts.pop(ip, None)
                else:
                    if (now - rec['last_attempt']).total_seconds() > LOGIN_LOCKOUT_MINUTES * 60:
                        _login_attempts.pop(ip, None)
            if not msg:
                c = cur()
                c.execute(
                    "SELECT * FROM admins WHERE username=%s AND role='hod'",
                    (username,)
                )
                hod = c.fetchone()
                if hod:
                    if sha256(password) == hod['password']:
                        _login_attempts.pop(ip, None)
                        session.update({'loggedin': True, 'username': hod['username'],
                                        'role': 'hod', 'hod_id': hod['id']})
                        return redirect(url_for('hod_dashboard'))
                    else:
                        msg = 'Incorrect password.'
                else:
                    msg = 'Account not found.'
                _login_attempts.setdefault(ip, {'count': 0, 'last_attempt': now})
                _login_attempts[ip]['count'] += 1
                _login_attempts[ip]['last_attempt'] = now
                remaining_attempts = MAX_LOGIN_ATTEMPTS - _login_attempts[ip]['count']
                if remaining_attempts > 0 and remaining_attempts <= 3:
                    msg += f' {remaining_attempts} attempt(s) remaining.'
                elif remaining_attempts <= 0:
                    msg = f'Account locked due to too many failed attempts. Try again in {LOGIN_LOCKOUT_MINUTES} minutes.'
    return render_template('hod_login.html', msg=msg)


@app.route('/hod/dashboard')
@hod_required
def hod_dashboard():
    c = cur()
    page = int(request.args.get('page', 1))
    per_page = 10

    c.execute("SELECT COUNT(*) AS cnt FROM appeals")
    total_appeals = c.fetchone()['cnt']

    rc_col = _has_review_comment(cur())
    c.execute(f"""
        SELECT a.id, a.student_id, st.name AS student_name,
               a.module_name, a.reason, a.created_at,
               s.status_name AS status{rc_col}
        FROM   appeals a
        JOIN   appeal_status s ON a.status_id = s.id
        JOIN   students st     ON a.student_id = st.student_id
        ORDER  BY a.id DESC
        LIMIT %s OFFSET %s
    """, (per_page, (page - 1) * per_page))
    appeals = c.fetchall()

    c.execute("""
        SELECT s.status_name, COUNT(*) AS cnt
        FROM   appeals a JOIN appeal_status s ON a.status_id = s.id
        GROUP  BY s.status_name
    """)
    counts = {r['status_name']: r['cnt'] for r in c.fetchall()}

    search = request.args.get('q', '').strip()
    total_pages = max(1, (total_appeals + per_page - 1) // per_page)

    return render_template('hod_dashboard.html', appeals=appeals, counts=counts,
                           search=search, page=page, total_pages=total_pages)


@app.route('/hod/manage_appeal/<int:appeal_id>', methods=['POST'])
@hod_required
def hod_manage_appeal(appeal_id):
    """HOD: update appeal status — Approved / Rejected / Pending."""
    new_status = request.form.get('status')
    comment    = request.form.get('review_comment', '').strip()

    if new_status != 'Pending' and not comment:
        flash('Please provide a comment for this action.', 'danger')
        return redirect(url_for('hod_dashboard'))

    c = cur()
    c.execute("SELECT id FROM appeal_status WHERE status_name=%s", (new_status,))
    row = c.fetchone()
    if row:
        c2 = cur(False)
        has_rc_col = _has_review_comment(cur()) != ', NULL AS review_comment'
        if has_rc_col:
            c2.execute(
                "UPDATE appeals SET status_id=%s, reviewed_by=%s, review_comment=%s WHERE id=%s",
                (row['id'], session['username'], comment if comment else None, appeal_id)
            )
        else:
            c2.execute(
                "UPDATE appeals SET status_id=%s, reviewed_by=%s WHERE id=%s",
                (row['id'], session['username'], appeal_id)
            )
        mysql.connection.commit()
        flash(f'Appeal #{appeal_id} marked as {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('hod_dashboard'))


@app.route('/hod/manage_results', methods=['GET', 'POST'])
@hod_required
def hod_manage_results():
    """HOD: view and update student marks (results)."""
    c = cur()

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update':
            student_id  = request.form['student_id']
            module_name = request.form['module_name']
            new_mark    = request.form['mark']
            c2 = cur(False)
            c2.execute(
                "UPDATE marks SET mark=%s, updated_by=%s, updated_at=NOW() "
                "WHERE student_id=%s AND module_name=%s",
                (new_mark, session['username'], student_id, module_name)
            )
            mysql.connection.commit()
            flash(f'✅ Mark updated for {student_id} — {module_name}: {new_mark}', 'success')

        elif action == 'add':
            student_id  = request.form['student_id']
            module_name = request.form.get('module_name', '').strip()
            mark        = request.form['mark']
            c2 = cur(False)
            c2.execute(
                "INSERT INTO marks (student_id, module_name, mark) VALUES (%s, %s, %s)",
                (student_id, module_name, mark)
            )
            mysql.connection.commit()
            flash('✅ Mark added.', 'success')

    page = int(request.args.get('page', 1))
    per_page = 10

    # Count total marks (exclude template)
    c.execute("SELECT COUNT(*) AS cnt FROM marks WHERE student_id != '__TEMPLATE__'")
    total_marks = c.fetchone()['cnt']

    # Paginated student results (exclude template)
    c.execute("""
        SELECT m.id, m.student_id, s.name, m.module_name, m.mark,
               m.updated_by, m.updated_at
        FROM   marks m
        JOIN   students s ON m.student_id = s.student_id
        WHERE  m.student_id != '__TEMPLATE__'
        ORDER  BY m.student_id, m.module_name
        LIMIT %s OFFSET %s
    """, (per_page, (page - 1) * per_page))
    results = c.fetchall()

    c.execute("SELECT student_id, name FROM students WHERE student_id != '__TEMPLATE__' ORDER BY name")
    students = c.fetchall()

    c.execute("SELECT DISTINCT module_name FROM marks WHERE student_id != '__TEMPLATE__' ORDER BY module_name")
    modules = [r['module_name'] for r in c.fetchall()]

    search = request.args.get('q', '').strip()
    total_pages = max(1, (total_marks + per_page - 1) // per_page)

    return render_template('hod_results.html', results=results, students=students,
                           modules=modules, search=search,
                           page=page, total_pages=total_pages, total_marks=total_marks)


# =============================================================================
# ── SHARED LOGOUT ─────────────────────────────────────────────────────────────
# =============================================================================

@app.route('/logout')
def logout():
    role = session.get('role', 'admin')
    session.clear()
    if role == 'hod':
        return redirect(url_for('hod_login'))
    return redirect(url_for('admin_login'))


# =============================================================================
# ── USSD ENDPOINT ─────────────────────────────────────────────────────────────
# Actor: Student  |  login/logout · view marks · submit appeal · view results
# =============================================================================

@app.route('/ussd', methods=['POST'])
def ussd():
    phone_number = request.form.get('phoneNumber', '')
    text         = request.form.get('text', '')
    steps        = text.split('*') if text else ['']

    try:
        # ── WELCOME MENU ─────────────────────────────────────────────────────
        if text == '':
            return _ussd(
                "CON Dear Student, welcome to ULK Marks Appeal System.\n"
                "Please select an option:\n"
                "1. View my marks\n"
                "2. Submit an appeal\n"
                "3. Check appeal status\n"
                "4. Reset my PIN\n"
                "5. My account\n"
                "0. Exit"
            )

        if text == '0':
            return _ussd("END Thank you for using the ULK Marks Appeal System. Goodbye.")

        # ════════════════════════════════════════════════════════════════════
        # 1. VIEW MARKS  (Student: view marks / view results)
        #    Flow: 1 -> student_id -> PIN
        # ════════════════════════════════════════════════════════════════════
        if steps[0] == '1':
            if len(steps) == 1:
                return _ussd("CON Please enter your Student ID:\n0. Back to menu")
            if len(steps) == 2:
                if steps[1] == '0':
                    return _ussd(_main_menu())
                return _ussd("CON Kindly enter your 4-digit PIN:\n0. Back")
            if len(steps) == 3:
                if steps[2] == '0':
                    return _ussd("CON Please enter your Student ID:\n0. Back to menu")
                student_id = steps[1]
                auth = authenticate_student(mysql, student_id, steps[2], phone_number)
                if auth != 'OK':
                    return _ussd(f"END {auth}")
                c = cur()
                c.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
                student_row = c.fetchone()
                student_name = student_row['name'] if student_row else 'Dear Student'
                c.execute(
                    "SELECT module_name, mark FROM marks WHERE student_id=%s ORDER BY module_name",
                    (student_id,)
                )
                rows = c.fetchall()
                if not rows:
                    return _ussd("END No results found for your Student ID.")
                body = "\n".join(
                    (f"{r['module_name']}: {r['mark']} ({mark_to_grade(r['mark'])})"
                     if mark_to_grade(r['mark']) != r['mark']
                     else f"{r['module_name']}: {r['mark']}")
                    for r in rows
                )
                return _ussd(f"END Here are your results, {student_name}:\n{body}")

        # ════════════════════════════════════════════════════════════════════
        # 2. SUBMIT APPEAL  (Student: submit appeal)
        #    Flow: 2 -> student_id -> PIN -> module_no -> reason
        # ════════════════════════════════════════════════════════════════════
        if steps[0] == '2':
            if len(steps) == 1:
                return _ussd("CON Please enter your Student ID:\n0. Back to menu")
            if len(steps) == 2:
                if steps[1] == '0':
                    return _ussd(_main_menu())
                return _ussd("CON Kindly enter your 4-digit PIN:\n0. Back")
            if len(steps) == 3:
                if steps[2] == '0':
                    return _ussd("CON Please enter your Student ID:\n0. Back to menu")
                student_id = steps[1]
                auth = authenticate_student(mysql, student_id, steps[2], phone_number)
                if auth != 'OK':
                    return _ussd(f"END {auth}")
                c = cur()
                c.execute(
                    "SELECT module_name, mark FROM marks WHERE student_id=%s",
                    (student_id,)
                )
                modules = c.fetchall()
                if not modules:
                    return _ussd("END No modules found for your Student ID.")
                menu = "CON Please select the module you wish to appeal:\n"
                for i, m in enumerate(modules, 1):
                    menu += f"{i}. {m['module_name']} ({m['mark']})\n"
                menu += "0. Back"
                return _ussd(menu)
            if len(steps) == 4:
                if steps[3] == '0':
                    return _ussd(_main_menu())
                return _ussd("CON Kindly state your reason for appeal:\n0. Cancel")
            if len(steps) == 5:
                if steps[4] == '0':
                    return _ussd(_main_menu())
                student_id   = steps[1]
                module_index = int(steps[3]) - 1
                reason       = steps[4]
                c = cur()
                c.execute(
                    "SELECT module_name FROM marks WHERE student_id=%s",
                    (student_id,)
                )
                modules = [r['module_name'] for r in c.fetchall()]
                if module_index < 0 or module_index >= len(modules):
                    return _ussd("END Invalid selection. Please try again.")
                selected = modules[module_index]
                c.execute(
                    "SELECT id FROM appeal_status WHERE status_name='Pending'"
                )
                status_row = c.fetchone()
                status_id  = status_row['id'] if status_row else 1
                c2 = cur(False)
                c2.execute(
                    "INSERT INTO appeals (student_id, module_name, reason, status_id, created_at) "
                    "VALUES (%s, %s, %s, %s, NOW())",
                    (student_id, selected, reason, status_id)
                )
                log_access(student_id, phone_number, 'APPEAL_SUBMIT', True)
                mysql.connection.commit()
                return _ussd(
                    f"END Your appeal for {selected} has been received.\n"
                    "The HOD will review it. Thank you for reaching out."
                )

        # ════════════════════════════════════════════════════════════════════
        # 3. CHECK APPEAL STATUS  (Student: view results)
        #    Flow: 3 -> student_id -> PIN
        # ════════════════════════════════════════════════════════════════════
        if steps[0] == '3':
            if len(steps) == 1:
                return _ussd("CON Please enter your Student ID:\n0. Back to menu")
            if len(steps) == 2:
                if steps[1] == '0':
                    return _ussd(_main_menu())
                return _ussd("CON Kindly enter your 4-digit PIN:\n0. Back")
            if len(steps) == 3:
                if steps[2] == '0':
                    return _ussd("CON Please enter your Student ID:\n0. Back to menu")
                student_id = steps[1]
                auth = authenticate_student(mysql, student_id, steps[2], phone_number)
                if auth != 'OK':
                    return _ussd(f"END {auth}")
                c = cur()
                rc_col = _has_review_comment(cur())
                c.execute(f"""
                    SELECT a.module_name, s.status_name, a.reviewed_by,
                           a.created_at{rc_col}
                    FROM   appeals a
                    JOIN   appeal_status s ON a.status_id = s.id
                    WHERE  a.student_id=%s
                    ORDER  BY a.id DESC LIMIT 3
                """, (student_id,))
                rows = c.fetchall()
                if not rows:
                    return _ussd("END You have no appeals on record.")
                body = "END Your recent appeal requests:\n\n"
                for r in rows:
                    reviewed = f" (reviewed by {r['reviewed_by']})" if r['reviewed_by'] else ''
                    comment = f"\n   Comment: {r['review_comment']}" if r['review_comment'] else ''
                    body += f"{r['module_name']}: {r['status_name']}{reviewed}{comment}\n"
                return _ussd(body.strip())

        # ════════════════════════════════════════════════════════════════════
        # 5. MY PROFILE  (Student: view registered info)
        #    Flow: 5 -> student_id -> pin -> show profile
        # ════════════════════════════════════════════════════════════════════
        if steps[0] == '5':
            if len(steps) == 1:
                return _ussd("CON Enter your Student ID:\n0. Back to menu")
            if len(steps) == 2:
                if steps[1] == '0':
                    return _ussd(_main_menu())
                return _ussd("CON Enter your PIN:")
            if len(steps) == 3:
                student_id = steps[1]
                pin = steps[2]
                auth = authenticate_student(mysql, student_id, pin, phone_number)
                if auth != 'OK':
                    return _ussd(f"END {auth}")
                c = cur()
                c.execute(
                    "SELECT student_id, name, phone FROM students WHERE student_id=%s",
                    (student_id,)
                )
                s = c.fetchone()
                if not s:
                    return _ussd("END Student not found.")
                return _ussd(
                    f"CON Student Profile:\n"
                    f"ID: {s['student_id']}\n"
                    f"Name: {s['name']}\n"
                    f"Phone: {s['phone']}\n\n"
                    f"0. Main menu"
                )

            if len(steps) == 4:
                if steps[3] == '0':
                    return _ussd(_main_menu())

        # ════════════════════════════════════════════════════════════════════
        # 4. RESET PIN  (Student: login/logout — recover access)
        #    Flow: 4 -> student_id -> OTP -> new_pin -> confirm_pin
        # ════════════════════════════════════════════════════════════════════
        if steps[0] == '4':
            if len(steps) == 1:
                return _ussd("CON Please enter your Student ID to reset PIN:\n0. Back to menu")
            if len(steps) == 2:
                if steps[1] == '0':
                    return _ussd(_main_menu())
                student_id = steps[1]
                c = cur()
                c.execute("SELECT phone FROM students WHERE student_id=%s", (student_id,))
                st = c.fetchone()
                if not st:
                    return _ussd("END Student ID not found in our system.")
                _clean_expired_otps()
                c2 = cur()
                c2.execute("SELECT otp, expires FROM otp_store WHERE phone=%s", (st['phone'],))
                existing = c2.fetchone()
                if existing:
                    otp = existing['otp']
                else:
                    otp = send_otp(st['phone'])
                is_sim = phone_number.startswith('250') and request.form.get('sessionId','').startswith('sim-')
                msg = "CON An OTP has been sent to your registered mobile number.\nPlease enter the OTP:"
                msg += "\n\n(If session expires, re-dial *XXX# and re-enter your Student ID — the same OTP will still work.)"
                if is_sim:
                    msg += f"\n\n[Simulator OTP: {otp}]"
                return _ussd(msg)
            if len(steps) == 3:
                student_id = steps[1]
                c = cur()
                c.execute("SELECT phone FROM students WHERE student_id=%s", (student_id,))
                st = c.fetchone()
                if not st or not verify_otp(st['phone'], steps[2]):
                    return _ussd("END Invalid or expired OTP. Please start again.")
                return _ussd("CON OTP verified. Kindly enter your new 4-digit PIN:")
            if len(steps) == 4:
                if len(steps[3]) != 4 or not steps[3].isdigit():
                    return _ussd("END PIN must be exactly 4 digits. Please start again.")
                return _ussd("CON Please confirm your new PIN:")
            if len(steps) == 5:
                if steps[3] != steps[4]:
                    return _ussd("END PINs do not match. Please start again.")
                pin_hash = sha256(steps[3])
                c2 = cur(False)
                c2.execute("""
                    INSERT INTO pin_credentials (student_id, pin_hash, failed_attempts, locked, created_at)
                    VALUES (%s, %s, 0, 0, NOW())
                    ON DUPLICATE KEY UPDATE pin_hash=VALUES(pin_hash),
                                            failed_attempts=0, locked=0
                """, (steps[1], pin_hash))
                mysql.connection.commit()
                return _ussd("END Your PIN has been reset successfully. You may now log in.")

        return _ussd("END Invalid option. Please dial *123# and try again.")

    except Exception as exc:
        app.logger.error(f"[USSD] {exc}")
        return _ussd("END System error. Please try again later or contact support.")



#editing and adding 5=================================================
#=====================================================================
    if steps[0] == '5':
            if len(steps) == 1:
                return _ussd("CON please this service will coming soon:\n0. Back to menu")
# =============================================================================
# USSD SIMULATOR (browser-based testing)
# =============================================================================

@app.route('/ussd-simulator')
def ussd_simulator():
    if not session.get('loggedin'):
        return redirect(url_for('admin_login'))
    return render_template('ussd_simulator.html')


@app.route('/student/ussd')
def student_ussd():
    """Student-facing USSD simulator — no login required."""
    return render_template('student_ussd.html')


@app.route('/diagrams/view_diagrams.html')
def view_diagrams():
    """Serve the system diagrams HTML viewer."""
    diag_dir = os.path.join(app.root_path, 'diagrams')
    return send_from_directory(diag_dir, 'view_diagrams.html')


# =============================================================================
# ROOT REDIRECT
# =============================================================================

@app.route('/')
def index():
    return redirect(url_for('admin_login'))


# =============================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
