-- BloodConnect SQLite Database Schema
-- Compatible with SQLite 3

-- Clean existing tables if any
DROP TABLE IF EXISTS blood_bank_stock;
DROP TABLE IF EXISTS blood_banks;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS blood_requests;
DROP TABLE IF EXISTS donors;
DROP TABLE IF EXISTS users;

-- 1. Users Table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK(role IN ('donor', 'requester', 'admin')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Donors Table
CREATE TABLE donors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    blood_group VARCHAR(5) NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    city VARCHAR(80) NOT NULL,
    address TEXT,
    latitude REAL DEFAULT 13.0827,
    longitude REAL DEFAULT 80.2707,
    is_available INTEGER DEFAULT 1 CHECK(is_available IN (0, 1)),
    is_verified INTEGER DEFAULT 0 CHECK(is_verified IN (0, 1)),
    last_donation_date DATE,
    total_donations INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Blood Requests Table
CREATE TABLE blood_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requester_id INTEGER NOT NULL,
    patient_name VARCHAR(120) NOT NULL,
    blood_group VARCHAR(5) NOT NULL CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    units_needed INTEGER DEFAULT 1,
    hospital VARCHAR(150) NOT NULL,
    city VARCHAR(80) NOT NULL,
    contact_phone VARCHAR(30) NOT NULL,
    urgency VARCHAR(20) DEFAULT 'Urgent' CHECK(urgency IN ('Normal', 'Urgent', 'Critical')),
    status VARCHAR(20) DEFAULT 'Open' CHECK(status IN ('Open', 'Fulfilled', 'Closed')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. In-App Notifications Table
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(30) DEFAULT 'info' CHECK(type IN ('emergency', 'verification', 'info')),
    is_read INTEGER DEFAULT 0 CHECK(is_read IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indices for rapid search on blood group and city
CREATE INDEX idx_donors_search ON donors(blood_group, city, is_available, is_verified);
CREATE INDEX idx_requests_status ON blood_requests(status, urgency, blood_group);

-- Blood-bank inventory is separate from volunteer donor profiles.
CREATE TABLE IF NOT EXISTS blood_banks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(160) NOT NULL,
    email VARCHAR(160) NOT NULL UNIQUE,
    phone VARCHAR(40) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    license_number VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT NOT NULL,
    latitude REAL DEFAULT 13.0827,
    longitude REAL DEFAULT 80.2707,
    is_verified INTEGER NOT NULL DEFAULT 0 CHECK (is_verified IN (0, 1)),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blood_bank_stock (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blood_bank_id INTEGER NOT NULL,
    blood_group VARCHAR(5) NOT NULL CHECK (blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    component VARCHAR(40) NOT NULL CHECK (component IN ('Whole Blood', 'Red Cells', 'Platelets', 'Plasma')),
    units_available INTEGER NOT NULL DEFAULT 0 CHECK (units_available >= 0),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (blood_bank_id, blood_group, component),
    FOREIGN KEY (blood_bank_id) REFERENCES blood_banks(id) ON DELETE CASCADE
);
