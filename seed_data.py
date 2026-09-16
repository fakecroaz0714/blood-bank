import sqlite3
from werkzeug.security import generate_password_hash
from database import init_db, execute_db, query_db, get_db

def seed():
    """Initializes the database and seeds realistic demo data."""
    print("Initializing database...")
    init_db()

    conn = get_db()
    cur = conn.cursor()

    # 1. Admin Account
    admin_pw = generate_password_hash('admin123')
    cur.execute("""
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    """, ('Admin Officer', 'admin@bloodconnect.org', admin_pw, '+91 98765 43210', 'admin'))

    # 2. Requester Account
    req_pw = generate_password_hash('password123')
    cur.execute("""
        INSERT INTO users (name, email, password_hash, phone, role)
        VALUES (?, ?, ?, ?, ?)
    """, ('Sarah Jenkins', 'requester@bloodconnect.org', req_pw, '+91 98401 23456', 'requester'))
    requester_user_id = cur.lastrowid

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
        cur.execute("""
            INSERT INTO users (name, email, password_hash, phone, role)
            VALUES (?, ?, ?, ?, ?)
        """, (d['name'], d['email'], generate_password_hash(d['pw']), d['phone'], 'donor'))
        uid = cur.lastrowid
        if first_donor_user_id is None:
            first_donor_user_id = uid

        cur.execute("""
            INSERT INTO donors (user_id, blood_group, city, address, latitude, longitude, is_available, is_verified, last_donation_date, total_donations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (uid, d['blood_group'], d['city'], d['address'], d['lat'], d['lng'], d['available'], d['verified'], d['last_donation'], d['total_donations']))

    # 4. Blood Requests
    requests_data = [
        (requester_user_id, 'Ramesh Kumar', 'O+', 2, 'Apollo Hospital, Greams Road', 'Chennai', '+91 98401 23456', 'Critical', 'Open', 'Emergency cardiac procedure scheduled for tomorrow morning. Any O+ donors please reach out urgently.'),
        (requester_user_id, 'Kavitha M', 'A+', 1, 'Fortis Malar Hospital, Adyar', 'Chennai', '+91 98401 23456', 'Urgent', 'Open', 'Platelet and whole blood requirement for acute dengue treatment.'),
        (requester_user_id, 'Amitabh Sen', 'B+', 3, 'Manipal Hospital, Old Airport Road', 'Bangalore', '+91 99000 11223', 'Normal', 'Fulfilled', 'Replacement donor request for orthopedic elective knee surgery. Completed successfully.')
    ]

    for req in requests_data:
        cur.execute("""
            INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, req)

    # 5. In-App Notifications
    if first_donor_user_id:
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, ?)
        """, (
            first_donor_user_id,
            '🚨 CRITICAL REQUEST: O+ Blood Needed in Chennai',
            'Patient Ramesh Kumar needs 2 units of O+ blood at Apollo Hospital, Greams Road, Chennai. If eligible, please contact +91 98401 23456.',
            'emergency',
            0
        ))
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, ?)
        """, (
            first_donor_user_id,
            '✅ Account Verified',
            'Your donor profile has been verified by the BloodConnect Medical Admin. You are now visible to search queries.',
            'verification',
            1
        ))

    conn.commit()
    conn.close()
    print("Database seeded successfully with sample donors, requesters, admin, and blood requests!")

if __name__ == '__main__':
    seed()
