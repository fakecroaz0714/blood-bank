-- ==========================================================
-- BloodConnect: Supabase / PostgreSQL Database Schema
-- Ready to run in Supabase SQL Editor (https://supabase.com/dashboard)
-- ==========================================================

-- Clean existing tables if any
DROP TABLE IF EXISTS notifications CASCADE;
DROP TABLE IF EXISTS blood_requests CASCADE;
DROP TABLE IF EXISTS donors CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 1. Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK(role IN ('donor', 'requester', 'admin')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 2. Donors Table
CREATE TABLE donors (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    blood_group VARCHAR(5) NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    city VARCHAR(80) NOT NULL,
    address TEXT,
    latitude DOUBLE PRECISION DEFAULT 13.0827,
    longitude DOUBLE PRECISION DEFAULT 80.2707,
    is_available BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    last_donation_date DATE NULL,
    total_donations INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3. Blood Requests Table
CREATE TABLE blood_requests (
    id SERIAL PRIMARY KEY,
    requester_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_name VARCHAR(120) NOT NULL,
    blood_group VARCHAR(5) NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    units_needed INT DEFAULT 1,
    hospital VARCHAR(150) NOT NULL,
    city VARCHAR(80) NOT NULL,
    contact_phone VARCHAR(30) NOT NULL,
    urgency VARCHAR(20) DEFAULT 'Urgent' CHECK(urgency IN ('Normal', 'Urgent', 'Critical')),
    status VARCHAR(20) DEFAULT 'Open' CHECK(status IN ('Open', 'Fulfilled', 'Closed')),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 4. In-App Notifications Table
CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(30) DEFAULT 'info' CHECK(type IN ('emergency', 'verification', 'info')),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Performance indices for fast donor search and request lookup
CREATE INDEX idx_donors_search ON donors(blood_group, city, is_available, is_verified);
CREATE INDEX idx_requests_status ON blood_requests(status, urgency, blood_group);

-- ==========================================================
-- Pre-seeded Sample Data for Immediate Viva & Demo Testing
-- ==========================================================

-- Admin Account (admin@bloodconnect.org / admin123)
-- Password hash generated with werkzeug (scrypt/pbkdf2)
INSERT INTO users (id, name, email, password_hash, phone, role)
VALUES (1, 'Admin Officer', 'admin@bloodconnect.org', 'scrypt:32768:8:1$uHcxQ8i48GfFp2Wp$86df5b9c0a6b9a8f2762269a23ec18d7f1be70c0c66fe855eaee020c749b5c3b6bf4b693fa2b98bb2c2eb6118bfa6bdf3b58fc16df4b037ee46d03460677aa42', '+91 98765 43210', 'admin');

-- Requester Account (requester@bloodconnect.org / password123)
INSERT INTO users (id, name, email, password_hash, phone, role)
VALUES (2, 'Sarah Jenkins', 'requester@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 98401 23456', 'requester');

-- Donor Accounts (password123)
INSERT INTO users (id, name, email, password_hash, phone, role)
VALUES
(3, 'Rahul Sharma', 'donor@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 98402 11223', 'donor'),
(4, 'Priya Sundaram', 'priya@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 98405 55667', 'donor'),
(5, 'Vikram Malhotra', 'vikram@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 99887 76655', 'donor'),
(6, 'Ananya Iyer', 'ananya@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 97910 88990', 'donor'),
(7, 'Karthik Raja', 'karthik@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 91761 22334', 'donor'),
(8, 'Arjun Reddy', 'arjun@bloodconnect.org', 'scrypt:32768:8:1$7N0048Ld73t1fD7d$cffc82a17621c172ee240faebbc6ce21896a24921b714d24177dbe4184ec9c50005741fce224a132eef05e263d89ef19e2be279c13146479e0bf529ee37b98bf', '+91 98409 44332', 'donor');

-- Reset sequences
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users));

-- Donor Profiles
INSERT INTO donors (user_id, blood_group, city, address, latitude, longitude, is_available, is_verified, last_donation_date, total_donations)
VALUES
(3, 'O+', 'Chennai', 'No. 14, 2nd Avenue, Anna Nagar', 13.0850, 80.2100, TRUE, TRUE, '2026-05-15', 4),
(4, 'O+', 'Chennai', 'Flat 3B, Usman Road, T. Nagar', 13.0418, 80.2341, TRUE, TRUE, '2026-06-01', 2),
(5, 'A+', 'Bangalore', '4th Block, 80 Feet Road, Koramangala', 12.9352, 77.6245, TRUE, TRUE, '2026-03-20', 5),
(6, 'B+', 'Chennai', 'Gandhinagar, Adyar', 13.0012, 80.2565, TRUE, FALSE, NULL, 0),
(7, 'O-', 'Chennai', '100 Feet Bypass Road, Velachery', 12.9815, 80.2180, FALSE, TRUE, '2026-08-20', 3),
(8, 'O+', 'Chennai', 'GST Road, West Tambaram', 12.9249, 80.1000, TRUE, TRUE, '2026-02-14', 8);

-- Blood Requests
INSERT INTO blood_requests (requester_id, patient_name, blood_group, units_needed, hospital, city, contact_phone, urgency, status, notes)
VALUES
(2, 'Ramesh Kumar', 'O+', 2, 'Apollo Hospital, Greams Road', 'Chennai', '+91 98401 23456', 'Critical', 'Open', 'Emergency cardiac procedure scheduled for tomorrow morning. Any O+ donors please reach out urgently.'),
(2, 'Kavitha M', 'A+', 1, 'Fortis Malar Hospital, Adyar', 'Chennai', '+91 98401 23456', 'Urgent', 'Open', 'Platelet and whole blood requirement for acute dengue treatment.'),
(2, 'Amitabh Sen', 'B+', 3, 'Manipal Hospital, Old Airport Road', 'Bangalore', '+91 99000 11223', 'Normal', 'Fulfilled', 'Replacement donor request for orthopedic elective knee surgery. Completed successfully.');

-- Sample Notifications
INSERT INTO notifications (user_id, title, message, type, is_read)
VALUES
(3, '🚨 CRITICAL REQUEST: O+ Blood Needed in Chennai', 'Patient Ramesh Kumar needs 2 units of O+ blood at Apollo Hospital, Greams Road, Chennai. If eligible, please contact +91 98401 23456.', 'emergency', FALSE),
(3, '✅ Account Verified', 'Your donor profile has been verified by the BloodConnect Medical Admin. You are now visible to search queries.', 'verification', TRUE);
