import os
import sys
import unittest
import tempfile
import sqlite3

# Ensure scratch/bloodconnect directory is on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app
import database
from seed_data import seed

class BloodConnectTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database for isolated testing
        self.db_fd, self.temp_db_path = tempfile.mkstemp(suffix='.db')
        database.DATABASE_PATH = self.temp_db_path
        
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test_secret_key'
        self.client = app.test_client()

        # Seed test database
        seed()

    def tearDown(self):
        os.close(self.db_fd)
        if os.path.exists(self.temp_db_path):
            os.unlink(self.temp_db_path)

    def test_home_page_loads(self):
        """Home page should return 200 OK and show project title and statistics."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'BloodConnect', response.data)
        self.assertIn(b'Quick Donor Finder', response.data)
        self.assertIn(b'Registered Donors', response.data)

    def test_quick_demo_login(self):
        """1-Click Viva Demo login should log in admin, donor, and requester."""
        # 1. Admin quick login
        res_admin = self.client.get('/quick-login/admin', follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'System Overview', res_admin.data)

        # 2. Donor quick login
        res_donor = self.client.get('/quick-login/donor', follow_redirects=True)
        self.assertEqual(res_donor.status_code, 200)
        self.assertIn(b'Donor Dashboard', res_donor.data)
        self.assertIn(b'Rahul Sharma', res_donor.data)

        # 3. Requester quick login
        res_req = self.client.get('/quick-login/requester', follow_redirects=True)
        self.assertEqual(res_req.status_code, 200)
        self.assertIn(b'Emergency Blood Requests', res_req.data)

    def test_donor_search_filter(self):
        """Search should filter by blood group and city, showing only verified & available donors."""
        # Query for O+ in Chennai
        response = self.client.get('/search?blood_group=O%2B&city=Chennai&available_only=1&verified_only=1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Rahul Sharma', response.data) # O+, verified, available
        self.assertIn(b'Priya Sundaram', response.data) # O+, verified, available
        # Karthik Raja is O- and unavailable -> should NOT appear
        self.assertNotIn(b'Karthik Raja', response.data)
        # Ananya Iyer is B+ and unverified -> should NOT appear
        self.assertNotIn(b'Ananya Iyer', response.data)

    def test_registration_duplicate_email_prevention(self):
        """Registering with an already existing email must be rejected."""
        response = self.client.post('/register', data={
            'name': 'Duplicate User',
            'email': 'donor@bloodconnect.org', # already exists in seed data
            'phone': '+91 99999 00000',
            'password': 'password123',
            'role': 'donor',
            'blood_group': 'A+',
            'city': 'Chennai'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'already exists', response.data)

    def test_new_donor_registration(self):
        """Registering a new donor creates both user and donor records."""
        response = self.client.post('/register', data={
            'name': 'Fresh Volunteer',
            'email': 'volunteer@bloodconnect.org',
            'phone': '+91 98888 12345',
            'password': 'password123',
            'role': 'donor',
            'blood_group': 'B-',
            'city': 'Coimbatore',
            'address': 'RS Puram',
            'last_donation_date': '2026-01-01'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Account created successfully', response.data)

        # Verify DB entry
        with app.app_context():
            u = database.query_db("SELECT * FROM users WHERE email = 'volunteer@bloodconnect.org'", one=True)
            self.assertIsNotNone(u)
            d = database.query_db("SELECT * FROM donors WHERE user_id = ?", (u['id'],), one=True)
            self.assertIsNotNone(d)
            self.assertEqual(d['blood_group'], 'B-')
            self.assertEqual(d['city'], 'Coimbatore')

    def test_donor_availability_toggle_api(self):
        """Donor can toggle availability via JSON API."""
        # Login as donor
        self.client.get('/quick-login/donor')

        # Toggle to unavailable (0)
        res = self.client.post('/api/donor/toggle-availability', json={'is_available': 0})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['is_available'], 0)

        # Verify in DB
        with app.app_context():
            d = database.query_db("SELECT is_available FROM donors WHERE user_id = 3", one=True)
            self.assertEqual(d['is_available'], 0)

    def test_emergency_request_notification_dispatch(self):
        """Posting an emergency blood request creates alerts for matching verified donors."""
        # Login as requester
        self.client.get('/quick-login/requester')

        response = self.client.post('/requests/new', data={
            'patient_name': 'Emergency Patient Test',
            'blood_group': 'O+',
            'units_needed': 2,
            'hospital': 'MGM Healthcare',
            'city': 'Chennai',
            'contact_phone': '+91 98401 99999',
            'urgency': 'Critical',
            'notes': 'Urgent bypass surgery requirement'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Emergency Blood Request posted successfully', response.data)

        # Check notifications for Rahul Sharma (O+ donor in Chennai)
        with app.app_context():
            notif = database.query_db("SELECT * FROM notifications WHERE user_id = 3 ORDER BY id DESC LIMIT 1", one=True)
            self.assertIsNotNone(notif)
            self.assertIn('CRITICAL BLOOD NEEDED', notif['title'])
            self.assertEqual(notif['type'], 'emergency')

    def test_admin_donor_verification(self):
        """Admin can approve pending donors and toggle verification."""
        # Login as admin
        self.client.get('/quick-login/admin')

        # Find unverified donor (Ananya Iyer, donor id 4)
        with app.app_context():
            d_before = database.query_db("SELECT is_verified FROM donors WHERE user_id = 6", one=True)
            self.assertEqual(d_before['is_verified'], 0)

        # Verify donor
        res = self.client.post('/admin/donor/4/verify', follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        with app.app_context():
            d_after = database.query_db("SELECT is_verified FROM donors WHERE id = 4", one=True)
            self.assertEqual(d_after['is_verified'], 1)

    def test_api_donors_locations_json(self):
        """Locations API should return valid JSON with latitude, longitude, and blood group."""
        res = self.client.get('/api/donors/locations?blood_group=O%2B')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)
        self.assertIn('latitude', data[0])
        self.assertIn('longitude', data[0])
        self.assertEqual(data[0]['blood_group'], 'O+')

if __name__ == '__main__':
    unittest.main()
