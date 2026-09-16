# BloodConnect: Online Blood Donor Finder & Emergency Request System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20MySQL-orange.svg)](https://sqlite.org/)
[![UI](https://img.shields.io/badge/UI-Bootstrap%205%20%2B%20Leaflet.js-crimson.svg)](https://getbootstrap.com/)

A modern, full-stack web application designed for academic project presentations, vivas, and real-world emergency volunteer blood coordination.

---

## Key Highlights & Features

1. **Role-Based Access Control (RBAC)**:
   - **Donor**: Registers medical details, manages live availability switch, views 90-day eligibility countdown, receives localized emergency requests.
   - **Requester**: Searches matching donors, contacts donors securely, posts emergency blood requests with hospital & urgency details.
   - **Admin**: Verifies volunteer donors before public search listing, updates blood request lifecycles (Open -> Fulfilled -> Closed), monitors system metrics.

2. **Core System Workflow**:
   - Donor registers -> Admin verifies profile -> Donor sets status as **Available**.
   - Requester searches for a blood group (e.g. `O+`) and city (e.g. `Chennai`).
   - Only **verified** and **available** matching donors are returned in results and on the map.
   - If no local donors are immediately available, the requester submits an **Emergency Blood Request**.
   - The platform **automatically broadcasts in-app emergency alerts** to all registered matching donors in that city!

3. **Bonus Features for Maximum Viva Marks**:
   - 🗺️ **Interactive Geolocation Map (Leaflet.js & OpenStreetMap)**: Visualizes donor and hospital pins with custom blood drops without requiring paid Google Maps API keys.
   - ⏱️ **90-Day Medical Donation Eligibility Tracker**: Calculates cooldown days since `last_donation_date` based on medical blood donation safety guidelines.
   - ⚡ **1-Click Viva Demo Logins**: Dedicated one-click login buttons on the login page for `Admin`, `Donor`, and `Requester` so you never stumble during an oral presentation.
   - 🔄 **Real-Time AJAX Availability Switch**: Donors can toggle their status between "Available" and "Unavailable" without full page reloads.
   - 📊 **Interactive Blood Group Compatibility Guide**: Educational visualizer explaining universal donors (O-) and universal recipients (AB+).
   - 📁 **Dual Database Support**: SQLite (`bloodconnect.db`) out-of-the-box for instant zero-config demos, plus a ready-to-import MySQL dump (`schema_mysql.sql`) for submission requirements.

---

## Quick Start (Running Locally)

### 1. Launch with one command:
```bash
cd /Users/sadiqsmacbook/.gemini/antigravity-ide/scratch/bloodconnect
./run.sh
```
Or manually:
```bash
cd /Users/sadiqsmacbook/.gemini/antigravity-ide/scratch/bloodconnect
source venv/bin/activate
python app.py
```

### 2. Open in your browser:
Visit: **[http://127.0.0.1:5050](http://127.0.0.1:5050)**

*(Note: We use port 5050 to avoid conflicts with macOS AirPlay Receiver on port 5000).*

---

## Demo Login Credentials for Viva

| Role | Email | Password | Pre-seeded Details |
|---|---|---|---|
| **Admin** | `admin@bloodconnect.org` | `admin123` | System Administrator with verification rights |
| **Donor** | `donor@bloodconnect.org` | `password123` | Rahul Sharma (O+, Chennai, 4 donations) |
| **Donor** | `priya@bloodconnect.org` | `password123` | Priya Sundaram (O+, Chennai, 2 donations) |
| **Donor** | `ananya@bloodconnect.org` | `password123` | Ananya Iyer (B+, Unverified - test admin approval!) |
| **Donor** | `karthik@bloodconnect.org` | `password123` | Karthik Raja (O-, Unavailable toggle test) |
| **Requester** | `requester@bloodconnect.org` | `password123` | Sarah Jenkins (Posted Apollo Hospital request) |

> 💡 **Viva Tip**: On the `/login` page, you can simply click the pre-configured buttons in the top box to log in instantly as any role!

---

## Database Architecture

### Entity Relationship & Tables

```text
┌─────────────────┐       1:1       ┌──────────────────┐
│      USERS      │◄───────────────►│      DONORS      │
├─────────────────┤                 ├──────────────────┤
│ id (PK)         │                 │ id (PK)          │
│ name            │                 │ user_id (FK)     │
│ email (UNIQUE)  │                 │ blood_group      │
│ password_hash   │                 │ city             │
│ phone           │                 │ address          │
│ role            │                 │ latitude         │
│ created_at      │                 │ longitude        │
└────────┬────────┘                 │ is_available     │
         │                          │ is_verified      │
         │ 1:N                      │ last_donation_dt │
         ▼                          │ total_donations  │
┌─────────────────┐                 └──────────────────┘
│ BLOOD_REQUESTS  │
├─────────────────┤
│ id (PK)         │
│ requester_id(FK)│
│ patient_name    │
│ blood_group     │
│ units_needed    │
│ hospital        │
│ city            │
│ contact_phone   │
│ urgency         │
│ status          │
│ notes           │
└─────────────────┘
```

---

## Testing & Verification

Run the automated test suite with:
```bash
./venv/bin/python -m unittest tests/test_app.py
```
**Test Coverage Includes**:
- User registration and unique email constraint enforcement.
- Password hashing and authentication validation.
- Search queries returning only verified and available donors.
- Real-time donor availability toggle API.
- Emergency request generation and notification dispatch.
- Admin verification privileges and status management.

---

## Viva Q&A Guide

**Q1: Why did you choose Python Flask for the backend?**  
> *Flask is lightweight, modular, and provides fine-grained control over routing, session handling, and database transactions without heavy boilerplate, making it ideal for high-performance mini and major projects.*

**Q2: How are user passwords secured?**  
> *Passwords are never stored in plain text. We utilize `werkzeug.security.generate_password_hash`, which implements salted PBKDF2/SHA256 hashing. During login, `check_password_hash` verifies the hash in constant time to prevent timing attacks.*

**Q3: How does the system ensure requester safety and prevent fake donors?**  
> *Before any volunteer donor appears in search results or on the public map, their account must be reviewed and approved by an Administrator (`is_verified = 1`). Furthermore, donors can toggle their availability (`is_available = 0`) when unwell.*

**Q4: How does the emergency notification system work?**  
> *When an emergency request is posted, the backend executes a targeted query to find all verified donors of the requested blood group in that city, and immediately inserts alert records into the `notifications` table.*
