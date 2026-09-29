import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)
from auth_utils import generate_password_hash, check_password_hash

from database import (
    get_db, close_db, init_db, query_db,
    execute_db
)

app = Flask(__name__)
secret_val = (os.environ.get('SECRET_KEY') or '').strip()
if not secret_val:
    secret_val = 'bloodconnect_super_secret_viva_key_2026'
app.secret_key = secret_val
app.config['SECRET_KEY'] = secret_val

# Auto-close database connection on request teardown
app.teardown_appcontext(close_db)

# City Approximate Geocodes for map pinning
CITY_COORDINATES = {
    'chennai': (13.0827, 80.2707),
    'bangalore': (12.9716, 77.5946),
    'bengaluru': (12.9716, 77.5946),
    'mumbai': (19.0760, 72.8777),
    'delhi': (28.6139, 77.2090),
    'new delhi': (28.6139, 77.2090),
    'hyderabad': (17.3850, 78.4867),
    'kolkata': (22.5726, 88.3639),
    'pune': (18.5204, 73.8567),
    'coimbatore': (11.0168, 76.9558),
    'madurai': (9.9252, 78.1198),
}

def get_approx_coordinates(city_name):
    clean = city_name.strip().lower()
    return CITY_COORDINATES.get(clean, (13.0827, 80.2707))

# ---------------------------------------------------------
# Context Processors & Decorators
# ---------------------------------------------------------

@app.context_processor
def inject_global_data():
    """Injects unread notification counts and user info into all Jinja templates."""
    unread_count = 0
    if session.get('user_id'):
        try:
            row = query_db(
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0",
                (session['user_id'],),
                one=True
            )
            if row:
                unread_count = row['cnt']
        except Exception:
            unread_count = 0
    return dict(unread_notif_count=unread_count)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this feature.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Admin authentication required.', 'warning')
            return redirect(url_for('login', next=request.url))
        if session.get('user_role') != 'admin':
            flash('Access denied: Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def donor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in as a donor.', 'warning')
            return redirect(url_for('login'))
        if session.get('user_role') != 'donor':
            flash('This section is dedicated to registered blood donors.', 'info')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# Public & Home Routes
# ---------------------------------------------------------

@app.route('/')
def index():
    # 1. Fetch live metrics
    r_total = query_db("SELECT COUNT(*) as cnt FROM donors", one=True)
    r_verified = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = 1", one=True)
    r_available = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_available = 1 AND is_verified = 1", one=True)
    r_open = query_db("SELECT COUNT(*) as cnt FROM blood_requests WHERE status = 'Open'", one=True)

    stats = {
        'total_donors': r_total['cnt'] if r_total else 0,
        'verified_donors': r_verified['cnt'] if r_verified else 0,
        'available_donors': r_available['cnt'] if r_available else 0,
        'open_requests': r_open['cnt'] if r_open else 0
    }

    # 2. Fetch recent urgent requests
    recent_requests = query_db(
        "SELECT * FROM blood_requests WHERE status = 'Open' ORDER BY CASE urgency WHEN 'Critical' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC LIMIT 3"
    )

    return render_template('index.html', stats=stats, recent_requests=recent_requests)

@app.route('/compatibility')
def compatibility():
    return render_template('compatibility.html')

# ---------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']

            flash(f'Welcome back, {user["name"]}!', 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'donor':
                return redirect(url_for('donor_profile'))
            else:
                return redirect(url_for('requests_list'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/quick-login/<role>')
def quick_login(role):
    """Convenience 1-click login for viva demo presentation."""
    target_emails = {
        'admin': 'admin@bloodconnect.org',
        'donor': 'donor@bloodconnect.org',
        'requester': 'requester@bloodconnect.org'
    }
    email = target_emails.get(role)
    if not email:
        flash('Invalid demo role.', 'danger')
        return redirect(url_for('login'))

    user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
    if user:
        session.clear()
        session['user_id'] = user['id']
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_role'] = user['role']
        flash(f'Logged in as {user["name"]} ({user["role"].upper()}) for demonstration.', 'success')

        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'donor':
            return redirect(url_for('donor_profile'))
        else:
            return redirect(url_for('requests_list'))

    flash('Demo user not found. Please reseed database.', 'danger')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'donor').strip().lower()

        if not name or not email or not phone or not password:
            flash('All mandatory fields marked with * must be filled.', 'danger')
            return redirect(url_for('register'))

        # Check existing email
        existing = query_db("SELECT id FROM users WHERE email = ?", (email,), one=True)
        if existing:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Create user
        pw_hash = generate_password_hash(password)
        user_id = execute_db(
            "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
            (name, email, pw_hash, phone, role)
        )

        if role == 'donor':
            blood_group = request.form.get('blood_group', '').strip()
            city = request.form.get('city', '').strip()
            if not blood_group or not city:
                flash('Blood group and city are required for donor registration.', 'danger')
                return redirect(url_for('register'))
            address = request.form.get('address', '').strip()
            last_donation_date = request.form.get('last_donation_date', '').strip() or None

            lat, lng = get_approx_coordinates(city)

            execute_db("""
                INSERT INTO donors (user_id, blood_group, city, address, latitude, longitude, is_available, is_verified, last_donation_date, total_donations)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0, ?, 0)
            """, (user_id, blood_group, city, address, lat, lng, last_donation_date))

            # Send welcome notification
            execute_db("""
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            """, (
                user_id,
                'Registration Received',
                'Thank you for registering as a blood donor! An administrator will review and verify your details shortly.',
                'info'
            ))

        # Auto login
        session.clear()
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['user_role'] = role

        flash(f'Account created successfully! Welcome to BloodConnect, {name}.', 'success')

        if role == 'donor':
            return redirect(url_for('donor_profile'))
        else:
            return redirect(url_for('requests_list'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# ---------------------------------------------------------
# Donor Search & Map API
# ---------------------------------------------------------

@app.route('/search')
def search_donors():
    blood_group = request.args.get('blood_group', '').strip()
    city = request.args.get('city', '').strip()
    available_only = request.args.get('available_only', '1') == '1'
    verified_only = request.args.get('verified_only', '1') == '1'

    query = """
        SELECT d.*, u.name, u.email, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE 1=1
    """
    params = []

    if blood_group:
        query += " AND d.blood_group = ?"
        params.append(blood_group)

    if city:
        query += " AND LOWER(d.city) LIKE ?"
        params.append(f"%{city.lower()}%")

    if available_only:
        query += " AND d.is_available = 1"

    if verified_only:
        query += " AND d.is_verified = 1"

    query += " ORDER BY d.is_available DESC, d.total_donations DESC"

    donors = query_db(query, params)

    return render_template(
        'search.html',
        donors=donors,
        selected_blood_group=blood_group,
        selected_city=city,
        available_only=available_only,
        verified_only=verified_only
    )

@app.route('/api/donors/locations')
def api_donor_locations():
    """Returns JSON of donors for Leaflet.js interactive map."""
    blood_group = request.args.get('blood_group', '').strip()
    city = request.args.get('city', '').strip()

    query = """
        SELECT d.id, d.blood_group, d.city, d.address, d.latitude, d.longitude,
               d.is_available, d.is_verified, u.name, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE d.is_verified = 1
    """
    params = []

    if blood_group:
        query += " AND d.blood_group = ?"
        params.append(blood_group)
    if city:
        query += " AND LOWER(d.city) LIKE ?"
        params.append(f"%{city.lower()}%")

    donors = query_db(query, params)
    data = [dict(row) for row in donors]
    return jsonify(data)

# ---------------------------------------------------------
# Donor Dashboard & Profile
# ---------------------------------------------------------

@app.route('/donor/profile', methods=['GET', 'POST'])
@donor_required
def donor_profile():
    user_id = session['user_id']
    donor = query_db("""
        SELECT d.*, u.name, u.email, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE d.user_id = ?
    """, (user_id,), one=True)

    if not donor:
        flash('Donor record not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        last_donation_date = request.form.get('last_donation_date', '').strip() or None
        try:
            total_donations = max(0, int(request.form.get('total_donations', 0) or 0))
        except (ValueError, TypeError):
            total_donations = 0

        # Update users table
        execute_db("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, user_id))
        session['user_name'] = name

        # Update donors table
        lat, lng = get_approx_coordinates(city)
        execute_db("""
            UPDATE donors
            SET blood_group = ?, city = ?, address = ?, latitude = ?, longitude = ?,
                last_donation_date = ?, total_donations = ?
            WHERE user_id = ?
        """, (blood_group, city, address, lat, lng, last_donation_date, total_donations, user_id))

        flash('Donor profile updated successfully!', 'success')
        return redirect(url_for('donor_profile'))

    # Query matching active requests for this donor's blood group & city
    matching_requests = query_db("""
        SELECT * FROM blood_requests
        WHERE status = 'Open' AND blood_group = ? AND LOWER(city) = LOWER(?)
        ORDER BY CASE urgency WHEN 'Critical' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC
    """, (donor['blood_group'], donor['city']))

    return render_template('donor_profile.html', donor=donor, matching_requests=matching_requests)

@app.route('/api/donor/toggle-availability', methods=['POST'])
@login_required
def toggle_availability():
    """AJAX endpoint for real-time donor availability toggle."""
    user_id = session['user_id']
    data = request.get_json() or {}
    new_status = 1 if data.get('is_available') in (1, True, '1') else 0

    donor = query_db("SELECT id FROM donors WHERE user_id = ?", (user_id,), one=True)
    if not donor:
        return jsonify({'success': False, 'error': 'Not a registered donor'}), 404

    execute_db("UPDATE donors SET is_available = ? WHERE user_id = ?", (new_status, user_id))
    return jsonify({'success': True, 'is_available': new_status})

# ---------------------------------------------------------
# Emergency Blood Requests
# ---------------------------------------------------------

@app.route('/requests')
def requests_list():
    blood_group = request.args.get('blood_group', '').strip()
    city = request.args.get('city', '').strip()
    urgency = request.args.get('urgency', '').strip()
    status = request.args.get('status', '').strip()

    query = "SELECT * FROM blood_requests WHERE 1=1"
    params = []

    if blood_group:
        query += " AND blood_group = ?"
        params.append(blood_group)
    if city:
        query += " AND LOWER(city) LIKE ?"
        params.append(f"%{city.lower()}%")
    if urgency:
        query += " AND urgency = ?"
        params.append(urgency)
    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY CASE urgency WHEN 'Critical' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC"
    requests = query_db(query, params)

    return render_template(
        'requests_list.html',
        requests=requests,
        selected_blood_group=blood_group,
        selected_city=city,
        selected_urgency=urgency,
        selected_status=status
    )

@app.route('/requests/new', methods=['GET', 'POST'])
def emergency_request_new():
    user_phone = ''
    if session.get('user_id'):
        u = query_db("SELECT phone FROM users WHERE id = ?", (session['user_id'],), one=True)
        if u:
            user_phone = u['phone']

    if request.method == 'POST':
        # If user not logged in, auto-create a requester account or require login
        requester_id = session.get('user_id')
        if not requester_id:
            flash('Please log in or register before submitting an emergency request.', 'warning')
            return redirect(url_for('login', next=request.url))

        patient_name = request.form.get('patient_name', '').strip()
        blood_group = request.form.get('blood_group', '').strip()
        try:
            units_needed = max(1, int(request.form.get('units_needed', 1) or 1))
        except (ValueError, TypeError):
            units_needed = 1
        hospital = request.form.get('hospital', '').strip()
        city = request.form.get('city', '').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        urgency = request.form.get('urgency', 'Urgent').strip()
        notes = request.form.get('notes', '').strip()

        if not patient_name or not blood_group or not hospital or not city or not contact_phone:
            flash('Please fill in all mandatory emergency fields.', 'danger')
            return redirect(url_for('emergency_request_new'))

        req_id = execute_db("""
            INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?)
        """, (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, notes))

        # Broadcast in-app emergency alert to matching verified donors in that city
        matching_donors = query_db("""
            SELECT user_id FROM donors
            WHERE blood_group = ? AND LOWER(city) = LOWER(?) AND is_verified = 1
        """, (blood_group, city))

        for d in matching_donors:
            execute_db("""
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, ?)
            """, (
                d['user_id'],
                f"🚨 {urgency.upper()} BLOOD NEEDED: {blood_group} in {city}",
                f"{patient_name} requires {units_needed} unit(s) of {blood_group} blood at {hospital}, {city}. Emergency contact: {contact_phone}.",
                'emergency'
            ))

        flash(f'Emergency Blood Request posted successfully! Notified {len(matching_donors)} registered {blood_group} donor(s) in {city}.', 'success')
        return redirect(url_for('request_details', req_id=req_id))

    return render_template('emergency_request.html', user_phone=user_phone)

@app.route('/requests/<int:req_id>')
def request_details(req_id):
    req_item = query_db("SELECT * FROM blood_requests WHERE id = ?", (req_id,), one=True)
    if not req_item:
        flash('Blood request not found.', 'danger')
        return redirect(url_for('requests_list'))

    # Query matching available and verified donors for this request
    matching_donors = query_db("""
        SELECT d.*, u.name, u.phone, u.email
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE d.blood_group = ? AND LOWER(d.city) = LOWER(?) AND d.is_verified = 1 AND d.is_available = 1
        ORDER BY d.total_donations DESC
    """, (req_item['blood_group'], req_item['city']))

    return render_template('request_details.html', req=req_item, matching_donors=matching_donors)

@app.route('/requests/<int:req_id>/status', methods=['POST'])
@login_required
def update_request_status(req_id):
    req_item = query_db("SELECT * FROM blood_requests WHERE id = ?", (req_id,), one=True)
    if not req_item:
        flash('Request not found.', 'danger')
        return redirect(url_for('requests_list'))

    # Check permission (must be admin or owner)
    if session.get('user_role') != 'admin' and session.get('user_id') != req_item['requester_id']:
        flash('Permission denied.', 'danger')
        return redirect(url_for('request_details', req_id=req_id))

    new_status = request.form.get('status', 'Open')
    if new_status in ['Open', 'Fulfilled', 'Closed']:
        execute_db("UPDATE blood_requests SET status = ? WHERE id = ?", (new_status, req_id))
        flash(f'Request #{req_id} marked as {new_status}.', 'success')

    return redirect(url_for('request_details', req_id=req_id))

# ---------------------------------------------------------
# Admin Dashboard & Management
# ---------------------------------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    # 1. Stats
    r_total = query_db("SELECT COUNT(*) as cnt FROM donors", one=True)
    r_verified = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = 1", one=True)
    r_pending = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = 0", one=True)
    r_open = query_db("SELECT COUNT(*) as cnt FROM blood_requests WHERE status = 'Open'", one=True)

    stats = {
        'total_donors': r_total['cnt'] if r_total else 0,
        'verified_donors': r_verified['cnt'] if r_verified else 0,
        'pending_donors': r_pending['cnt'] if r_pending else 0,
        'open_requests': r_open['cnt'] if r_open else 0
    }

    # 2. Donors Table
    donors = query_db("""
        SELECT d.*, u.name, u.email, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        ORDER BY d.is_verified ASC, d.created_at DESC
    """)

    # 3. Requests Table
    requests = query_db("SELECT * FROM blood_requests ORDER BY created_at DESC")

    # 4. Users Table
    users = query_db("SELECT id, name, email, phone, role, created_at FROM users ORDER BY created_at DESC")

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        donors=donors,
        requests=requests,
        users=users
    )

@app.route('/admin/donor/<int:donor_id>/verify', methods=['POST'])
@admin_required
def admin_verify_donor(donor_id):
    donor = query_db("SELECT * FROM donors WHERE id = ?", (donor_id,), one=True)
    if not donor:
        flash('Donor record not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_status = 0 if donor['is_verified'] == 1 else 1
    execute_db("UPDATE donors SET is_verified = ? WHERE id = ?", (new_status, donor_id))

    if new_status == 1:
        execute_db("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, ?)
        """, (
            donor['user_id'],
            'Account Verified by Administrator',
            'Your donor profile has been verified! You are now active and visible in donor searches.',
            'verification'
        ))
        flash('Donor record verified successfully!', 'success')
    else:
        flash('Donor verification revoked.', 'info')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/donor/<int:donor_id>/delete', methods=['POST'])
@admin_required
def admin_delete_donor(donor_id):
    donor = query_db("SELECT user_id FROM donors WHERE id = ?", (donor_id,), one=True)
    if donor:
        # Cascade delete user and donor
        execute_db("DELETE FROM users WHERE id = ?", (donor['user_id'],))
        flash('Donor record removed successfully.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:req_id>/status', methods=['POST'])
@admin_required
def admin_update_request_status(req_id):
    new_status = request.form.get('status', 'Open')
    execute_db("UPDATE blood_requests SET status = ? WHERE id = ?", (new_status, req_id))
    flash(f'Request #{req_id} status updated to {new_status}.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/request/<int:req_id>/delete', methods=['POST'])
@admin_required
def admin_delete_request(req_id):
    execute_db("DELETE FROM blood_requests WHERE id = ?", (req_id,))
    flash('Blood request deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------
# Notifications Center
# ---------------------------------------------------------

@app.route('/notifications')
@login_required
def notifications_view():
    user_id = session['user_id']
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def notification_mark_read(notif_id):
    user_id = session['user_id']
    execute_db("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user_id))
    return redirect(url_for('notifications_view'))

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def notifications_mark_all_read():
    user_id = session['user_id']
    execute_db("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    flash('All notifications marked as read.', 'info')
    return redirect(url_for('notifications_view'))

# ---------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    import traceback
    error_tb = traceback.format_exc()
    if not error_tb or 'NoneType' in error_tb:
        error_tb = str(error)
    return render_template('500.html', error_details=error_tb), 500

# ---------------------------------------------------------
# Application Runner
# ---------------------------------------------------------

if __name__ == '__main__':
    # Initialize DB if not exists
    port = int(os.environ.get('PORT', 5050))
    app.run(debug=False, host='127.0.0.1', port=port)
