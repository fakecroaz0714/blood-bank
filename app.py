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
    execute_db, ensure_blood_bank_tables, is_using_postgres
)
import whatsapp_service

app = Flask(__name__)
secret_val = (os.environ.get('SECRET_KEY') or '').strip()
if not secret_val:
    secret_val = 'bloodconnect_super_secret_viva_key_2026'
app.secret_key = secret_val
app.config['SECRET_KEY'] = secret_val

_blood_bank_schema_ready = False

@app.before_request
def ensure_database_schema_ready():
    """Ensure base database schema and blood bank tables are prepared once per app instance."""
    global _blood_bank_schema_ready
    if not _blood_bank_schema_ready:
        try:
            row = query_db("SELECT COUNT(*) as cnt FROM users", one=True)
        except Exception:
            row = None
        if row is None:
            try:
                init_db()
            except Exception as e:
                app.logger.warning(f"Could not initialize base schema: {e}")
        try:
            ensure_blood_bank_tables()
        except Exception as e:
            app.logger.warning(f"Could not initialize blood bank tables on startup: {e}")
        _blood_bank_schema_ready = True

@app.route('/api/index')
@app.route('/api/index.py')
def vercel_entrypoint_redirect():
    return index()

@app.route('/api/index/<path:subpath>')
@app.route('/api/index.py/<path:subpath>')
def vercel_subpath_redirect(subpath):
    return redirect('/' + subpath.lstrip('/'))

def inventory_database_available():
    """Returns True indicating blood bank inventory storage is enabled."""
    return True

def inventory_database_setup_response():
    return render_template('database_setup.html'), 503

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
                "SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = FALSE",
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

def blood_bank_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('user_role') != 'blood_bank' or not session.get('blood_bank_id'):
            flash('Please sign in with your blood bank account.', 'warning')
            return redirect(url_for('blood_bank_login'))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------
# Public & Home Routes
# ---------------------------------------------------------

@app.route('/')
def index():
    # 1. Fetch live metrics
    r_total = query_db("SELECT COUNT(*) as cnt FROM donors", one=True)
    r_verified = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = TRUE", one=True)
    r_available = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_available = TRUE AND is_verified = TRUE", one=True)
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
    ) or []

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

        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')

        user = query_db("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,), one=True)
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['user_role'] = user['role']

            flash(f'Welcome back, {user["name"]}!', 'success')
            next_url = request.args.get('next')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
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
    role_clean = (role or '').strip().lower()
    target_emails = {
        'admin': 'admin@bloodconnect.org',
        'donor': 'donor@bloodconnect.org',
        'requester': 'requester@bloodconnect.org',
        'blood_bank': 'central@bank.org',
        'bank': 'central@bank.org'
    }
    email = target_emails.get(role_clean)
    if not email:
        flash('Invalid demo role.', 'danger')
        return redirect(url_for('login'))

    if role_clean in ('blood_bank', 'bank'):
        bank = query_db("SELECT * FROM blood_banks WHERE LOWER(email) = LOWER(?)", (email,), one=True)
        if not bank:
            bank = query_db("SELECT * FROM blood_banks ORDER BY id ASC LIMIT 1", one=True)
        if bank:
            session.clear()
            session['user_role'] = 'blood_bank'
            session['user_name'] = bank['name']
            session['user_email'] = bank['email']
            session['blood_bank_id'] = bank['id']
            flash(f'Logged in as {bank["name"]} (BLOOD BANK) for demonstration.', 'success')
            return redirect(url_for('blood_bank_dashboard'))
        flash('No blood bank accounts found in database. Please register one first.', 'warning')
        return redirect(url_for('blood_bank_login'))

    user = query_db("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,), one=True)
    if not user:
        # Fallback: find first matching user with this role
        user = query_db("SELECT * FROM users WHERE role = ? ORDER BY id ASC LIMIT 1", (role_clean,), one=True)

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

    flash(f'No {role_clean} accounts found in database. Please use the registration form to create one.', 'warning')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        raw_role = request.form.get('role', 'donor').strip().lower()
        # Security: restrict public self-registration to 'donor' or 'requester' only (prevent unauthorized admin creation)
        role = raw_role if raw_role in ('donor', 'requester') else 'donor'

        if not name or not email or not phone or not password:
            flash('All mandatory fields marked with * must be filled.', 'danger')
            return redirect(url_for('register'))

        if role == 'donor':
            blood_group = request.form.get('blood_group', '').strip()
            city = request.form.get('city', '').strip()
            if not blood_group or not city:
                flash('Blood group and city are required for donor registration.', 'danger')
                return redirect(url_for('register'))
            valid_bgs = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
            if blood_group not in valid_bgs:
                flash('Please select a valid blood group.', 'danger')
                return redirect(url_for('register'))
            address = request.form.get('address', '').strip()
            last_donation_date = request.form.get('last_donation_date', '').strip() or None
        else:
            blood_group = None
            city = None
            address = None
            last_donation_date = None

        # Check existing email
        existing = query_db("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,), one=True)
        if existing:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        # Create user
        pw_hash = generate_password_hash(password)
        user_id = execute_db(
            "INSERT INTO users (name, email, password_hash, phone, role) VALUES (?, ?, ?, ?, ?)",
            (name, email, pw_hash, phone, role)
        )

        if role == 'donor' and user_id:
            lat, lng = get_approx_coordinates(city)

            execute_db("""
                INSERT INTO donors (user_id, blood_group, city, address, latitude, longitude, is_available, is_verified, last_donation_date, total_donations)
                VALUES (?, ?, ?, ?, ?, ?, TRUE, FALSE, ?, 0)
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

    if blood_group and blood_group.lower() not in ('all', '', 'any'):
        query += " AND d.blood_group = ?"
        params.append(blood_group)

    if city and city.lower() not in ('all', '', 'any'):
        query += " AND LOWER(TRIM(d.city)) LIKE ?"
        params.append(f"%{city.lower()}%")

    if available_only:
        query += " AND d.is_available = TRUE"

    if verified_only:
        query += " AND d.is_verified = TRUE"

    query += " ORDER BY d.is_available DESC, d.total_donations DESC"

    donors = query_db(query, params) or []

    return render_template(
        'search.html',
        donors=donors,
        selected_blood_group=blood_group,
        selected_city=city,
        available_only=available_only,
        verified_only=verified_only
    )

# ---------------------------------------------------------
# Blood Bank Inventory (separate from volunteer donors)
# ---------------------------------------------------------

BLOOD_GROUPS = ('O+', 'O-', 'A+', 'A-', 'B+', 'B-', 'AB+', 'AB-')
BLOOD_COMPONENTS = ('Whole Blood', 'Red Cells', 'Platelets', 'Plasma')

def _inventory_rows(blood_group='', city='', component=''):
    sql = '''
        SELECT s.id, s.blood_group, s.component, s.units_available, s.updated_at,
               b.id AS blood_bank_id, b.name AS bank_name, b.phone, b.city,
               b.address, b.latitude, b.longitude
        FROM blood_bank_stock s
        JOIN blood_banks b ON b.id = s.blood_bank_id
        WHERE b.is_verified = TRUE AND s.units_available > 0
    '''
    params = []
    if blood_group in BLOOD_GROUPS:
        sql += ' AND s.blood_group = ?'
        params.append(blood_group)
    if component in BLOOD_COMPONENTS:
        sql += ' AND s.component = ?'
        params.append(component)
    if city:
        sql += ' AND LOWER(TRIM(b.city)) LIKE ?'
        params.append(f'%{city.lower()}%')
    sql += ' ORDER BY s.updated_at DESC, b.name ASC'
    rows = query_db(sql, tuple(params)) or []
    now = datetime.utcnow()
    result = []
    for row in rows:
        item = dict(row)
        raw_updated = item.get('updated_at')
        try:
            updated = raw_updated if isinstance(raw_updated, datetime) else datetime.fromisoformat(str(raw_updated).replace('Z', '+00:00'))
            if updated.tzinfo:
                from datetime import timezone
                updated = updated.astimezone(timezone.utc).replace(tzinfo=None)
            item['is_stale'] = (now - updated).total_seconds() > 24 * 60 * 60
            item['updated_at'] = updated.isoformat(timespec='minutes') + 'Z'
        except (TypeError, ValueError):
            item['is_stale'] = True
            item['updated_at'] = str(raw_updated or '')
        result.append(item)
    return result

@app.route('/blood-banks')
def blood_banks():
    if not inventory_database_available():
        return inventory_database_setup_response()
    blood_group = request.args.get('blood_group', '').strip()
    city = request.args.get('city', '').strip()
    component = request.args.get('component', '').strip()
    inventory = _inventory_rows(blood_group, city, component)
    return render_template(
        'blood_banks.html', inventory=inventory,
        selected_blood_group=blood_group, selected_city=city,
        selected_component=component,
        blood_groups=BLOOD_GROUPS, components=BLOOD_COMPONENTS
    )

@app.route('/api/blood-banks/inventory')
def api_blood_bank_inventory():
    if not inventory_database_available():
        return jsonify({'error': 'Configure a Postgres DATABASE_URL or POSTGRES_URL to enable blood bank inventory.'}), 503
    inventory = _inventory_rows(
        request.args.get('blood_group', '').strip(),
        request.args.get('city', '').strip(),
        request.args.get('component', '').strip()
    )
    response = jsonify({'inventory': inventory, 'updated_at': datetime.utcnow().isoformat(timespec='seconds') + 'Z'})
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

@app.route('/blood-banks/register', methods=['GET', 'POST'])
def blood_bank_register():
    if not inventory_database_available():
        return inventory_database_setup_response()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        license_number = request.form.get('license_number', '').strip()
        city = request.form.get('city', '').strip()
        address = request.form.get('address', '').strip()
        if not all((name, email, phone, password, license_number, city, address)):
            flash('Complete all fields to register your blood bank.', 'danger')
            return render_template('blood_bank_register.html')
        if len(password) < 10:
            flash('Use a password with at least 10 characters.', 'warning')
            return render_template('blood_bank_register.html')
        if query_db('SELECT id FROM blood_banks WHERE LOWER(email) = LOWER(?)', (email,), one=True):
            flash('An account already exists for this email address.', 'warning')
            return render_template('blood_bank_register.html')
        execute_db('''
            INSERT INTO blood_banks (name, email, phone, password_hash, license_number, city, address)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, email, phone, generate_password_hash(password), license_number, city, address))
        flash('Registration submitted. An administrator must verify your blood bank before its stock appears publicly.', 'success')
        return redirect(url_for('blood_bank_login'))
    return render_template('blood_bank_register.html')

@app.route('/blood-banks/login', methods=['GET', 'POST'])
def blood_bank_login():
    if not inventory_database_available():
        return inventory_database_setup_response()
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        bank = query_db('SELECT * FROM blood_banks WHERE LOWER(email) = LOWER(?)', (email,), one=True)
        if bank and check_password_hash(bank['password_hash'], password):
            session.clear()
            session['user_role'] = 'blood_bank'
            session['user_name'] = bank['name']
            session['user_email'] = bank['email']
            session['blood_bank_id'] = bank['id']
            if not bank['is_verified']:
                flash('Your account is pending administrator verification. You can prepare stock updates, but they will not appear publicly until approval.', 'info')
            return redirect(url_for('blood_bank_dashboard'))
        flash('Invalid blood bank email or password.', 'danger')
    return render_template('blood_bank_login.html')

@app.route('/blood-banks/dashboard', methods=['GET', 'POST'])
@blood_bank_required
def blood_bank_dashboard():
    if not inventory_database_available():
        return inventory_database_setup_response()
    bank_id = session['blood_bank_id']
    bank = query_db('SELECT * FROM blood_banks WHERE id = ?', (bank_id,), one=True)
    if not bank:
        session.clear()
        return redirect(url_for('blood_bank_login'))
    if request.method == 'POST':
        blood_group = request.form.get('blood_group', '').strip()
        component = request.form.get('component', '').strip()
        try:
            units = int(request.form.get('units_available', ''))
        except (TypeError, ValueError):
            units = -1
        if blood_group not in BLOOD_GROUPS or component not in BLOOD_COMPONENTS or units < 0 or units > 100000:
            flash('Enter a valid blood group, component, and non-negative unit count.', 'danger')
        else:
            execute_db('''
                INSERT INTO blood_bank_stock (blood_bank_id, blood_group, component, units_available, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (blood_bank_id, blood_group, component)
                DO UPDATE SET units_available = EXCLUDED.units_available, updated_at = CURRENT_TIMESTAMP
            ''', (bank_id, blood_group, component, units))
            flash(f'{blood_group} {component} stock updated to {units} unit(s).', 'success')
            return redirect(url_for('blood_bank_dashboard'))
    stock = query_db('SELECT * FROM blood_bank_stock WHERE blood_bank_id = ? ORDER BY blood_group, component', (bank_id,)) or []
    return render_template('blood_bank_dashboard.html', bank=bank, stock=stock, blood_groups=BLOOD_GROUPS, components=BLOOD_COMPONENTS)

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
        WHERE d.is_verified = TRUE
    """
    params = []

    if blood_group and blood_group.lower() not in ('all', '', 'any'):
        query += " AND d.blood_group = ?"
        params.append(blood_group)
    if city and city.lower() not in ('all', '', 'any'):
        query += " AND LOWER(TRIM(d.city)) LIKE ?"
        params.append(f"%{city.lower()}%")

    donors = query_db(query, params) or []
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

        if not name or not phone or not blood_group or not city:
            flash('Name, phone, blood group, and city are required fields.', 'danger')
            return redirect(url_for('donor_profile'))

        valid_bgs = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
        if blood_group not in valid_bgs:
            flash('Please select a valid blood group.', 'danger')
            return redirect(url_for('donor_profile'))

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
        WHERE status = 'Open' AND blood_group = ? AND LOWER(TRIM(city)) = LOWER(TRIM(?))
        ORDER BY CASE urgency WHEN 'Critical' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC
    """, (donor['blood_group'], donor['city'])) or []

    return render_template('donor_profile.html', donor=donor, matching_requests=matching_requests)

@app.route('/api/donor/toggle-availability', methods=['POST'])
@login_required
def toggle_availability():
    """AJAX endpoint for real-time donor availability toggle."""
    user_id = session['user_id']
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    if not isinstance(data, dict):
        data = {}

    new_status = bool(data.get('is_available') in (1, True, '1', 'true', 'True'))

    donor = query_db("SELECT id FROM donors WHERE user_id = ?", (user_id,), one=True)
    if not donor:
        return jsonify({'success': False, 'error': 'Not a registered donor'}), 404

    execute_db("UPDATE donors SET is_available = ? WHERE user_id = ?", (new_status, user_id))
    return jsonify({'success': True, 'is_available': 1 if new_status else 0})

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

    if blood_group and blood_group.lower() not in ('all', '', 'any'):
        query += " AND blood_group = ?"
        params.append(blood_group)
    if city and city.lower() not in ('all', '', 'any'):
        query += " AND LOWER(TRIM(city)) LIKE ?"
        params.append(f"%{city.lower()}%")
    if urgency and urgency.lower() not in ('all', '', 'any'):
        query += " AND urgency = ?"
        params.append(urgency)
    if status and status.lower() not in ('all', '', 'any'):
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY CASE urgency WHEN 'Critical' THEN 1 WHEN 'Urgent' THEN 2 ELSE 3 END, created_at DESC"
    requests = query_db(query, params) or []

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

        valid_bgs = ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')
        if blood_group not in valid_bgs:
            flash('Please select a valid blood group.', 'danger')
            return redirect(url_for('emergency_request_new'))

        req_id = execute_db("""
            INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Open', ?)
        """, (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, notes))

        # Broadcast in-app emergency alert to matching verified donors in that city
        matching_donors = query_db("""
            SELECT user_id FROM donors
            WHERE blood_group = ? AND LOWER(TRIM(city)) = LOWER(TRIM(?)) AND is_verified = TRUE
        """, (blood_group, city)) or []

        for d in matching_donors:
            try:
                execute_db("""
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, ?)
                """, (
                    d['user_id'],
                    f"🚨 {urgency.upper()} BLOOD NEEDED: {blood_group} in {city}",
                    f"{patient_name} requires {units_needed} unit(s) of {blood_group} blood at {hospital}, {city}. Emergency contact: {contact_phone}.",
                    'emergency'
                ))
            except Exception:
                pass

        flash(f'Emergency Blood Request posted successfully! Notified {len(matching_donors)} registered {blood_group} donor(s) in {city}.', 'success')
        if req_id:
            return redirect(url_for('request_details', req_id=req_id))
        return redirect(url_for('requests_list'))

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
        WHERE d.blood_group = ? AND LOWER(TRIM(d.city)) = LOWER(TRIM(?)) AND d.is_verified = TRUE AND d.is_available = TRUE
        ORDER BY d.total_donations DESC
    """, (req_item['blood_group'], req_item['city'])) or []

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
# Meta WhatsApp Cloud API Broadcast Routes
# ---------------------------------------------------------

@app.route('/api/whatsapp/status')
def api_whatsapp_status():
    """Returns current Meta WhatsApp Cloud API configuration status and registered donor counts."""
    is_configured = whatsapp_service.is_whatsapp_configured()
    total_donors = query_db("SELECT COUNT(*) as cnt FROM donors", one=True)
    verified_donors = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = TRUE", one=True)
    available_donors = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_available = TRUE AND is_verified = TRUE", one=True)

    return jsonify({
        'is_configured': is_configured,
        'phone_id_set': bool(os.environ.get('WHATSAPP_PHONE_NUMBER_ID', '').strip()),
        'total_donors': total_donors['cnt'] if total_donors else 0,
        'verified_donors': verified_donors['cnt'] if verified_donors else 0,
        'available_donors': available_donors['cnt'] if available_donors else 0,
        'api_version': os.environ.get('WHATSAPP_API_VERSION', 'v19.0')
    })

@app.route('/api/whatsapp/matching-donors')
def api_whatsapp_matching_donors():
    """Fetches matching registered donors for a proposed WhatsApp emergency alert."""
    blood_group = request.args.get('blood_group', '').strip()
    city = request.args.get('city', '').strip()
    verified_only = request.args.get('verified_only', '1') in ('1', 'true', 'on', 'True')
    available_only = request.args.get('available_only', '1') in ('1', 'true', 'on', 'True')

    query = """
        SELECT d.id as donor_id, d.blood_group, d.city, d.is_verified, d.is_available,
               u.name, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE 1=1
    """
    params = []
    if blood_group and blood_group.lower() not in ('all', '', 'any'):
        query += " AND d.blood_group = ?"
        params.append(blood_group)
    if city and city.lower() not in ('all', '', 'any'):
        query += " AND LOWER(TRIM(d.city)) LIKE ?"
        params.append(f"%{city.lower()}%")
    if verified_only:
        query += " AND d.is_verified = TRUE"
    if available_only:
        query += " AND d.is_available = TRUE"

    query += " ORDER BY d.id DESC"
    donors = query_db(query, tuple(params)) or []

    donor_list = []
    for d in donors:
        clean_p = whatsapp_service.clean_phone_for_whatsapp(d['phone'])
        donor_list.append({
            'donor_id': d['donor_id'],
            'name': d['name'],
            'phone': d['phone'],
            'clean_phone': clean_p,
            'blood_group': d['blood_group'],
            'city': d['city'],
            'is_verified': bool(d['is_verified']),
            'is_available': bool(d['is_available'])
        })

    return jsonify({
        'count': len(donor_list),
        'donors': donor_list,
        'is_meta_configured': whatsapp_service.is_whatsapp_configured()
    })

@app.route('/api/whatsapp/broadcast', methods=['POST'])
def api_whatsapp_broadcast():
    """Broadcasts a real-time WhatsApp alert directly to registered donors."""
    data = request.get_json(silent=True) or request.form.to_dict() or {}
    if not isinstance(data, dict):
        data = {}

    patient_name = str(data.get('patient_name', '')).strip()
    hospital = str(data.get('hospital', '')).strip()
    contact_phone = str(data.get('contact_phone', '')).strip()
    blood_group = str(data.get('blood_group', '')).strip()
    city = str(data.get('city', '')).strip()
    urgency = str(data.get('urgency', 'Urgent')).strip()
    units_needed = str(data.get('units_needed', '1')).strip()
    notes = str(data.get('notes', '')).strip()
    verified_only = str(data.get('verified_only', '1')).lower() in ('1', 'true', 'on')
    available_only = str(data.get('available_only', '1')).lower() in ('1', 'true', 'on')

    if not patient_name or not hospital or not contact_phone:
        return jsonify({
            'success': False,
            'error': 'Patient name, hospital name, and emergency contact phone are required fields.'
        }), 400

    query = """
        SELECT d.id as donor_id, d.user_id, d.blood_group, d.city,
               u.name, u.phone
        FROM donors d
        JOIN users u ON d.user_id = u.id
        WHERE 1=1
    """
    params = []
    if blood_group and blood_group.lower() not in ('all', '', 'any'):
        query += " AND d.blood_group = ?"
        params.append(blood_group)
    if city and city.lower() not in ('all', '', 'any'):
        query += " AND LOWER(TRIM(d.city)) LIKE ?"
        params.append(f"%{city.lower()}%")
    if verified_only:
        query += " AND d.is_verified = TRUE"
    if available_only:
        query += " AND d.is_available = TRUE"

    matching_donors = query_db(query, tuple(params)) or []

    if not matching_donors:
        return jsonify({
            'success': False,
            'total_targeted': 0,
            'error': f'No matching registered donors found for {blood_group or "All blood groups"} in {city or "All cities"}. Tip: Register or verify volunteer donors first!'
        }), 200

    bg_display = "Any Blood Group" if blood_group.lower() in ('all', '', 'any') else blood_group
    city_display = city if city and city.lower() not in ('all', '', 'any') else "Hospital Location"

    alert_data = {
        'patient_name': patient_name,
        'hospital': hospital,
        'contact_phone': contact_phone,
        'blood_group': bg_display,
        'city': city_display,
        'urgency': urgency,
        'units_needed': units_needed,
        'notes': notes
    }

    broadcast_result = whatsapp_service.broadcast_emergency_alert(matching_donors, alert_data)

    # Sync to In-App Notifications table so targeted donors also see it in their portal
    notif_title = f"🚨 WhatsApp Emergency Alert: {bg_display} Needed in {city_display}"
    notif_body = f"Emergency blood alert dispatched for patient {patient_name} at {hospital}. Urgency: {urgency}. Contact: {contact_phone}"
    for donor in matching_donors:
        try:
            execute_db("""
                INSERT INTO notifications (user_id, title, message, type)
                VALUES (?, ?, ?, 'emergency')
            """, (donor['user_id'], notif_title, notif_body))
        except Exception:
            pass

    return jsonify(broadcast_result)

# ---------------------------------------------------------
# Admin Dashboard & Management
# ---------------------------------------------------------

@app.route('/admin')
@admin_required
def admin_dashboard():
    # 1. Stats
    r_total = query_db("SELECT COUNT(*) as cnt FROM donors", one=True)
    r_verified = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = TRUE", one=True)
    r_pending = query_db("SELECT COUNT(*) as cnt FROM donors WHERE is_verified = FALSE", one=True)
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
    """) or []

    # 3. Requests Table
    requests = query_db("SELECT * FROM blood_requests ORDER BY created_at DESC") or []

    # Blood centres publish inventory only after administrator verification.
    blood_banks = query_db("SELECT * FROM blood_banks ORDER BY is_verified ASC, created_at DESC") or [] if inventory_database_available() else []

    # 4. Users Table
    users = query_db("SELECT id, name, email, phone, role, created_at FROM users ORDER BY created_at DESC") or []

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        donors=donors,
        blood_banks=blood_banks,
        requests=requests,
        users=users
    )

@app.route('/admin/blood-bank/<int:bank_id>/verify', methods=['POST'])
@admin_required
def admin_verify_blood_bank(bank_id):
    if not inventory_database_available():
        return inventory_database_setup_response()
    bank = query_db('SELECT * FROM blood_banks WHERE id = ?', (bank_id,), one=True)
    if not bank:
        flash('Blood bank record not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    new_status = not bool(bank['is_verified'])
    execute_db('UPDATE blood_banks SET is_verified = ? WHERE id = ?', (new_status, bank_id))
    flash(f'{bank["name"]} verification ' + ('approved.' if new_status else 'revoked.'), 'success' if new_status else 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/blood-bank/<int:bank_id>/delete', methods=['POST'])
@admin_required
def admin_delete_blood_bank(bank_id):
    bank = query_db('SELECT id, name FROM blood_banks WHERE id = ?', (bank_id,), one=True)
    if bank:
        execute_db('DELETE FROM blood_banks WHERE id = ?', (bank_id,))
        flash(f'Blood bank "{bank["name"]}" deleted.', 'success')
    else:
        flash('Blood bank record not found.', 'danger')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/donor/<int:donor_id>/verify', methods=['POST'])
@admin_required
def admin_verify_donor(donor_id):
    donor = query_db("SELECT * FROM donors WHERE id = ?", (donor_id,), one=True)
    if not donor:
        flash('Donor record not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    current_verified = bool(donor['is_verified'])
    new_status = not current_verified
    execute_db("UPDATE donors SET is_verified = ? WHERE id = ?", (new_status, donor_id))

    if new_status:
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
        execute_db("DELETE FROM donors WHERE id = ?", (donor_id,))
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
    ) or []
    return render_template('notifications.html', notifications=notifications)

@app.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def notification_mark_read(notif_id):
    user_id = session['user_id']
    execute_db("UPDATE notifications SET is_read = TRUE WHERE id = ? AND user_id = ?", (notif_id, user_id))
    return redirect(url_for('notifications_view'))

@app.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def notifications_mark_all_read():
    user_id = session['user_id']
    execute_db("UPDATE notifications SET is_read = TRUE WHERE user_id = ?", (user_id,))
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
    host = os.environ.get('HOST', '0.0.0.0')
    app.run(debug=False, host=host, port=port)
