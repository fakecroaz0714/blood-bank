#!/bin/bash
# ==========================================================
# BloodConnect - Quick Launch Script for Viva / Local Demo
# ==========================================================

echo "======================================================="
echo "   BloodConnect: Online Blood Donor Finder System     "
echo "======================================================="

# Navigate to project directory
cd "$(dirname "$0")"

# Ensure virtual environment exists and is activated
if [ ! -d "venv" ]; then
    echo "First time setup: Initializing Python virtual environment..."
    python3 -m venv venv
    venv/bin/pip install --quiet -r requirements.txt
fi
source venv/bin/activate

# Ensure database is seeded if missing
if [ ! -f "bloodconnect.db" ]; then
    echo "First time setup: Seeding database with realistic demo data..."
    python seed_data.py
fi

echo ""
echo "🚀 Starting BloodConnect web server on http://127.0.0.1:5050 ..."
echo "👉 Open http://127.0.0.1:5050 in your browser to view the app."
echo ""
echo "Demo Login Credentials:"
echo "-------------------------------------------------------"
echo "Role        | Email                      | Password    "
echo "-------------------------------------------------------"
echo "Admin       | admin@bloodconnect.org     | admin123    "
echo "Donor (O+)  | donor@bloodconnect.org     | password123 "
echo "Requester   | requester@bloodconnect.org | password123 "
echo "-------------------------------------------------------"
echo "Tip: You can also use the 1-click 'Viva Demo' buttons on the login page!"
echo ""

python app.py
