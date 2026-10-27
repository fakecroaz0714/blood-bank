import sqlite3
from auth_utils import generate_password_hash
from database import init_db, execute_db, query_db, get_db

def seed():
    """Initializes the database and seeds realistic demo data."""
    print("Initializing database...")
    init_db()

    conn = get_db()
    cur = conn.cursor()

    # 1. Admin Account
    admin_pw = generate_password_hash('admin123')
    execute_db("""
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    """, ('Admin Officer', 'admin@bloodconnect.org', admin_pw, '+91 98765 43210', 'admin'))

    # 2. Requester Account
    req_pw = generate_password_hash('password123')
    requester_user_id = execute_db("""
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    """, ('Sarah Jenkins', 'requester@bloodconnect.org', req_pw, '+91 98401 23456', 'requester'))

    # 3. Donors Data
    donors_data = [
        {
            'name': 'Rahul Sharma',
            'email': 'donor@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 98402 11223',
            'blood_group': 'O+',
            'city': 'Chennai',
            'address': 'No. 14, 2nd Avenue, Anna Nagar',
            'lat': 13.0850,
            'lng': 80.2100,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-05-15',
            'total_donations': 4
        },
        {
            'name': 'Priya Sundaram',
            'email': 'priya@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 98405 55667',
            'blood_group': 'O+',
            'city': 'Chennai',
            'address': 'Flat 3B, Usman Road, T. Nagar',
            'lat': 13.0418,
            'lng': 80.2341,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-06-01',
            'total_donations': 2
        },
        {
            'name': 'Vikram Malhotra',
            'email': 'vikram@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 99887 76655',
            'blood_group': 'A+',
            'city': 'Bangalore',
            'address': '4th Block, 80 Feet Road, Koramangala',
            'lat': 12.9352,
            'lng': 77.6245,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-03-20',
            'total_donations': 5
        },
        {
            'name': 'Ananya Iyer',
            'email': 'ananya@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 97910 88990',
            'blood_group': 'B+',
            'city': 'Chennai',
            'address': 'Gandhinagar, Adyar',
            'lat': 13.0012,
            'lng': 80.2565,
            'available': 1,
            'verified': 0, # Unverified donor for admin testing!
            'last_donation': None,
            'total_donations': 0
        },
        {
            'name': 'Karthik Raja',
            'email': 'karthik@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 91761 22334',
            'blood_group': 'O-',
            'city': 'Chennai',
            'address': '100 Feet Bypass Road, Velachery',
            'lat': 12.9815,
            'lng': 80.2180,
            'available': 0, # Unavailable toggle test!
            'verified': 1,
            'last_donation': '2026-08-20',
            'total_donations': 3
        },
        {
            'name': 'Meera Nair',
            'email': 'meera@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 98200 33445',
            'blood_group': 'AB+',
            'city': 'Mumbai',
            'address': 'Hill Road, Bandra West',
            'lat': 19.0596,
            'lng': 72.8295,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-01-10',
            'total_donations': 6
        },
        {
            'name': 'Rohit Varma',
            'email': 'rohit@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 98111 66778',
            'blood_group': 'A-',
            'city': 'Delhi',
            'address': 'Block C, Connaught Place',
            'lat': 28.6315,
            'lng': 77.2167,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-04-12',
            'total_donations': 1
        },
        {
            'name': 'Arjun Reddy',
            'email': 'arjun@bloodconnect.org',
            'pw': 'password123',
            'phone': '+91 98409 44332',
            'blood_group': 'O+',
            'city': 'Chennai',
            'address': 'GST Road, West Tambaram',
            'lat': 12.9249,
            'lng': 80.1000,
            'available': 1,
            'verified': 1,
            'last_donation': '2026-02-14',
            'total_donations': 8
        }
    ]

    first_donor_user_id = None
    for d in donors_data:
        uid = execute_db("""
            INSERT INTO users (name, email, password_hash, phone, role)
            VALUES (?, ?, ?, ?, ?)
        """, (d['name'], d['email'], generate_password_hash(d['pw']), d['phone'], 'donor'))
        if first_donor_user_id is None:
            first_donor_user_id = uid

        execute_db("""
            INSERT INTO donors (user_id, blood_group, city, address, latitude, longitude, is_available, is_verified, last_donation_date, total_donations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, d['blood_group'], d['city'], d['address'], d['lat'], d['lng'], bool(d['available']), bool(d['verified']), d['last_donation'], d['total_donations']))

    # 4. Blood Requests
    requests_data = [
        (requester_user_id, 'Ramesh Kumar', 'O+', 2, 'Apollo Hospital, Greams Road', 'Chennai', '+91 98401 23456', 'Critical', 'Open', 'Emergency cardiac procedure scheduled for tomorrow morning. Any O+ donors please reach out urgently.'),
        (requester_user_id, 'Kavitha M', 'A+', 1, 'Fortis Malar Hospital, Adyar', 'Chennai', '+91 98401 23456', 'Urgent', 'Open', 'Platelet and whole blood requirement for acute dengue treatment.'),
        (requester_user_id, 'Amitabh Sen', 'B+', 3, 'Manipal Hospital, Old Airport Road', 'Bangalore', '+91 99000 11223', 'Normal', 'Fulfilled', 'Replacement donor request for orthopedic elective knee surgery. Completed successfully.')
    ]

    for req in requests_data:
        execute_db("""
            INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, req)

    # 5. In-App Notifications
    if first_donor_user_id:
        execute_db("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, FALSE)
        """, (
            first_donor_user_id,
            '🚨 CRITICAL REQUEST: O+ Blood Needed in Chennai',
            'Patient Ramesh Kumar needs 2 units of O+ blood at Apollo Hospital, Greams Road, Chennai. If eligible, please contact +91 98401 23456.',
            'emergency'
        ))
        execute_db("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, TRUE)
        """, (
            first_donor_user_id,
            '✅ Account Verified',
            'Your donor profile has been verified by the BloodConnect Medical Admin. You are now visible to search queries.',
            'verification'
        ))

    # 6. Blood Banks & Stock
    bank_pw = generate_password_hash('password123')
    bank1_id = execute_db("""
        INSERT INTO blood_banks (name, email, phone, password_hash, license_number, city, address, latitude, longitude, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
    """, ('City Central Blood Centre', 'central@bank.org', '+91 98401 99999', bank_pw, 'LIC-TN-CHE-2026', 'Chennai', '123 Hospital Road, Thousand Lights', 13.0600, 80.2500))

    bank2_id = execute_db("""
        INSERT INTO blood_banks (name, email, phone, password_hash, license_number, city, address, latitude, longitude, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
    """, ('Bangalore Metro Blood Bank', 'metro@bank.org', '+91 98000 88888', bank_pw, 'LIC-KA-BLR-2026', 'Bangalore', '45 Indiranagar 100ft Road', 12.9716, 77.5946))

    bank3_id = execute_db("""
        INSERT INTO blood_banks (name, email, phone, password_hash, license_number, city, address, latitude, longitude, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)
    """, ('Apollo Life Blood Centre', 'apollo@bank.org', '+91 98401 11222', bank_pw, 'LIC-TN-CHE-9999', 'Chennai', '21 Greams Lane, Thousand Lights', 13.0580, 80.2520))

    stock_items = [
        (bank1_id, 'O+', 'Whole Blood', 15),
        (bank1_id, 'A+', 'Red Cells', 10),
        (bank1_id, 'B+', 'Platelets', 8),
        (bank1_id, 'O-', 'Whole Blood', 4),
        (bank2_id, 'A+', 'Whole Blood', 12),
        (bank2_id, 'B+', 'Plasma', 6),
        (bank2_id, 'AB+', 'Platelets', 5),
    ]
    for s in stock_items:
        if s[0]:
            execute_db("""
                INSERT INTO blood_bank_stock (blood_bank_id, blood_group, component, units_available, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, s)

    print("Database seeded successfully with sample donors, requesters, admin, and blood requests!")

def init_clean():
    """Initializes a clean database with only the Administrator account (no dummy donors or requesters)."""
    print("Initializing clean database for real-time registrations...")
    init_db()

    admin_pw = generate_password_hash('admin123')
    execute_db("""
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    """, ('Admin Officer', 'admin@bloodconnect.org', admin_pw, '+91 98765 43210', 'admin'))

    print("Clean database ready! Only Admin account created. All donors and requesters will be real-time registrations.")

if __name__ == '__main__':
    import sys
    if '--demo' in sys.argv:
        seed()
    else:
        init_clean()
